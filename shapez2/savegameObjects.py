from . import utils, islands, gameObjects
from ._gameObjectsSerializer import serializationId as _serializationId

import typing
from dataclasses import dataclass
import enum
import math

#region misc

class GlobalTileCoordinate(utils.Pos):

    def toIslandTile(self,islandPos:"GlobalChunkCoordinate") -> "IslandTileCoordinate":
        islandOrigin = islandPos.tileOrigin()
        return IslandTileCoordinate(
            self.x - islandOrigin.x,
            self.y - islandOrigin.y,
            self.z - islandOrigin.z
        )

    def containedInGlobalChunk(self) -> "GlobalChunkCoordinate":
        return GlobalChunkCoordinate(
            self.x // islands.ISLAND_SIZE,
            self.y // islands.ISLAND_SIZE,
            self.z // islands.ISLAND_SIZE
        )

class IslandTileCoordinate(utils.Pos):

    def toGlobalTile(self,islandPos:"GlobalChunkCoordinate") -> GlobalTileCoordinate:
        islandOrigin = islandPos.tileOrigin()
        return GlobalTileCoordinate(
            self.x + islandOrigin.x,
            self.y + islandOrigin.y,
            self.z + islandOrigin.z
        )

class GlobalChunkCoordinate(utils.Pos):

    def tileOrigin(self) -> GlobalTileCoordinate:
        return GlobalTileCoordinate(
            self.x * islands.ISLAND_SIZE,
            self.y * islands.ISLAND_SIZE,
            self.z * islands.ISLAND_SIZE
        )

    def containedInSuperChunk(self) -> "SuperChunkCoordinate":
        return SuperChunkCoordinate(
            math.floor((self.x+(islands.CHUNKS_PER_SUPER_CHUNK/2))/islands.CHUNKS_PER_SUPER_CHUNK),
            math.floor((self.y+(islands.CHUNKS_PER_SUPER_CHUNK/2))/islands.CHUNKS_PER_SUPER_CHUNK)
        )

