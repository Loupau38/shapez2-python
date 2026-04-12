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



#region map

@dataclass
class PlacedBuilding:
    type:buildings.BuildingInternalVariant
    pos:gameObjects.IslandTileCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.GenericBuildingConfig|None
    simulationState:gameObjects.GenericSimulationState|None=None

@dataclass
class PlacedIsland:
    type:islands.Island
    pos:gameObjects.GlobalChunkCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.GenericIslandConfig|None
    placedBuildings:list[PlacedBuilding]
    simulationState:gameObjects.GenericSimulationState|None=None

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

def _decodeIslandStates(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer,
    islandsMap:dict[gameObjects.GlobalChunkCoordinate,PlacedIsland],
    buildingsMap:dict[gameObjects.GlobalTileCoordinate,PlacedBuilding]
) -> None:

    def decodeIsland() -> None:

        islandPos = serializer.deserialize(reader,gameObjects.GlobalChunkCoordinate)
        islandDefinition = serializer.deserialize(reader,islands.Island)

        placedIsland = islandsMap.get(islandPos)

        if placedIsland is None:
            raise InvalidSerializedData(f"Island '{islandDefinition.id}' not found at {islandPos}")

        if placedIsland.type != islandDefinition:
            raise InvalidSerializedData(
                f"Island '{placedIsland.type.id}' was expected to be '{islandDefinition.id}'"
            )

        @reader.readBlob
        def _():
            placedIsland.simulationState = serializer.deserialize(reader,gameObjects.GenericSimulationState)

    def decodeBuilding() -> None:

        buildingPos = serializer.deserialize(reader,gameObjects.GlobalTileCoordinate)
        buildingDefinition = serializer.deserialize(reader,buildings.BuildingInternalVariant)

        placedBuilding = buildingsMap.get(buildingPos)

        if placedBuilding is None:
            raise InvalidSerializedData(f"Building '{buildingDefinition.id}' not found at {buildingPos}")

        if placedBuilding.type != buildingDefinition:
            raise InvalidSerializedData(
                f"Building '{placedBuilding.type.id}' was expected to be '{buildingDefinition.id}'"
            )

        @reader.readBlob
        def _():
            placedBuilding.simulationState = serializer.deserialize(reader,gameObjects.GenericSimulationState)

    for islandIndex in range(reader.readInt()):
        try:
            decodeIsland()
        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading island state #{islandIndex} : {e}")

    for buildingIndex in range(reader.readInt()):
        try:
            decodeBuilding()
        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading building state #{buildingIndex} : {e}")

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
                @writer.writeBlob
                def _():
                    serializer.serialize(writer,island.configuration) # no type override

            @writer.writeBlob
            def _():
                _encodeBuildings(island.placedBuildings,writer,serializer)

def _encodeIslandStates(
    islands:list[PlacedIsland],
    writer:BinaryStreamWriterWithStringLUT,
    serializer:GameObjectsSerializer
) -> None:

    writer.writeInt(len(islands))
    placedBuildings:list[tuple[gameObjects.GlobalTileCoordinate,PlacedBuilding]] = []

    for island in islands:

        serializer.serialize(writer,island.pos)
        serializer.serialize(writer,island.type)

        @writer.writeBlob
        def _():
            serializer.serialize(
                writer,
                island.simulationState,
                gameObjects.GenericSimulationState
            )

        placedBuildings.extend(
            (b.pos.toGlobalTile(island.pos),b)
            for b in island.placedBuildings
        )

    writer.writeInt(len(placedBuildings))

    for buildingPos,building in placedBuildings:

        serializer.serialize(writer,buildingPos)
        serializer.serialize(writer,building.type)

        @writer.writeBlob
        def _():
            serializer.serialize(
                writer,
                building.simulationState,
                gameObjects.GenericSimulationState
            )

#endregion



#region trains

class WagonState(enum.Enum):
    moving = 0
    airborne = 1
    twisting = 2
    flipping = 3
    inQueueForProduction = 4
    producing = 5
    looping = 6
    launchingIntoHub = 7
    loopingFlipped = 8

