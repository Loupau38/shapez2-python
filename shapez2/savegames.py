from . import buildings, gameObjects, utils, islands, _gameObjectsSerializer, research, savegameObjects
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
import collections.abc



#region map

@dataclass
class PlacedBuilding:
    type:buildings.BuildingInternalVariant
    pos:savegameObjects.IslandTileCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.GenericBuildingConfig|None
    simulationState:savegameObjects.GenericSimulationState|None=None

@dataclass
class PlacedIsland:
    type:islands.Island
    pos:savegameObjects.GlobalChunkCoordinate
    rotation:utils.Rotation
    configuration:gameObjects.GenericIslandConfig|None
    placedBuildings:list[PlacedBuilding]
    simulationState:savegameObjects.GenericSimulationState|None=None

def _decodeBuildings(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> list[PlacedBuilding]:

    decodedBuildings = []
    reader.assertCheckpoint(Checkpoint.buildings)

    def decodeBuilding() -> None:

        reader.assertCheckpoint(Checkpoint.building)
        buildingPos = serializer.deserialize(reader,savegameObjects.IslandTileCoordinate)
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
        islandPos = serializer.deserialize(reader,savegameObjects.GlobalChunkCoordinate)
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
    islandsMap:dict[savegameObjects.GlobalChunkCoordinate,PlacedIsland],
    buildingsMap:dict[savegameObjects.GlobalTileCoordinate,PlacedBuilding]
) -> None:

    def decodeIsland() -> None:

        islandPos = serializer.deserialize(reader,savegameObjects.GlobalChunkCoordinate)
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
            placedIsland.simulationState = serializer.deserialize(reader,savegameObjects.GenericSimulationState)

    def decodeBuilding() -> None:

        buildingPos = serializer.deserialize(reader,savegameObjects.GlobalTileCoordinate)
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
            placedBuilding.simulationState = serializer.deserialize(reader,savegameObjects.GenericSimulationState)

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
    placedBuildings:list[tuple[savegameObjects.GlobalTileCoordinate,PlacedBuilding]] = []

    for island in islands:

        serializer.serialize(writer,island.pos)
        serializer.serialize(writer,island.type)

        @writer.writeBlob
        def _():
            serializer.serialize(
                writer,
                island.simulationState,
                savegameObjects.GenericSimulationState
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
                savegameObjects.GenericSimulationState
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
    incomingPosition:savegameObjects.GlobalChunkCoordinate
    outgoingPosition:savegameObjects.GlobalChunkCoordinate
    incomingDirection:savegameObjects.ChunkDirection
    outgoingDirection:savegameObjects.ChunkDirection
    upsideDown:bool
    state:WagonState
    travelledChunksInsideJump:float
    jumpLength:float

    # ingame this is stored elsewhere
    # but moved here for convenience
    cargo:savegameObjects.LayeredWagonCargo[
        savegameObjects.CargoContainer[
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
    stopTime:savegameObjects.SimulationTicks

@dataclass
class TrainNavigationState:
    data:TrainSimulationData
    occupiedRails:list[savegameObjects.SidedCoordinate]

@dataclass
class TrainState:
    navigationState:TrainNavigationState
    parentProducerPosition:savegameObjects.GlobalChunkCoordinate

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
                                serializer.deserialize(reader,savegameObjects.GlobalChunkCoordinate),
                                serializer.deserialize(reader,savegameObjects.GlobalChunkCoordinate),
                                getSerializedEnum(savegameObjects.ChunkDirection),
                                getSerializedEnum(savegameObjects.ChunkDirection),
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
                        serializer.deserialize(reader,savegameObjects.SimulationTicks)
                    ),
                    [
                        savegameObjects.SidedCoordinate(
                            serializer.deserialize(reader,savegameObjects.GlobalChunkCoordinate),
                            reader.readBool()
                        )
                        for _ in range(reader.readInt())
                    ]
                )

            curTrain = TrainState(
                navState,
                serializer.deserialize(reader,savegameObjects.GlobalChunkCoordinate)
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
                                savegameObjects.LayeredWagonCargo[
                                    savegameObjects.CargoContainer[
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



#region cargo

@dataclass
class CargoExchangingController[
    TWagonData,
    TLoader:savegameObjects.GenericCargoExchanger[TWagonData],
    TUnloader:savegameObjects.GenericCargoExchanger[TWagonData],
    TTransferrer:savegameObjects.GenericCargoTransferrer[TWagonData]
]:
    cargoLoaderMap:dict[savegameObjects.GlobalChunkCoordinate,TLoader]
    cargoUnloaderMap:dict[savegameObjects.GlobalChunkCoordinate,TUnloader]
    cargoTransferrerMap:dict[savegameObjects.GlobalChunkCoordinate,TTransferrer]

@dataclass
class CargoExchangingOrchestrator:
    shapeCargoLoaderUnloader:CargoExchangingController[
        savegameObjects.LayeredWagonCargo[savegameObjects.CargoContainer[gameObjects.ShapeItem]], # ShapeId ingame
        savegameObjects.TrainCargoLoaderSimulation[gameObjects.ShapeItem], # ShapeId ingame
        savegameObjects.TrainCargoUnloaderSimulation[gameObjects.ShapeItem], # ShapeId ingame
        savegameObjects.TrainCargoTransferrerSimulation[gameObjects.ShapeItem] # ShapeId ingame
    ]
    fluidCargoLoaderUnloader:CargoExchangingController[
        savegameObjects.LayeredWagonCargo[savegameObjects.CargoContainer[gameObjects.GenericFluid]], # FluidId ingame
        savegameObjects.TrainCargoLoaderSimulation[gameObjects.GenericFluid], # FluidId ingame
        savegameObjects.TrainCargoUnloaderSimulation[gameObjects.GenericFluid], # FluidId ingame
        savegameObjects.TrainCargoTransferrerSimulation[gameObjects.GenericFluid] # FluidId ingame
    ]

def _decodeCargo(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> CargoExchangingOrchestrator:

    cargo = CargoExchangingOrchestrator(
        CargoExchangingController({},{},{}),
        CargoExchangingController({},{},{})
    )

    @reader.readBlob
    def _():

        for simType,stateType,cargoMaps,islandName in [
            (
                savegameObjects.TrainCargoLoaderSimulation,
                savegameObjects.TrainCargoExchangerState,
                (
                    cargo.shapeCargoLoaderUnloader.cargoLoaderMap,
                    cargo.fluidCargoLoaderUnloader.cargoLoaderMap
                ),
                "loader"
            ),
            (
                savegameObjects.TrainCargoUnloaderSimulation,
                savegameObjects.TrainCargoExchangerState,
                (
                    cargo.shapeCargoLoaderUnloader.cargoUnloaderMap,
                    cargo.fluidCargoLoaderUnloader.cargoUnloaderMap
                ),
                "unloader"
            ),
            (
                savegameObjects.TrainCargoTransferrerSimulation,
                savegameObjects.TrainCargoTransferState,
                (
                    cargo.shapeCargoLoaderUnloader.cargoTransferrerMap,
                    cargo.fluidCargoLoaderUnloader.cargoTransferrerMap
                ),
                "transferrer"
            )
        ]:

            for cargoMap,cargoType,cargoName in [
                (cargoMaps[0],gameObjects.ShapeItem,"shape"),
                (cargoMaps[1],gameObjects.GenericFluid,"fluid")
            ]:

                for i in range(reader.readInt()):

                    try:

                        pos = serializer.deserialize(reader,savegameObjects.GlobalChunkCoordinate)

                        @reader.readBlob
                        def _():
                            cargoMap[pos] = simType(serializer.deserialize(reader,stateType[cargoType]))

                    except InvalidSerializedData as e:
                        raise InvalidSerializedData(f"Error while reading {cargoName} {islandName} #{i} : {e}")

    return cargo

def _encodeCargo(
    cargo:CargoExchangingOrchestrator,
    writer:BinaryStreamWriterWithStringLUT,
    serializer:GameObjectsSerializer
) -> None:

    @writer.writeBlob
    def _():

        for cargoMap in [
            cargo.shapeCargoLoaderUnloader.cargoLoaderMap,
            cargo.fluidCargoLoaderUnloader.cargoLoaderMap,
            cargo.shapeCargoLoaderUnloader.cargoUnloaderMap,
            cargo.fluidCargoLoaderUnloader.cargoUnloaderMap,
            cargo.shapeCargoLoaderUnloader.cargoTransferrerMap,
            cargo.fluidCargoLoaderUnloader.cargoTransferrerMap
        ]:

            cargoMap:dict[
                savegameObjects.GlobalChunkCoordinate,
                savegameObjects.TrainCargoLoaderSimulation
                | savegameObjects.TrainCargoUnloaderSimulation
                | savegameObjects.TrainCargoTransferrerSimulation
            ]

            writer.writeInt(len(cargoMap))
            for pos,sim in cargoMap.items():
                serializer.serialize(writer,pos)
                @writer.writeBlob
                def _():
                    # contained type for TrainCargoExchangerState and
                    # TrainCargoTransferState ignored on serialization
                    serializer.serialize(writer,sim.state)

#endregion



#region simulation state

@dataclass
class SignalChannelRegistry:
    dynamicChannels:dict[gameObjects.SignalChannelId,savegameObjects.SignalChannelRingBuffer]

def _decodeSimulationState(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> tuple[savegameObjects.SimulationTicks,SignalChannelRegistry]:

    simTime = serializer.deserialize(reader,savegameObjects.SimulationTicks)
    registry = SignalChannelRegistry({})

    for i in range(reader.readInt()):
        try:

            channelId = serializer.deserialize(reader,gameObjects.SignalChannelId)
            @reader.readBlob
            def _():
                registry.dynamicChannels[channelId] = savegameObjects.SignalChannelRingBuffer(
                    serializer.deserialize(reader,savegameObjects.SignalChannelRingBufferState)
                )

        except InvalidSerializedData as e:
            raise InvalidSerializedData(f"Error while reading channel #{i} : {e}")

    return simTime, registry

def _encodeSimulationState(
    simTime:savegameObjects.SimulationTicks,
    registry:SignalChannelRegistry,
    writer:BinaryStreamWriterWithStringLUT,
    serializer:GameObjectsSerializer
) -> None:

    serializer.serialize(writer,simTime)

    writer.writeInt(len(registry.dynamicChannels))
    for channelId,channel in registry.dynamicChannels.items():
        serializer.serialize(writer,channelId)
        @writer.writeBlob
        def _():
            serializer.serialize(writer,channel.state)

#endregion



#region resource chunks

@dataclass
class GenericMapResourceSource:
    origin:savegameObjects.GlobalChunkCoordinate
    chunks:list[utils.Pos] # ChunkVector ingame

@dataclass
class ShapeMapResourceSource(GenericMapResourceSource):
    definitions:list[gameObjects.Shape] # ShapeDefinition ingame

@dataclass
class FluidMapResourceSource(GenericMapResourceSource):
    fluid:gameObjects.GenericFluid

@dataclass
class MapSuperChunk:
    pos:savegameObjects.SuperChunkCoordinate
    resources:list[GenericMapResourceSource]

@dataclass
class GameResourcesMap:
    superChunks:dict[savegameObjects.SuperChunkCoordinate,MapSuperChunk]

def _decodeResourceChunks(
    reader:BinaryStreamReaderWithStringLUT,
    serializer:GameObjectsSerializer
) -> GameResourcesMap:

    resourcesMap = GameResourcesMap({})

    for superChunkIndex in range(reader.readInt()):
        try:

            reader.assertCheckpoint(Checkpoint.superChunkStart)
            superChunkPos = savegameObjects.SuperChunkCoordinate(
                reader.readInt(),
                reader.readInt()
            )

            if superChunkPos in resourcesMap.superChunks:
                raise InvalidSerializedData(f"Duplicate super chunk : {superChunkPos}")

            resources:list[GenericMapResourceSource] = []

            @reader.readBlob
            def _():

                reader.assertCheckpoint(Checkpoint.superChunkShapeResources)

                for resourceIndex in range(reader.readInt()):
                    try:

                        resourceType = reader.readInt1()
                        if resourceType != 1:
                            raise InvalidSerializedData(
                                f"Invalid resource type : {resourceType}"
                            )

                        resourceOrigin = serializer.deserialize(
                            reader,
                            savegameObjects.GlobalChunkCoordinate
                        )
                        numDefinitions = reader.readInt()
                        definitions:list[gameObjects.Shape] = []

                        for defIndex in range(numDefinitions):
                            try:
                                definitions.append(serializer.deserialize(
                                    reader,
                                    gameObjects.Shape
                                ))
                            except InvalidSerializedData as e:
                                raise InvalidSerializedData(
                                    f"Error while reading shape definition #{defIndex} : {e}"
                                )

                        chunks:list[utils.Pos] = []
                        for chunkIndex in range(numDefinitions):
                            try:
                                chunks.append(utils.Pos(
                                    reader.readInt(),
                                    reader.readInt(),
                                    0
                                ))
                            except InvalidSerializedData as e:
                                raise InvalidSerializedData(
                                    f"Error while reading chunk #{chunkIndex} : {e}"
                                )

                        resources.append(ShapeMapResourceSource(
                            resourceOrigin,
                            chunks,
                            definitions
                        ))

                    except InvalidSerializedData as e:
                        raise InvalidSerializedData(
                            f"Error while reading shape resource #{resourceIndex} : {e}"
                        )

                reader.assertCheckpoint(Checkpoint.superChunkFluidResources)

                for resourceIndex in range(reader.readInt()):
                    try:

                        resourceType = reader.readInt1()
                        if resourceType != 1:
                            raise InvalidSerializedData(
                                f"Invalid resource type : {resourceType}"
                            )

                        resourceOrigin = serializer.deserialize(
                            reader,
                            savegameObjects.GlobalChunkCoordinate
                        )

                        fluid = serializer.deserialize(reader,gameObjects.GenericFluid)
                        numChunks = reader.readInt()
                        chunks:list[utils.Pos] = []

                        for chunkIndex in range(numChunks):
                            try:
                                chunks.append(utils.Pos(
                                    reader.readInt(),
                                    reader.readInt(),
                                    0
                                ))
                            except InvalidSerializedData as e:
                                raise InvalidSerializedData(
                                    f"Error while reading chunk #{chunkIndex} : {e}"
                                )

                        resources.append(FluidMapResourceSource(
                            resourceOrigin,
                            chunks,
                            fluid
                        ))

                    except InvalidSerializedData as e:
                        raise InvalidSerializedData(
                            f"Error while reading fluid resource #{resourceIndex} : {e}"
                        )

            resourcesMap.superChunks[superChunkPos] = MapSuperChunk(superChunkPos,resources)

        except InvalidSerializedData as e:
            raise InvalidSerializedData(
                f"Error while reading super chunk #{superChunkIndex} : {e}"
            )

    return resourcesMap

def _encodeResourceChunks(
    resourcesMap:GameResourcesMap,
    writer:BinaryStreamWriterWithStringLUT,
    serializer:GameObjectsSerializer
) -> None:

    writer.writeInt(len(resourcesMap.superChunks))

    for superChunk in resourcesMap.superChunks.values():

        writer.writeCheckpoint(Checkpoint.superChunkStart)
        writer.writeInt(superChunk.pos.x)
        writer.writeInt(superChunk.pos.y)

        @writer.writeBlob
        def _():

            writer.writeCheckpoint(Checkpoint.superChunkShapeResources)
            shapeResources = [r for r in superChunk.resources if isinstance(r,ShapeMapResourceSource)]
            writer.writeInt(len(shapeResources))

            for resource in shapeResources:

                writer.writeInt1(1)
                serializer.serialize(writer,resource.origin)
                writer.writeInt(len(resource.definitions))

                for shapeDef in resource.definitions:
                    serializer.serialize(writer,shapeDef)

                if len(resource.definitions) != len(resource.chunks):
                    raise ValueError(
                        "Different number of shape definitions and chunks in "
                        + ShapeMapResourceSource.__name__
                    )

                for chunk in resource.chunks:
                    writer.writeInt(chunk.x)
                    writer.writeInt(chunk.y)

            writer.writeCheckpoint(Checkpoint.superChunkFluidResources)
            fluidResources = [r for r in superChunk.resources if isinstance(r,FluidMapResourceSource)]
            writer.writeInt(len(fluidResources))

            for resource in fluidResources:

                writer.writeInt1(1)
                serializer.serialize(writer,resource.origin)
                serializer.serialize(writer,resource.fluid,gameObjects.GenericFluid)
                writer.writeInt(len(resource.chunks))

                for chunk in resource.chunks:
                    writer.writeInt(chunk.x)
                    writer.writeInt(chunk.y)

#endregion



#region statistics

# the classes in this section have a structure closer to
# the ingame ones (i.e. serialization methods directly here)
# for simplicity of recreating the correct behaviors

@dataclass
class SerializationEntry:
    deliveredTime:savegameObjects.SimulationTicks
    amount:int

class GenericStatisticsBucketSerializer[T]:

    def serialize(
        self,
        writer:BinaryStreamWriter,
        serializer:GameObjectsSerializer,
        value:T
    ) -> None: ...

    def deserialize(
        self,
        reader:BinaryStreamReader,
        serializer:GameObjectsSerializer
    ) -> T: ...

# Shape -> UnifiedShapeId ingame
class StatisticsBucketShapeSerializer(
    GenericStatisticsBucketSerializer[gameObjects.Shape]
):

    def serialize(self,writer,serializer,value):
        # serialized as ShapeId ingame
        serializer.serialize(writer,gameObjects.ShapeItem(value))

    def deserialize(self,reader,serializer):
        # deserialized from ShapeId ingame
        return serializer.deserialize(reader,gameObjects.ShapeItem).shape

class StatisticsBucketRocketGroupIdSerializer(
    GenericStatisticsBucketSerializer[savegameObjects.RocketGroupId]
):

    def serialize(self,writer,serializer,value):
        writer.writeString(value.id)

    def deserialize(self,reader,serializer):
        return savegameObjects.RocketGroupId(reader.readString())

class StatisticsStream[T:collections.abc.Hashable]:

    def __init__(self) -> None:
        # ingame the entries are stored differently
        # and this dict is computed on serialization
        self.entries = dict[T,list[SerializationEntry]]()

    def serialize(
        self,
        writer:BinaryStreamWriter,
        serializer:GameObjectsSerializer,
        containedTypeSerializer:GenericStatisticsBucketSerializer[T]
    ) -> None:

        numEntries = sum(len(l) for l in self.entries.values())
        writer.writeInt(numEntries)
        writer.writeInt(len(self.entries))

        for key,serializationEntries in self.entries.items():

            containedTypeSerializer.serialize(writer,serializer,key)
            writer.writeInt(len(serializationEntries))

            for entry in serializationEntries:
                serializer.serialize(writer,entry.deliveredTime)

                if entry.amount > 255:
                    raise ValueError(
                        "Amount too big for "
                        + SerializationEntry.__name__
                        + f" : {entry.amount}"
                    )

                writer.writeInt1(entry.amount)

    def deserialize(
        self,
        reader:BinaryStreamReader,
        serializer:GameObjectsSerializer,
        containedTypeSerializer:GenericStatisticsBucketSerializer[T]
    ) -> None:

        self.entries.clear()
        totalNumEntries = reader.readInt()
        numEntries = reader.readInt()

        if (numEntries == 0) or (totalNumEntries == 0):
            return

        for entriesIndex in range(numEntries):
            try:

                dictKey = containedTypeSerializer.deserialize(reader,serializer)

                if dictKey in self.entries:
                    entriesList = self.entries[dictKey]
                else:
                    entriesList = []
                    self.entries[dictKey] = entriesList

                for serializationEntryIndex in range(reader.readInt()):
                    try:
                        entriesList.append(SerializationEntry(
                            serializer.deserialize(reader,savegameObjects.SimulationTicks),
                            reader.readInt1()
                        ))
                    except InvalidSerializedData as e:
                        raise InvalidSerializedData(
                            f"Error while reading serialization entry #{serializationEntryIndex} : {e}"
                        )

            except InvalidSerializedData as e:
                raise InvalidSerializedData(
                    f"Error while reading entries list #{entriesIndex} : {e}"
                )

class GenericStatisticsTracker[T]:

    # ingame these are from IStatisticsStream
    # which IStatisticsTracker inherits from

    def serialize(
        self,
        writer:BinaryStreamWriter,
        serializer:GameObjectsSerializer,
        containedTypeSerializer:GenericStatisticsBucketSerializer[T]
    ) -> None: ...

    def deserialize(
        self,
        reader:BinaryStreamReader,
        serializer:GameObjectsSerializer,
        containedTypeSerializer:GenericStatisticsBucketSerializer[T]
    ) -> None: ...

class StatisticsBucket[T:collections.abc.Hashable]:

    def __init__(self) -> None:
        self.counts:dict[T,int] = {}

    def serialize(
        self,
        writer:BinaryStreamWriter,
        serializer:GameObjectsSerializer,
        containedTypeSerializer:GenericStatisticsBucketSerializer[T]
    ) -> None:
        writer.writeInt(len(self.counts))
        for k,v in self.counts.items():
            containedTypeSerializer.serialize(writer,serializer,k)
            writer.writeLong(v)

    def deserialize(
        self,
        reader:BinaryStreamReader,
        serializer:GameObjectsSerializer,
        containedTypeSerializer:GenericStatisticsBucketSerializer[T]
    ) -> None:

        self.counts.clear()
        for i in range(reader.readInt()):
            try:
                key = containedTypeSerializer.deserialize(reader,serializer)
                self.counts[key] = reader.readLong()
            except InvalidSerializedData as e:
                raise InvalidSerializedData(f"Error while reading count #{i} : {e}")

class IntervalBasedStatisticsTracker[T](GenericStatisticsTracker[T]):

    def __init__(
        self,
        interval:savegameObjects.SimulationTicks,
        maxBucketHistory:int
    ) -> None:
        self.interval = interval
        self.maxBucketHistory = maxBucketHistory
        self.buckets = [StatisticsBucket[T]() for _ in range(maxBucketHistory)]
        self.lastBucketIndex = 0

    def serialize(self,writer,serializer,containedTypeSerializer):

        writer.writeInt(self.lastBucketIndex)
        writer.writeInt(self.maxBucketHistory)
        # TicksSerializer not used ingame
        writer.writeLong(self.interval.value)
        writer.writeInt(len(self.buckets))

        @writer.writeBlob
        def _():
            for bucket in self.buckets:
                bucket.serialize(writer,serializer,containedTypeSerializer)

    def deserialize(self,reader,serializer,containedTypeSerializer):

        self.lastBucketIndex = reader.readInt()

        maxBucketHistory = reader.readInt()
        if maxBucketHistory != self.maxBucketHistory:
            raise InvalidSerializedData(
                f"Invalid max bucket history, expected {self.maxBucketHistory}, got {maxBucketHistory}"
            )

        # TicksSerializer not used ingame
        interval = reader.readLong()
        if interval != self.interval.value:
            raise InvalidSerializedData(
                f"Invalid interval, expected {self.interval.value}, got {interval}"
            )

        self.buckets.clear()
        numBuckets = reader.readInt()

        @reader.readBlob
        def _():
            for i in range(numBuckets):
                try:
                    self.buckets[i].deserialize(reader,serializer,containedTypeSerializer)
                except InvalidSerializedData as e:
                    raise InvalidSerializedData(f"Error while reading bucket #{i} : {e}")

class AggregatedStatisticsTracker[T](GenericStatisticsTracker[T]):

    def __init__(self) -> None:
        self.bucket = StatisticsBucket[T]()

    def serialize(self,writer,serializer,containedTypeSerializer):
        self.bucket.serialize(writer,serializer,containedTypeSerializer)

    def deserialize(self,reader,serializer,containedTypeSerializer):
        self.bucket.deserialize(reader,serializer,containedTypeSerializer)

class SlidingWindowStatisticsStreamBucket:

    def serialize(self,writer:BinaryStreamWriter) -> None:
        writer.writeInt(self.entriesStartIndex)
        writer.writeInt(self.entriesCount)

    def deserialize(self,reader:BinaryStreamReader) -> None:
        self.entriesStartIndex = reader.readInt()
        self.entriesCount = reader.readInt()

class SlidingWindowStatisticsStreamView[T](GenericStatisticsTracker[T]):

    def __init__(self,maxBuckets:int) -> None:
        self.buckets = [
            SlidingWindowStatisticsStreamBucket()
            for _ in range(maxBuckets)
        ]

    def serialize(self,writer,serializer,containedTypeSerializer):
        writer.writeInt(len(self.buckets))
        for b in self.buckets:
            b.serialize(writer)

    def deserialize(self,reader,serializer,containedTypeSerializer):

        numBuckets = reader.readInt()
        if numBuckets != len(self.buckets):
            raise InvalidSerializedData(
                f"Invalid number of buckets, expected {len(self.buckets)}, got {numBuckets}"
            )

        for b in self.buckets:
            b.deserialize(reader)

class GameStatisticsTrackerInterval(enum.Enum):
    oneSecond = 1
    fiveSeconds = 5
    oneMinute = 60
    fiveMinutes = 5 * 60
    oneHour = 60 * 60

class GameStatisticsTrackerSlidingWindowDuration(enum.Enum):
    oneSecond = 1
    fiveSeconds = 5
    oneMinute = 60

class GameStatisticsTracker:

    INTERVAL_TRACKER_HISTORY_SIZE = 32
    SLIDING_WINDOW_TRACKER_HISTORY_SIZE = 1
    INTERVALS = list(GameStatisticsTrackerInterval)
    SLIDING_WINDOW_DURATIONS = list(GameStatisticsTrackerSlidingWindowDuration)

    def __init__(self) -> None:

        self.shapeStatisticsStream = StatisticsStream[gameObjects.Shape]() # UnifiedShapeId ingame
        self.rocketStatisticsStream = StatisticsStream[savegameObjects.RocketGroupId]()

        self.shapeDeliveryTrackers = list[GenericStatisticsTracker[gameObjects.Shape]]() # UnifiedShapeId ingame
        self.rocketDeliveryTrackers = list[GenericStatisticsTracker[savegameObjects.RocketGroupId]]()

        for interval in GameStatisticsTracker.INTERVALS:
            intervalTicks = savegameObjects.SimulationTicks.fromSeconds(interval.value)
            self.shapeDeliveryTrackers.append(IntervalBasedStatisticsTracker(
                intervalTicks,
                GameStatisticsTracker.INTERVAL_TRACKER_HISTORY_SIZE
            ))
            self.rocketDeliveryTrackers.append(IntervalBasedStatisticsTracker(
                intervalTicks,
                GameStatisticsTracker.INTERVAL_TRACKER_HISTORY_SIZE
            ))

        self.shapeDeliveryTrackers.append(AggregatedStatisticsTracker())
        self.rocketDeliveryTrackers.append(AggregatedStatisticsTracker())

        # duration unused for serialization
        for _ in GameStatisticsTracker.SLIDING_WINDOW_DURATIONS:
            self.shapeDeliveryTrackers.append(SlidingWindowStatisticsStreamView(
                GameStatisticsTracker.SLIDING_WINDOW_TRACKER_HISTORY_SIZE
            ))
            self.rocketDeliveryTrackers.append(SlidingWindowStatisticsStreamView(
                GameStatisticsTracker.SLIDING_WINDOW_TRACKER_HISTORY_SIZE
            ))

    def serialize(
        self,
        writer:BinaryStreamWriter,
        serializer:GameObjectsSerializer
    ) -> None:

        for statisticsStream,deliveryTrackers,typeSerializer in [
            (
                self.shapeStatisticsStream,
                self.shapeDeliveryTrackers,
                StatisticsBucketShapeSerializer()
            ),
            (
                self.rocketStatisticsStream,
                self.rocketDeliveryTrackers,
                StatisticsBucketRocketGroupIdSerializer()
            )
        ]:

            statisticsStream:StatisticsStream
            deliveryTrackers:list[GenericStatisticsTracker]
            typeSerializer:GenericStatisticsBucketSerializer

            @writer.writeBlob
            def _():

                @writer.writeBlob
                def _():
                    statisticsStream.serialize(writer,serializer,typeSerializer)

                writer.writeInt(len(deliveryTrackers))
                for tracker in deliveryTrackers:
                    @writer.writeBlob
                    def _():
                        tracker.serialize(writer,serializer,typeSerializer)

    def deserialize(
        self,
        reader:BinaryStreamReader,
        serializer:GameObjectsSerializer
    ) -> None:

        for statisticsStream,deliveryTrackers,typeSerializer,text in [
            (
                self.shapeStatisticsStream,
                self.shapeDeliveryTrackers,
                StatisticsBucketShapeSerializer(),
                "shape"
            ),
            (
                self.rocketStatisticsStream,
                self.rocketDeliveryTrackers,
                StatisticsBucketRocketGroupIdSerializer(),
                "rocket"
            )
        ]:

            statisticsStream:StatisticsStream
            deliveryTrackers:list[GenericStatisticsTracker]
            typeSerializer:GenericStatisticsBucketSerializer
            text:str

            @reader.readBlob
            def _():

                try:
                    @reader.readBlob
                    def _():
                        statisticsStream.deserialize(reader,serializer,typeSerializer)
                except InvalidSerializedData as e:
                    raise InvalidSerializedData(
                        f"Error while reading {text} statistics stream : {e}"
                    )

                numTrackers = reader.readInt()
                if numTrackers != len(deliveryTrackers):
                    raise InvalidSerializedData(
                        f"Invalid number of {text} delivery trackers, "
                        + f"expected {len(deliveryTrackers)}, got {numTrackers}"
                    )

                for i in range(numTrackers):
                    try:
                        @reader.readBlob
                        def _():
                            deliveryTrackers[i].deserialize(reader,serializer,typeSerializer)
                    except InvalidSerializedData as e:
                        raise InvalidSerializedData(
                            f"Error while reading {text} delivery tracker #{i} : {e}"
                        )

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
    simulationTime:savegameObjects.SimulationTicks
    simulationState:SignalChannelRegistry
    placedIslands:list[PlacedIsland]
    trains:TrainsSimulation
    resourceChunks:GameResourcesMap
    cargo:CargoExchangingOrchestrator

@dataclass
class Savegame:
    map:SavegameMap
    statistics:GameStatisticsTracker
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
        stringsLUTRaw = f.read(FilePaths.stringsLUT.value)
        statisticsRaw = f.read(FilePaths.statistics.value)
        saveInfoRaw = f.read(FilePaths.saveInfo.value)
        researchRaw = f.read(FilePaths.research.value)
        playerRaw = f.read(FilePaths.player.value)
        simulationStateRaw = f.read(FilePaths.simulationState.value)
        trainsRaw = f.read(FilePaths.trains.value)
        resourceChunksRaw = f.read(FilePaths.resourceChunks.value)
        cargoRaw = f.read(FilePaths.cargo.value)
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

    buildingsMap:dict[savegameObjects.GlobalTileCoordinate,PlacedBuilding] = {}
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

    try:
        decodedCargo = _decodeCargo(
            BinaryStreamReaderWithStringLUT(cargoRaw,useCheckpoints,stringsLUT),
            serializer
        )
    except InvalidSerializedData as e:
        raise InvalidSerializedData(f"Error while reading cargo : {e}")

    try:
        decodedSimTime, decodedSimState = _decodeSimulationState(
            BinaryStreamReaderWithStringLUT(simulationStateRaw,useCheckpoints,stringsLUT),
            serializer
        )
    except InvalidSerializedData as e:
        raise InvalidSerializedData(f"Error while reading simulation state : {e}")

    try:
        decodedResourceChunks = _decodeResourceChunks(
            BinaryStreamReaderWithStringLUT(resourceChunksRaw,useCheckpoints,stringsLUT),
            serializer
        )
    except InvalidSerializedData as e:
        raise InvalidSerializedData(f"Error while reading resource chunks : {e}")

    decodedStatistics = GameStatisticsTracker()
    try:
        decodedStatistics.deserialize(
            BinaryStreamReaderWithStringLUT(statisticsRaw,useCheckpoints,stringsLUT),
            serializer
        )
    except InvalidSerializedData as e:
        raise InvalidSerializedData(f"Error while reading statistics : {e}")

    # temp
    return Savegame(
        SavegameMap(
            decodedSimTime,
            decodedSimState,
            decodedIslands,
            decodedTrains,
            decodedResourceChunks,
            decodedCargo
        ),
        decodedStatistics,
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
    stringsLUT = StringLUTReadWrite()

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

    cargoWriter = BinaryStreamWriterWithStringLUT(useCheckpoints,stringsLUT)
    _encodeCargo(savegame.map.cargo,cargoWriter,serializer)
    encodedCargo = cargoWriter.toBytes()

    simStateWriter = BinaryStreamWriterWithStringLUT(useCheckpoints,stringsLUT)
    _encodeSimulationState(
        savegame.map.simulationTime,
        savegame.map.simulationState,
        simStateWriter,
        serializer
    )
    encodedSimState = simStateWriter.toBytes()

    resourceChunksWriter = BinaryStreamWriterWithStringLUT(useCheckpoints,stringsLUT)
    _encodeResourceChunks(savegame.map.resourceChunks,resourceChunksWriter,serializer)
    encodedResourceChunks = resourceChunksWriter.toBytes()

    statisticsWriter = BinaryStreamWriterWithStringLUT(useCheckpoints,stringsLUT)
    savegame.statistics.serialize(statisticsWriter,serializer)
    encodedStatistics = statisticsWriter.toBytes()

    stringsLUTWriter = BinaryStreamWriter(useCheckpoints)
    stringsLUT.serialize(stringsLUTWriter)
    encodedStringsLUT = stringsLUTWriter.toBytes()

    with zipfile.ZipFile(file,"w") as f:
        f.writestr(FilePaths.stringsLUT.value,encodedStringsLUT)
        f.writestr(FilePaths.statistics.value,encodedStatistics)
        f.writestr(FilePaths.saveInfo.value,savegame.temp_info)
        f.writestr(FilePaths.research.value,savegame.temp_research)
        f.writestr(FilePaths.player.value,savegame.temp_player)
        f.writestr(FilePaths.simulationState.value,encodedSimState)
        f.writestr(FilePaths.trains.value,encodedTrains)
        f.writestr(FilePaths.resourceChunks.value,encodedResourceChunks)
        f.writestr(FilePaths.cargo.value,encodedCargo)
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