class SuperChunkCoordinate(utils.Pos):
    """z attribute shouldn't be used"""

    def globalChunkOrigin(self) -> GlobalChunkCoordinate:
        return GlobalChunkCoordinate(
            (self.x*islands.CHUNKS_PER_SUPER_CHUNK) - (islands.CHUNKS_PER_SUPER_CHUNK//2),
            (self.y*islands.CHUNKS_PER_SUPER_CHUNK) - (islands.CHUNKS_PER_SUPER_CHUNK//2),
            0
        )

@dataclass
class SidedCoordinate:
    coordinate:GlobalChunkCoordinate
    upsideDown:bool

class ChunkDirection(enum.Enum):
    east = 0
    south = 1
    west = 2
    north = 3
    up = 4
    down = 5

@dataclass
class LayeredWagonCargo[T]:
    containers:list[T]

@dataclass
class CargoContainer[T]:
    packages:list[gameObjects.CargoPackage[T]]
    maxPackages:int

class SimulationSteps:

    STEPS_PER_WORLD_UNIT = 2305195200000

    def __init__(self,steps:int):
        self.steps = steps

    @classmethod
    def fromWorldUnits(cls,worldUnits:int) -> typing.Self:
        return cls(worldUnits*cls.STEPS_PER_WORLD_UNIT)

    def toWorldUnits(self) -> float:
        return self.steps / self.STEPS_PER_WORLD_UNIT

@dataclass
class BeltSlotState:
    item:gameObjects.GenericBeltItem|None
    progress:SimulationSteps

@dataclass
class BeltLaneState:
    item:gameObjects.GenericBeltItem|None
    progress:SimulationSteps

@dataclass
class FluidContainerState:
    value:gameObjects.FluidUnit
    fluid:gameObjects.GenericFluid|None

# ingame this is just `Ticks`
class SimulationTicks:

    TICKS_PER_SECOND = 9604980000

    def __init__(self,value:int):
        self.value = value

    @classmethod
    def fromSeconds(cls,seconds:int) -> typing.Self:
        return cls(seconds*cls.TICKS_PER_SECOND)

    def toSeconds(self) -> float:
        return self.value / self.TICKS_PER_SECOND

@dataclass
class ShapeCollapseResultEntry:
    shape:gameObjects.Shape
    fallDownLayers:int
    vanish:bool

@dataclass
class ShapeCollapseResult:
    entries:list[ShapeCollapseResultEntry]
    shape:gameObjects.Shape|None

class SignalTicks:

    TICKS_PER_SECOND = 12
    MIN_VALUE = -(2**63)

    def __init__(self,value:int):
        self.value = value

    @classmethod
    def fromSeconds(cls,seconds:int) -> typing.Self:
        return cls(seconds*cls.TICKS_PER_SECOND)

    def toSeconds(self) -> float:
        return self.value / self.TICKS_PER_SECOND

class SignalBuffer:

    # based on SignalSimulation.MaxSignalsPerUpdate = 4
    ARRAY_SIZE = 4

    def __init__(
        self,
        values:list[gameObjects.GenericSignal],
        lastStartTicks:SimulationTicks,
        lastSignalTick:SignalTicks,
        wasPushedThisStartTick:bool
    ):
        self.values = values
        self.lastStartTicks = lastStartTicks
        self.lastSignalTick = lastSignalTick
        self.wasPushedThisStartTick = wasPushedThisStartTick

@dataclass
class SignalConductorInputState:
    inputConductor:SignalBuffer

class MixerSimulationMixingState(enum.Enum):
    fillingChambers = 0
    mixing = 1
    draining = 2

@dataclass
class ItemOnBelt:
    item:gameObjects.GenericBeltItem # not None
    nextItemDistance:SimulationSteps

@dataclass
class FastBeltPathLaneState:
    itemCapacity:int
    compressedItemsAfterFirst:int
    firstItemDistance:SimulationSteps
    items:list[ItemOnBelt]

class SpacePathsConstants:
    NUM_LAYERS = 3
    NUM_LANES = 4
    ENTRIES_PER_BUNDLE = NUM_LAYERS * NUM_LANES

class BundleState[T]:

    ENTRIES_PER_BUNDLE = SpacePathsConstants.ENTRIES_PER_BUNDLE

    def __init__(self,entries:list[T]) -> None:
        self.entries = entries

class PathMergerSimulationState:

    NUM_ITEMS_PER_LANE = 4

    def __init__(
        self,
        inputSegmentSlotStates:list[list[BeltLaneState]],
        priorityLaneIndex:int,
        preferredInputIndex:int
    ) -> None:
        self.inputSegmentSlotStates = inputSegmentSlotStates
        self.priorityLaneIndex = priorityLaneIndex
        self.preferredInputIndex = preferredInputIndex

@dataclass
class BeltPathLaneState:
    slots:list[BeltSlotState]

@dataclass
class PathSplitterSimulationState:
    outputLaneStates:list[BeltPathLaneState]
    nextPreferredIndex:int

@dataclass
class SimulationTimedBufferItem[T]:
    item:T
    selfExcess:SimulationTicks

@dataclass
class SimulationBufferState[T]:
    queue:list[SimulationTimedBufferItem[T]]

class BeltItemSimulationBufferState(SimulationBufferState[gameObjects.GenericBeltItem]): ...

@dataclass
class FluidPackageData:
    fluid:gameObjects.GenericFluid|None
    amount:gameObjects.FluidUnit

@dataclass
class FluidPackageLaunchData:
    fluidPackage:FluidPackageData
    remainingTicks:SimulationTicks
    totalTicks:SimulationTicks

@dataclass
class FluidPackageLaunchState:
    travellingPackageLaunch:FluidPackageLaunchData

@dataclass
class TrainCargoFillingContainerState[T]:
    package:gameObjects.CargoPackage[T]

class TrainCargoExchangerState[T]:

    NUM_LAYERS = SpacePathsConstants.NUM_LAYERS
    NUM_LOADING_PATH_SLOTS = 2

    def __init__(
        self,
        loadingPathsStates:BundleState[BeltPathLaneState],
        trainCargoFillingContainerState:list[TrainCargoFillingContainerState[T]],
        cargoContainerTracksStates:list[BeltPathLaneState],
        cargoOnBridge:list[BeltPathLaneState]
    ) -> None:
        self.loadingPathsStates = loadingPathsStates
        self.trainCargoFillingContainerState = trainCargoFillingContainerState
        self.cargoContainerTracksStates = cargoContainerTracksStates
        self.cargoOnBridge = cargoOnBridge

class TrainCargoTransferState[T]: # T unused but kept for other classes

    NUM_LAYERS = SpacePathsConstants.NUM_LAYERS

    def __init__(
        self,
        cargoContainerTracksStates:list[BeltPathLaneState],
        cargoOnInputBridge:list[BeltPathLaneState],
        cargoOnOutputBridge:list[BeltPathLaneState]
    ) -> None:
        self.cargoContainerTracksStates = cargoContainerTracksStates
        self.cargoOnInputBridge = cargoOnInputBridge
        self.cargoOnOutputBridge = cargoOnOutputBridge

class GenericCargoExchanger[T]: ...
class GenericCargoTransferrer[T]: ...

@dataclass
class TrainCargoLoaderSimulation[T](GenericCargoExchanger[LayeredWagonCargo[CargoContainer[T]]]):
    state:TrainCargoExchangerState[T]

@dataclass
class TrainCargoUnloaderSimulation[T](GenericCargoExchanger[LayeredWagonCargo[CargoContainer[T]]]):
    state:TrainCargoExchangerState[T]

@dataclass
class TrainCargoTransferrerSimulation[T](GenericCargoTransferrer[LayeredWagonCargo[CargoContainer[T]]]):
    state:TrainCargoTransferState[T]

@dataclass
class TimedSignal:
    signal:gameObjects.GenericSignal
    tick:SignalTicks

@dataclass
class SignalChannelRingBufferState:
    timedSignals:list[TimedSignal]

class SignalChannelRingBuffer:

    # based on SignalSimulation.MaxSignalsPerUpdate = 4
    SIGNAL_ARRAY_SIZE = (4+(4*2))*2

    def __init__(self,state:SignalChannelRingBufferState) -> None:
        self.state = state

# this might need to go in the research module
@dataclass
class RocketGroupId:
    id:str

    def __hash__(self):
        return hash(self.id)

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,RocketGroupId):
            return NotImplemented
        return self.id == other.id

#endregion



#region simulation states

class GenericSimulationState: ...

@_serializationId("BeltFilterState")
@dataclass
class BeltFilterSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    outputLaneStates:list[BeltLaneState]
    inputConductorState:SignalConductorInputState

@_serializationId("BeltPortReceiverDisabledState")
@dataclass
class BeltPortReceiverDisabledState(GenericSimulationState):
    outputLaneState:BeltLaneState

@_serializationId("BeltPortSenderBlockedState")
@dataclass
class BeltPortSenderBlockedState(GenericSimulationState):
    inputLaneState:BeltLaneState

@_serializationId("BeltPortSenderDiscardState")
@dataclass
class BeltPortSenderDiscardState(GenericSimulationState):
    inputLaneState:BeltLaneState

@_serializationId("BeltPortSenderToHubState")
@dataclass
class BeltPortSenderToHubSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    vortexLaneState:FastBeltPathLaneState

@_serializationId("BeltPortSenderToSpacePathState")
@dataclass
class BeltPortSenderToSpacePathSimulationState(GenericSimulationState):
    pathLaneState:BeltPathLaneState
    bufferState:BeltItemSimulationBufferState

@_serializationId("BeltPortSenderTransferState")
class BeltPortSenderTransferSimulationState(GenericSimulationState):

    NUM_JUMP_LANE_ITEMS = 2

    def __init__(self,jumpLaneState:FastBeltPathLaneState):
        self.jumpLaneState = jumpLaneState

@_serializationId("BeltReaderState")
@dataclass
class BeltReaderSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@_serializationId("ControlledSignalReceiverState")
@dataclass
class ControlledSignalReceiverState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

@_serializationId("ControlledSignalTransmitterState")
@dataclass
class ControlledSignalTransmitterState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

@_serializationId("ConverterHubProducerState")
@dataclass
class ConverterHubProducerSimulationState(GenericSimulationState):
    outputLaneState:BeltLaneState
    numProducedItems:int

@_serializationId("ConverterState")
@dataclass
class ConverterSimulationState(GenericSimulationState):
    inputLaneStates:list[BeltLaneState]
    processingReceiverStates:list[BeltLaneState]
    processingLaneStates:list[BeltLaneState]
    outputLaneStates:list[BeltLaneState]

@_serializationId("ConveyorState")
@dataclass
class ConveyorSimulationState(GenericSimulationState):
    slot0:BeltSlotState
    slot1:BeltSlotState

@_serializationId("CrystalGeneratorState")
@dataclass
class CrystalGeneratorSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    containerState:FluidContainerState
    currentProcessingPaint:gameObjects.GenericFluid|None
    currentSourceShape:gameObjects.ShapeItem|None
    currentCrystalOnlyShape:gameObjects.ShapeItem|None
    fluidAmountDuringLastUpdate:gameObjects.FluidUnit
    excessTicks:SimulationTicks
    ticksSinceLastCrystallization:SimulationTicks
    ticksSinceItemEntered:SimulationTicks

@_serializationId("DisplayState")
@dataclass
class DisplaySimulationState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

@_serializationId("ExtractorState")
@dataclass
class ExtractorSimulationState(GenericSimulationState):
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@_serializationId("FluidPortReceiverDisabledState")
@dataclass
class FluidPortReceiverDisabledState(GenericSimulationState):
    outputContainer:FluidContainerState

@_serializationId("FluidPortSenderBlockedState")
@dataclass
class FluidPortSenderBlockedState(GenericSimulationState):
    inputContainer:FluidContainerState

@_serializationId("FluidPortSenderDiscardState")
@dataclass
class FluidPortSenderDiscardState(GenericSimulationState):
    inputContainer:FluidContainerState

@_serializationId("FluidPortSenderToSpacePipeState")
@dataclass
class FluidPortSenderToSpacePipeSimulationState(GenericSimulationState):
    inputContainer:FluidContainerState
    launchState:FluidPackageLaunchState

@_serializationId("FluidPortTransferState")
@dataclass
class FluidPortTransferState(GenericSimulationState):
    inputContainer:FluidContainerState
    launchState:FluidPackageLaunchState
    outputContainer:FluidContainerState

@_serializationId("FluidStorageState")
@dataclass
class FluidStorageSimulationState(GenericSimulationState):
    containerState:FluidContainerState

@_serializationId("FullCutterState")
@dataclass
class FullCutterSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    leftLaneState:BeltLaneState
    rightLaneState:BeltLaneState
    leftOutputLaneState:BeltLaneState
    rightOutputLaneState:BeltLaneState
    leftCollapseResult:ShapeCollapseResult|None
    rightCollapseResult:ShapeCollapseResult|None

@_serializationId("HalfCutterState")
@dataclass
class HalfCutterSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    currentWaste:ShapeCollapseResult|None
    currentCollapseResult:ShapeCollapseResult|None
    producingEmptyShape:bool

@_serializationId("HalvesSwapperState")
@dataclass
class HalvesSwapperSimulationState(GenericSimulationState):
    lowerInputLaneState:BeltLaneState
    lowerProcessingLaneState:BeltLaneState
    lowerOutputLaneState:BeltLaneState
    upperInputLaneState:BeltLaneState
    upperProcessingLaneState:BeltLaneState
    upperOutputLaneState:BeltLaneState
    lowerLeftCollapseResult:ShapeCollapseResult|None
    lowerRightCollapseResult:ShapeCollapseResult|None
    upperLeftCollapseResult:ShapeCollapseResult|None
    upperRightCollapseResult:ShapeCollapseResult|None
    lowerFinalResult:gameObjects.ShapeItem|None
    upperFinalResult:gameObjects.ShapeItem|None

@_serializationId("ItemProducerState")
@dataclass
class ItemProducerSimulationState(GenericSimulationState):
    outputLaneState:BeltLaneState

@_serializationId("Lift1LayerState")
@dataclass
class Lift1LayerSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    verticalLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@_serializationId("Lift2LayerState")
@dataclass
class Lift2LayerSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    verticalLane0State:BeltLaneState
    verticalLane1State:BeltLaneState
    outputLaneState:BeltLaneState

@_serializationId("LogicGate2In1OutState")
@dataclass
class LogicGate2In1OutSimulationState(GenericSimulationState):
    input0ConductorState:SignalConductorInputState
    Input1ConductorState:SignalConductorInputState

@_serializationId("LogicGateCompareState")
@dataclass
class LogicGateCompareSimulationState(GenericSimulationState):
    input0ConductorState:SignalConductorInputState
    input1ConductorState:SignalConductorInputState

@_serializationId("LogicGateIfState")
@dataclass
class LogicGateIfSimulationState(GenericSimulationState):
    inputConductorState:SignalConductorInputState
    gateConductorState:SignalConductorInputState

@_serializationId("LogicGateNotState")
@dataclass
class LogicGateNotSimulationState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

@_serializationId("MergerState")
@dataclass
class MergerSimulationState(GenericSimulationState):
    inputLaneStates:list[BeltLaneState]
    outputLaneState:BeltLaneState
    currentInputIndex:int
    preferredInputIndex:int

@_serializationId("MixerState")
@dataclass
class MixerSimulationState(GenericSimulationState):
    input0ContainerState:FluidContainerState
    input1ContainerState:FluidContainerState
    chamber0ContainerState:FluidContainerState
    chamber1ContainerState:FluidContainerState
    outputContainerState:FluidContainerState
    mixingState:MixerSimulationMixingState
    mixingProgress:SimulationTicks
    mixingResult:gameObjects.GenericFluid|None

@_serializationId("PainterState")
@dataclass
class PainterSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    containerState:FluidContainerState
    currentProcessingPaint:gameObjects.GenericFluid|None
    fluidAmountDuringLastUpdate:gameObjects.FluidUnit
    excessTicks:SimulationTicks
    ticksSinceLastPaint:SimulationTicks
    ticksSinceItemEntered:SimulationTicks

@_serializationId("PinPusherState")
@dataclass
class PinPusherSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    currentWaste:gameObjects.ShapeItem|None
    currentResult:ShapeCollapseResult|None

@_serializationId("PipeGateState")
@dataclass
class PipeGateSimulationState(GenericSimulationState):
    containerState:FluidContainerState
    inputConductorState:SignalConductorInputState

@_serializationId("RotatorState")
@dataclass
class RotatorSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@_serializationId("PrioritySplitterState")
@dataclass
class PrioritySplitterSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    outputLaneStates:list[BeltLaneState]
    prioritizedIndex:int

@_serializationId("SignalPortSenderBlockedState")
@dataclass
class SignalPortSenderBlockedState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

@_serializationId("SignalPortTransferState")
@dataclass
class SignalPortTransferState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

@_serializationId("ConverterHubState")
@dataclass
class SpaceConverterHubSimulationState(GenericSimulationState):
    outputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]