@dataclass
class WagonNavigationData:
    incomingPosition:gameObjects.GlobalChunkCoordinate
    outgoingPosition:gameObjects.GlobalChunkCoordinate
    incomingDirection:gameObjects.ChunkDirection
    outgoingDirection:gameObjects.ChunkDirection
    upsideDown:bool
    state:WagonState
    travelledChunksInsideJump:float
    jumpLength:float

    # ingame this is stored elsewhere
    # but moved here for convenience
    cargo:gameObjects.LayeredWagonCargo[
        gameObjects.CargoContainer[
            gameObjects.ShapeItem # ShapeId ingame
            | gameObjects.GenericFluid # FluidId ingame
        ]
    ] | None = None
    # not ingame but needed here because the different lists inside `cargo` can be empty
    cargoType:typing.Literal["shape","fluid"] | None = None

class TrainSimulationState(enum.Enum):
    idle = 0
    moving = 1

@dataclass
class TrainSimulationData:
    color:str
    chunkProgress:float
    state:TrainSimulationState
    upsideDown:bool
    wagons:list[WagonNavigationData]
    velocity:float
    maxSpeedAhead:float
    acceleration:float
    chunksUntilMaxSpeedShouldBeRespected:float
    isStopped:bool
    wasStoppedInCurrentChunk:bool
    stopTime:gameObjects.SimulationTicks

@dataclass
class TrainNavigationState:
    data:TrainSimulationData
    occupiedRails:list[gameObjects.SidedCoordinate]

@dataclass
class TrainState:
    navigationState:TrainNavigationState
    parentProducerPosition:gameObjects.GlobalChunkCoordinate

@dataclass
class TrainsSimulation:
    trains:list[TrainState]

