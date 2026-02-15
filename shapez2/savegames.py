from . import buildings, gameObjects, utils, islands, _gameObjectsSerializer, research
from ._gameObjectsSerializer import (
    Checkpoint,
    BinaryStreamReader,
    BinaryStreamWriter,
    StringLUTReadWrite,
    BinaryStreamReaderWithStringLUT,
    BinaryStreamWriterWithStringLUT,
    GameObjectsSerializer,
    InvalidSerializedData
)

import zipfile
import os
from dataclasses import dataclass
import typing
import enum
import json
import math
import datetime

class FilePaths(enum.Enum):
    stringsLUT = "strings.bin"
    statistics = "statistics.bin"
    saveInfo = "savegame.json"
    research = "research.json"
    player = "local-player.json"
    mainMap = "maps/main/"
    simulationState = mainMap + "simulation/state.bin"
    placedIslandsPrefix = mainMap + "islands/"
    placedIslandsSuffix = ".bin"
    islandAndBuildingStatesPrefix = mainMap + "buildings/"
    islandAndBuildingStatesSuffix = ".bin"
    trains = mainMap + "trains.bin"
    resourceChunks = mainMap + "resource-chunks.bin"
    cargo = mainMap + "cargo.bin"

@dataclass
class PlacedBuilding:
    type:buildings.BuildingInternalVariant
    pos:gameObjects.IslandTileCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.IBuildingConfig|None

@dataclass
class PlacedIsland:
    type:islands.Island
    pos:gameObjects.GlobalChunkCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.IIslandConfig|None
    placedBuildings:list[PlacedBuilding]

@dataclass
class SavegameMap:
    temp_simulationState:bytes
    placedIslands:list[PlacedIsland]
    temp_islandAndBuildingStates:list[tuple[int,bytes]]
    temp_trains:bytes
    temp_resourceChunks:bytes
    temp_cargo:bytes

@dataclass
class Savegame:
    map:SavegameMap
    temp_stringsLUT:StringLUTReadWrite
    temp_statistics:bytes
    temp_info:bytes
    temp_research:bytes
    temp_player:bytes

_NUMBERS = [str(i) for i in range(10)]
def _isNumber(string:str) -> bool:
    if string == "":
        return False
    for char in string:
        if char not in _NUMBERS:
            return False
    return True