@_serializationId("SpaceConverterState")
@dataclass
class SpaceConverterSimulationState(GenericSimulationState):
    inputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]
    simulationBundleState:BundleState[ConverterSimulationState]
    outputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]
    conversionCount:int

@_serializationId("SpaceConveyorState")
@dataclass
class SpaceConveyorSimulationState(GenericSimulationState):
    pathBundleState:BundleState[FastBeltPathLaneState]

@_serializationId("SpaceMergerState")
@dataclass
class SpaceMergerSimulationState(GenericSimulationState):
    mergerSimulationBundleState:BundleState[PathMergerSimulationState]
    inputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]

@_serializationId("SpacePathToBeltPortReceiverState")
@dataclass
class SpacePathToBeltPortReceiverSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    pathLaneState:FastBeltPathLaneState
    bufferState:BeltItemSimulationBufferState

@_serializationId("SpacePipeToFluidPortReceiverState")
@dataclass
class SpacePipeToFluidPortReceiverSimulationState(GenericSimulationState):
    outputContainer:FluidContainerState
    launchState:FluidPackageLaunchState
    bufferState:BeltItemSimulationBufferState
    inputLaneState:BeltLaneState

@_serializationId("ResearchStationState")
@dataclass
class SpaceResearchStationSimulationState(GenericSimulationState):
    inputBundleState:BundleState[FastBeltPathLaneState]
    processingBundleState:BundleState[FastBeltPathLaneState]
    outputBundleState:BundleState[FastBeltPathLaneState]

@_serializationId("SpaceSplitterState")
@dataclass
class SpaceSplitterSimulationState(GenericSimulationState):
    splitterSimulationBundleState:BundleState[PathSplitterSimulationState]

@_serializationId("SpaceTrashState")
@dataclass
class SpaceTrashSimulationState(GenericSimulationState):
    inputBundleState:BundleState[FastBeltPathLaneState]

@_serializationId("SplitterState")
@dataclass
class SplitterSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    outputLaneStates:list[BeltLaneState]

@_serializationId("StackerState")
@dataclass
class StackerSimulationState(GenericSimulationState):
    lowerInputLaneState:BeltLaneState
    upperInputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    currentCollapseResult:ShapeCollapseResult|None

@_serializationId("TrashState")
class TrashSimulationState(GenericSimulationState):

    NUM_LANES = 4

    def __init__(self,laneStates:list[BeltLaneState]):
        self.laneStates = laneStates

@_serializationId("Virtual1InSimulationState")
@dataclass
class Virtual1InSimulationState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

@_serializationId("Virtual2InSimulationState")
@dataclass
class Virtual2InSimulationState(GenericSimulationState):
    input0ConductorState:SignalConductorInputState
    input1ConductorState:SignalConductorInputState

#endregion