def _decodeTrains(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> TrainsSimulation:

    decodedTrains:list[TrainState] = []

    def decodeTrain() -> None:

        reader.assertCheckpoint(Checkpoint.trainData)
        curTrain:TrainState

        @reader.readBlob
        def _():
            nonlocal curTrain

            navState:TrainNavigationState

            @reader.readBlob
            def _():
                nonlocal navState

                def getColor() -> str:
                    color = reader.readString()
                    if color is None:
                        raise InvalidSerializedData("Train color can't be None")
                    return color

                def getSerializedEnum[T:enum.Enum](cls:enum.EnumType[T]) -> T:
                    raw = reader.readInt1()
                    if raw not in cls:
                        raise InvalidSerializedData(f"Invalid value for {cls.__name__} : {raw}")
                    return cls(raw)

                def getWagons() -> list[WagonNavigationData]:
                    wagons = []
                    for i in range(reader.readInt()):
                        try:
                            wagons.append(WagonNavigationData(
                                serializer.deserialize(reader,gameObjects.GlobalChunkCoordinate),
                                serializer.deserialize(reader,gameObjects.GlobalChunkCoordinate),
                                getSerializedEnum(gameObjects.ChunkDirection),
                                getSerializedEnum(gameObjects.ChunkDirection),
                                reader.readBool(),
                                getSerializedEnum(WagonState),
                                reader.readFloat(),
                                reader.readFloat()
                            ))
                        except InvalidSerializedData as e:
                            raise InvalidSerializedData(f"Error while reading wagon #{i} : {e}")
                    return wagons

                navState = TrainNavigationState(
                    TrainSimulationData(
                        getColor(),
                        reader.readFloat(),
                        getSerializedEnum(TrainSimulationState),
                        reader.readBool(),
                        getWagons(),
                        reader.readFloat(),
                        reader.readFloat(),
                        reader.readFloat(),
                        reader.readFloat(),
                        reader.readBool(),
                        reader.readBool(),
                        serializer.deserialize(reader,gameObjects.SimulationTicks)
                    ),
                    [
                        gameObjects.SidedCoordinate(
                            serializer.deserialize(reader,gameObjects.GlobalChunkCoordinate),
                            reader.readBool()
                        )
                        for _ in range(reader.readInt())
                    ]
                )

            curTrain = TrainState(
                navState,
                serializer.deserialize(reader,gameObjects.GlobalChunkCoordinate)
            )

            for text,dataType in (
                ("fluid",gameObjects.GenericFluid), # FluidId ingame
                ("shape",gameObjects.ShapeItem) # ShapeId ingame
            ):

                @reader.readBlob
                def _():

                    for i in range(reader.readInt()):
                        try:

                            wagonIndex = reader.readInt()
                            print(f"TODO : check wagon index range : {wagonIndex}")
                            decodedCargo = serializer.deserialize(
                                reader,
                                gameObjects.LayeredWagonCargo[
                                    gameObjects.CargoContainer[
                                        dataType
                                    ]
                                ]
                            )

                            if (wagonIndex < 0) or (wagonIndex >= len(navState.data.wagons)):
                                raise InvalidSerializedData(f"Wagon index out of range : {wagonIndex}")

                            if navState.data.wagons[wagonIndex].cargo is not None:
                                raise InvalidSerializedData(f"Wagon #{wagonIndex} already has cargo")

                            navState.data.wagons[wagonIndex].cargo = decodedCargo
                            navState.data.wagons[wagonIndex].cargoType = text

                        except InvalidSerializedData as e:
                            raise InvalidSerializedData(f"Error while reading {text} cargo #{i} : {e}")

        decodedTrains.append(curTrain)

    for i in range(reader.readInt()):
        try:
            decodeTrain()
        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading train #{i} : {e}")

    return TrainsSimulation(decodedTrains)

def _encodeTrains(
    trains:TrainsSimulation,
    writer:BinaryStreamWriterWithStringLUT,
    serializer:GameObjectsSerializer
) -> None:

    writer.writeInt(len(trains.trains))

    for train in trains.trains:

        writer.writeCheckpoint(Checkpoint.trainData)

        @writer.writeBlob
        def _():

            simData = train.navigationState.data

            @writer.writeBlob
            def _():

                writer.writeString(simData.color)
                writer.writeFloat(simData.chunkProgress)
                writer.writeInt1(simData.state.value)
                writer.writeBool(simData.upsideDown)
                writer.writeInt(len(simData.wagons))

                for wagon in simData.wagons:
                    serializer.serialize(writer,wagon.incomingPosition)
                    serializer.serialize(writer,wagon.outgoingPosition)
                    writer.writeInt1(wagon.incomingDirection.value)
                    writer.writeInt1(wagon.outgoingDirection.value)
                    writer.writeBool(wagon.upsideDown)
                    writer.writeInt1(wagon.state.value)
                    writer.writeFloat(wagon.travelledChunksInsideJump)
                    writer.writeFloat(wagon.jumpLength)

                writer.writeFloat(simData.velocity)
                writer.writeFloat(simData.maxSpeedAhead)
                writer.writeFloat(simData.acceleration)
                writer.writeFloat(simData.chunksUntilMaxSpeedShouldBeRespected)
                writer.writeBool(simData.isStopped)
                writer.writeBool(simData.wasStoppedInCurrentChunk)
                serializer.serialize(writer,simData.stopTime)

                writer.writeInt(len(train.navigationState.occupiedRails))
                for rail in train.navigationState.occupiedRails:
                    serializer.serialize(writer,rail.coordinate)
                    writer.writeBool(rail.upsideDown)

            serializer.serialize(writer,train.parentProducerPosition)

            for cargoType in ("fluid","shape"):
                @writer.writeBlob
                def _():
                    filteredCargo = []
                    for i,wagon in enumerate(simData.wagons):
                        if wagon.cargoType == cargoType:
                            filteredCargo.append((i,wagon.cargo))
                    writer.writeInt(len(filteredCargo))
                    for wagonIndex,cargo in filteredCargo:
                        writer.writeInt(wagonIndex)
                        serializer.serialize(writer,cargo)

#endregion



#region savegame

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
class SavegameMap:
    temp_simulationState:bytes
    placedIslands:list[PlacedIsland]
    trains:TrainsSimulation
    temp_resourceChunks:bytes
    temp_cargo:bytes

@dataclass
class Savegame:
    map:SavegameMap
    temp_stringsLUT:StringLUTReadWrite # remove when all other parts are done
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

    decodedIslands:list[PlacedIsland] = []

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

    islandsMap = {i.pos:i for i in decodedIslands}

    buildingsMap:dict[gameObjects.GlobalTileCoordinate,PlacedBuilding] = {}
    for decodedIsland in decodedIslands:
        for decodedBuilding in decodedIsland.placedBuildings:
            buildingsMap[
                decodedBuilding.pos.toGlobalTile(decodedIsland.pos)
            ] = decodedBuilding

    for bundleIndex,islandBundle in islandAndBuildingStatesRaw:
        try:
            _decodeIslandStates(
                BinaryStreamReaderWithStringLUT(
                    islandBundle,
                    useCheckpoints,
                    stringsLUT
                ),
                serializer,
                islandsMap,
                buildingsMap
            )
        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading island state bundle #{bundleIndex} : {e}")

    try:
        decodedTrains = _decodeTrains(
            BinaryStreamReaderWithStringLUT(trainsRaw,useCheckpoints,stringsLUT),
            serializer
        )
    except InvalidSerializedData as e:
        raise InvalidSerializedData(f"Error while reading trains : {e}")

    # temp
    return Savegame(
        SavegameMap(
            simulationStateRaw,
            decodedIslands,
            decodedTrains,
            resourceChunksRaw,
            cargoRaw
        ),
        stringsLUT,
        statisticsRaw,
        saveInfoRaw,
        researchRaw,
        playerRaw
    )

def encodeSavegame(savegame:Savegame,file:str|os.PathLike|typing.IO[bytes]) -> None:

    tempSaveInfo = json.loads(savegame.temp_info)
    useCheckpoints = tempSaveInfo["BinaryDataCheckpoints"]
    tempScenario = research.ingameScenarios[tempSaveInfo["Parameters"]["ScenarioParameters"]["ScenarioId"]]
    serializer = GameObjectsSerializer(
        tempScenario.researchConfig.shapesConfig,
        tempScenario.researchConfig.colorScheme
    )
    stringsLUT = savegame.temp_stringsLUT

    islandsToEncode = savegame.map.placedIslands.copy()
    maxIslandsPerBundle = math.ceil(4**math.log10(len(islandsToEncode)))
    assert (maxIslandsPerBundle > 0) or (len(islandsToEncode) == 0)

    encodedPlacedIslands:list[tuple[int,bytes]] = []
    encodedIslandAndBuildingStates:list[tuple[int,bytes]] = []

    curBundle = []
    curBundleIndex = 0
    lastBundle = False
    while not lastBundle:

        if len(islandsToEncode) == 0:
            lastBundle = True
        else:
            curBundle.append(islandsToEncode.pop(0))

        if (len(curBundle) >= maxIslandsPerBundle) or (lastBundle and (len(curBundle) > 0)):

            placedIslandsWriter = BinaryStreamWriterWithStringLUT(useCheckpoints,stringsLUT)
            _encodeIslands(curBundle,placedIslandsWriter,serializer)
            encodedPlacedIslands.append((
                curBundleIndex,
                placedIslandsWriter.toBytes()
            ))

            islandStatesWriter = BinaryStreamWriterWithStringLUT(useCheckpoints,stringsLUT)
            _encodeIslandStates(curBundle,islandStatesWriter,serializer)
            encodedIslandAndBuildingStates.append((
                curBundleIndex,
                islandStatesWriter.toBytes()
            ))

            curBundleIndex += 1
            curBundle.clear()

    trainsWriter = BinaryStreamWriterWithStringLUT(useCheckpoints,stringsLUT)
    _encodeTrains(savegame.map.trains,trainsWriter,serializer)
    encodedTrains = trainsWriter.toBytes()

    encodedStringsLUT = BinaryStreamWriter(useCheckpoints)
    savegame.temp_stringsLUT.serialize(encodedStringsLUT)

    with zipfile.ZipFile(file,"w") as f:
        f.writestr(FilePaths.stringsLUT,encodedStringsLUT.toBytes())
        f.writestr(FilePaths.statistics,savegame.temp_statistics)
        f.writestr(FilePaths.saveInfo,savegame.temp_info)
        f.writestr(FilePaths.research,savegame.temp_research)
        f.writestr(FilePaths.player,savegame.temp_player)
        f.writestr(FilePaths.simulationState,savegame.map.temp_simulationState)
        f.writestr(FilePaths.trains,encodedTrains)
        f.writestr(FilePaths.resourceChunks,savegame.map.temp_resourceChunks)
        f.writestr(FilePaths.cargo,savegame.map.temp_cargo)
        for fileList,prefix,suffix in [
            (
                encodedPlacedIslands,
                FilePaths.placedIslandsPrefix,
                FilePaths.placedIslandsSuffix
            ),
            (
                encodedIslandAndBuildingStates,
                FilePaths.islandAndBuildingStatesPrefix,
                FilePaths.islandAndBuildingStatesSuffix
            )
        ]:
            for i,data in fileList:
                f.writestr(prefix.value+str(i)+suffix.value,data)

#endregion



# region files

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

#endregion