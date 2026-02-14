from . import buildings, gameObjects, utils, islands, _gameObjectsSerializer
from ._gameObjectsSerializer import (
    Checkpoint,
    BinaryStreamReader,
    StringLUTReadWrite,
    BinaryStreamReaderWithStringLUT,
    GameObjectsSerializer
)

import zipfile
import os
from dataclasses import dataclass
import typing
import enum
import json

class FilePaths(enum.Enum):
    stringsLUT = "strings.bin"
    statistics = "statistics.bin"
    saveInfo = "savegame.json"
    research = "research.json"
    player = "local-player.json"
    mainMap = "maps/main/"
    simulationState = mainMap + "simulation/state.bin"
    placedIslands = mainMap + "islands/"
    islandAndBuildingStates = mainMap + "buildings/"
    trains = mainMap + "trains.bin"
    resourceChunks = mainMap + "resource-chunks.bin"
    cargo = mainMap + "cargo.bin"

@dataclass
class PlacedBuilding:
    type:buildings.BuildingInternalVariant
    pos:gameObjects.IslandTileCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.IBuildingConfig

@dataclass
class PlacedIsland:
    type:islands.Island
    pos:gameObjects.GlobalChunkCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.IIslandConfig
    placedBuildings:list[PlacedBuilding]

@dataclass
class Map:
    temp_simulationState:bytes
    placedIslands:list[PlacedIsland]
    temp_islandAndBuildingStates:bytes
    temp_trains:bytes
    temp_resourceChunks:bytes
    temp_cargo:bytes

@dataclass
class Savegame:
    map:Map
    temp_stringsLUT:StringLUTReadWrite
    temp_statistics:bytes
    temp_info:bytes
    temp_research:bytes
    temp_player:bytes

def _decodeIslands(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> list[PlacedIsland]:

    decodedIslands = []

    for _ in range(reader.readInt()):

        reader.assertCheckpoint(Checkpoint.Island)
        islandPos = serializer.deserialize(reader,gameObjects.GlobalChunkCoordinate)
        islandDefinition = serializer.deserialize(reader,islands.Island)
        islandRotation = serializer.deserialize(reader,utils.Rotation)
        islandConfig = None

        @reader.readBlob
        def _() -> None:
            nonlocal islandConfig

            if reader.readBool():
                @reader.readBlob
                def _() -> None:
                    nonlocal islandConfig

                    islandConfig = _gameObjectsSerializer.deserializeIslandConfig(
                        islandDefinition.id,
                        reader,
                        serializer,
                        False
                    )

            @reader.readBlob
            def _() -> None:

                reader.assertCheckpoint(Checkpoint.Buildings)

                for _ in range(reader.readInt()):

                    reader.assertCheckpoint(Checkpoint.Building)
                    buildingPos = serializer.deserialize(reader,gameObjects.IslandTileCoordinate)
                    buildingRotation = serializer.deserialize(reader,utils.Rotation)
                    buildingDefinition = serializer.deserialize(reader,buildings.BuildingInternalVariant)
                    buildingConfig = None

                    if reader.readBool():
                        buildingConfig = _gameObjectsSerializer.deserializeBuildingConfig(
                            buildingDefinition.id,
                            reader,
                            serializer,
                            False
                        )

def decodeSavegame(file:str|os.PathLike|typing.IO[bytes]) -> Savegame:

    with zipfile.ZipFile(file,"r") as f:
        stringsLUTRaw = f.read(FilePaths.stringsLUT)
        statisticsRaw = f.read(FilePaths.statistics)
        saveInfoRaw = f.read(FilePaths.saveInfo)
        playerRaw = f.read(FilePaths.player)
        simulationStateRaw = f.read(FilePaths.simulationState)
        trainsRaw = f.read(FilePaths.trains)
        resourceChunksRaw = f.read(FilePaths.resourceChunks)
        cargoRaw = f.read(FilePaths.cargo)
        placedIslandsRaw:list[bytes] = []
        islandAndBuildingStatesRaw:list[bytes] = []
        for name in f.namelist():
            if name.startswith(FilePaths.placedIslands):
                placedIslandsRaw.append(f.read(name))
            elif name.startswith(FilePaths.islandAndBuildingStates):
                islandAndBuildingStatesRaw.append(f.read(name))

    useCheckpoints = json.loads(saveInfoRaw)["BinaryDataCheckpoints"]

    stringsLUT = StringLUTReadWrite()
    stringsLUT.deserialize(BinaryStreamReader(stringsLUTRaw,useCheckpoints))

    decodedIslands = []

    for islandBundle in placedIslandsRaw:

        decodedIslands.extend(_decodeIslands(BinaryStreamReaderWithStringLUT(
            islandBundle,
            useCheckpoints,
            stringsLUT
        )))



_NUMBERS = [str(i) for i in range(10)]
def _isNumber(string:str) -> bool:
    if string == "":
        return False
    for char in string:
        if char not in _NUMBERS:
            return False
    return True

def getLatestBackupPath(folderPath:str) -> str:
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
    return latestBackupPath

if __name__ == "__main__":
    pass