def _decodeBuildings(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> list[PlacedBuilding]:

    decodedBuildings = []
    reader.assertCheckpoint(Checkpoint.buildings)

    def decodeBuilding() -> None:

        reader.assertCheckpoint(Checkpoint.building)
        buildingPos = serializer.deserialize(reader,gameObjects.IslandTileCoordinate)
        buildingRotation = serializer.deserialize(reader,utils.Rotation)
        buildingDefinition = serializer.deserialize(reader,buildings.BuildingInternalVariant)
        buildingConfig = None

        if reader.readBool():
            @reader.readBlob
            def _():
                nonlocal buildingConfig
                buildingConfig = _gameObjectsSerializer.deserializeBuildingConfig(
                    buildingDefinition.id,
                    reader,
                    serializer,
                    False
                )

        decodedBuildings.append(PlacedBuilding(
            buildingDefinition,
            buildingPos,
            buildingRotation,
            buildingConfig
        ))

    for buildingIndex in range(reader.readInt()):
        try:
            decodeBuilding()
        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading building #{buildingIndex} : {e}")

    return decodedBuildings

def _decodeIslands(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> list[PlacedIsland]:

    decodedIslands = []

    def decodeIsland() -> None:

        reader.assertCheckpoint(Checkpoint.island)
        islandPos = serializer.deserialize(reader,gameObjects.GlobalChunkCoordinate)
        islandDefinition = serializer.deserialize(reader,islands.Island)
        islandRotation = serializer.deserialize(reader,utils.Rotation)
        islandConfig = None
        decodedBuildings:list[PlacedBuilding]

        @reader.readBlob
        def _():

            if reader.readBool():
                @reader.readBlob
                def _():
                    nonlocal islandConfig

                    islandConfig = _gameObjectsSerializer.deserializeIslandConfig(
                        islandDefinition.id,
                        reader,
                        serializer,
                        False
                    )

            @reader.readBlob
            def _():
                nonlocal decodedBuildings
                decodedBuildings = _decodeBuildings(reader,serializer)

        decodedIslands.append(PlacedIsland(
            islandDefinition,
            islandPos,
            islandRotation,
            islandConfig,
            decodedBuildings
        ))

    for islandIndex in range(reader.readInt()):
        try:
            decodeIsland()
        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading island #{islandIndex} : {e}")

    return decodedIslands

def decodeSavegame(file:str|os.PathLike|typing.IO[bytes]) -> Savegame:

    with zipfile.ZipFile(file,"r") as f:
        stringsLUTRaw = f.read(FilePaths.stringsLUT)
        statisticsRaw = f.read(FilePaths.statistics)
        saveInfoRaw = f.read(FilePaths.saveInfo)
        researchRaw = f.read(FilePaths.research)
        playerRaw = f.read(FilePaths.player)
        simulationStateRaw = f.read(FilePaths.simulationState)
        trainsRaw = f.read(FilePaths.trains)
        resourceChunksRaw = f.read(FilePaths.resourceChunks)
        cargoRaw = f.read(FilePaths.cargo)
        placedIslandsRaw:list[tuple[int,bytes]] = []
        islandAndBuildingStatesRaw:list[tuple[int,bytes]] = []
        for fileList,prefix,suffix in [
            (
                placedIslandsRaw,
                FilePaths.placedIslandsPrefix,
                FilePaths.placedIslandsSuffix
            ),
            (
                islandAndBuildingStatesRaw,
                FilePaths.islandAndBuildingStatesPrefix,
                FilePaths.islandAndBuildingStatesSuffix
            )
        ]:
            for name in f.namelist():
                if name.startswith(prefix.value) and name.endswith(suffix.value):
                    index = name.removeprefix(prefix.value).removesuffix(suffix.value)
                    if _isNumber(index):
                        fileList.append((int(index),f.read(name)))

    tempSaveInfo = json.loads(saveInfoRaw)
    useCheckpoints = tempSaveInfo["BinaryDataCheckpoints"]
    tempScenario = research.ingameScenarios[
        tempSaveInfo["Parameters"]["ScenarioParameters"]["ScenarioId"]
    ]
    serializer = GameObjectsSerializer(
        tempScenario.researchConfig.shapesConfig,
        tempScenario.researchConfig.colorScheme
    )

    stringsLUT = StringLUTReadWrite()
    try:
        stringsLUT.deserialize(BinaryStreamReader(stringsLUTRaw,useCheckpoints))
    except InvalidSerializedData as e:
        raise InvalidSerializedData(f"Error while reading strings LUT : {e}")

    decodedIslands = []

    for bundleIndex,islandBundle in placedIslandsRaw:

        try:
            decodedIslands.extend(_decodeIslands(
                BinaryStreamReaderWithStringLUT(
                    islandBundle,
                    useCheckpoints,
                    stringsLUT
                ),
                serializer
            ))
        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading island bundle #{bundleIndex} : {e}")

    # temp
    return Savegame(
        SavegameMap(
            simulationStateRaw,
            decodedIslands,
            islandAndBuildingStatesRaw,
            trainsRaw,
            resourceChunksRaw,
            cargoRaw
        ),
        stringsLUT,
        statisticsRaw,
        saveInfoRaw,
        researchRaw,
        playerRaw
    )

def _encodeBuildings(
    buildings:list[PlacedBuilding],
    writer:BinaryStreamWriterWithStringLUT,
    serializer:GameObjectsSerializer
) -> None:

    writer.writeCheckpoint(Checkpoint.buildings)
    writer.writeInt(len(buildings))

    for building in buildings:

        writer.writeCheckpoint(Checkpoint.building)
        serializer.serialize(writer,building.pos)
        serializer.serialize(writer,building.rotation)
        serializer.serialize(writer,building.type)
        if building.configuration is None:
            writer.writeBool(False)
        else:
            writer.writeBool(True)
            @writer.writeBlob
            def _():
                serializer.serialize(writer,building.configuration) # no type override

def _encodeIslands(
    islands:list[PlacedIsland],
    writer:BinaryStreamWriterWithStringLUT,
    serializer:GameObjectsSerializer
) -> None:

    writer.writeInt(len(islands))

    for island in islands:

        writer.writeCheckpoint(Checkpoint.island)
        serializer.serialize(writer,island.pos)
        serializer.serialize(writer,island.type)
        serializer.serialize(writer,island.rotation)

        @writer.writeBlob
        def _():

            if island.configuration is None:
                writer.writeBool(False)
            else:
                writer.writeBool(True)
                serializer.serialize(writer,island.configuration) # no type override

            @writer.writeBlob
            def _():
                _encodeBuildings(island.placedBuildings,writer,serializer)

def encodeSavegame(savegame:Savegame,file:str|os.PathLike|typing.IO[bytes]) -> None:

    tempSaveInfo = json.loads(savegame.temp_info)
    useCheckpoints = tempSaveInfo["BinaryDataCheckpoints"]
    tempScenario = research.ingameScenarios[tempSaveInfo["Parameters"]["ScenarioParameters"]["ScenarioId"]]
    serializer = GameObjectsSerializer(
        tempScenario.researchConfig.shapesConfig,
        tempScenario.researchConfig.colorScheme
    )

    islandsToEncode = savegame.map.placedIslands.copy()
    maxIslandsPerBundle = math.ceil(4**math.log10(len(islandsToEncode)))
    assert (maxIslandsPerBundle > 0) or (len(islandsToEncode) == 0)

    encodedIslands:list[tuple[int,bytes]] = []

    curBundle = []
    curBundleIndex = 0
    lastBundle = False
    while not lastBundle:
        if len(islandsToEncode) == 0:
            lastBundle = True
        else:
            curBundle.append(islandsToEncode.pop(0))
        if (len(curBundle) >= maxIslandsPerBundle) or (lastBundle and (len(curBundle) > 0)):
            writer = BinaryStreamWriterWithStringLUT(
                useCheckpoints,
                savegame.temp_stringsLUT
            )
            _encodeIslands(curBundle,writer,serializer)
            encodedIslands.append((curBundleIndex,writer.toBytes()))
            curBundleIndex += 1
            curBundle.clear()

    encodedStringsLUT = BinaryStreamWriter(useCheckpoints)
    savegame.temp_stringsLUT.serialize(encodedStringsLUT)

    with zipfile.ZipFile(file,"w") as f:
        f.writestr(FilePaths.stringsLUT,encodedStringsLUT.toBytes())
        f.writestr(FilePaths.statistics,savegame.temp_statistics)
        f.writestr(FilePaths.saveInfo,savegame.temp_info)
        f.writestr(FilePaths.research,savegame.temp_research)
        f.writestr(FilePaths.player,savegame.temp_player)
        f.writestr(FilePaths.simulationState,savegame.map.temp_simulationState)
        f.writestr(FilePaths.trains,savegame.map.temp_trains)
        f.writestr(FilePaths.resourceChunks,savegame.map.temp_resourceChunks)
        f.writestr(FilePaths.cargo,savegame.map.temp_cargo)
        for fileList,prefix,suffix in [
            (
                encodedIslands,
                FilePaths.placedIslandsPrefix,
                FilePaths.placedIslandsSuffix
            ),
            (
                savegame.map.temp_islandAndBuildingStates,
                FilePaths.islandAndBuildingStatesPrefix,
                FilePaths.islandAndBuildingStatesSuffix
            )
        ]:
            for i,data in fileList:
                f.writestr(prefix.value+str(i)+suffix.value,data)



def _getLatestBackupPathAndNum(folderPath:str) -> tuple[str,int]:
    latestBackupNum = 0
    latestBackupPath = None
    for dirEntry in os.scandir(folderPath):
        if (
            dirEntry.is_file()
            and dirEntry.name.startswith("backup-v")
            and _isNumber(curNum:=dirEntry.name.removeprefix("backup-v").split("-")[0])
            and (curNum:=int(curNum)) >= latestBackupNum
        ):
            latestBackupPath = dirEntry.path
            latestBackupNum = curNum
    if latestBackupPath is None:
        raise ValueError(f"No backups found in '{folderPath}'")
    return latestBackupPath, latestBackupNum

def getLatestBackupPath(folderPath:str) -> str:
    return _getLatestBackupPathAndNum(folderPath)[0]

def getNextBackupPath(folderPath:str) -> str:
    return os.path.join(
        folderPath,
        f"backup-v{_getLatestBackupPathAndNum(folderPath)[1]+1}-"
        + (
            datetime.datetime.now()
            .isoformat(timespec="microseconds")
            .replace("T","--")
            .replace(":","-")
            .replace(".","--")
        )
        + ".spz2"
    )