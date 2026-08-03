from . import utils, islands, gameObjects, _gameObjectsSerializer

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

class GenericSimulationState(
    _gameObjectsSerializer.PolymorphicSerializable,
    serializationID = None
): ...

@dataclass
class BeltFilterSimulationState(GenericSimulationState,serializationID="BeltFilterState"):
    inputLaneState:BeltLaneState
    outputLaneStates:list[BeltLaneState]
    inputConductorState:SignalConductorInputState

@dataclass
class BeltPortReceiverDisabledState(GenericSimulationState,serializationID="BeltPortReceiverDisabledState"):
    outputLaneState:BeltLaneState

@dataclass
class BeltPortSenderBlockedState(GenericSimulationState,serializationID="BeltPortSenderBlockedState"):
    inputLaneState:BeltLaneState

@dataclass
class BeltPortSenderDiscardState(GenericSimulationState,serializationID="BeltPortSenderDiscardState"):
    inputLaneState:BeltLaneState

@dataclass
class BeltPortSenderToHubSimulationState(GenericSimulationState,serializationID="BeltPortSenderToHubState"):
    inputLaneState:BeltLaneState
    vortexLaneState:FastBeltPathLaneState

@dataclass
class BeltPortSenderToSpacePathSimulationState(GenericSimulationState,serializationID="BeltPortSenderToSpacePathState"):
    pathLaneState:BeltPathLaneState
    bufferState:BeltItemSimulationBufferState

class BeltPortSenderTransferSimulationState(GenericSimulationState,serializationID="BeltPortSenderTransferState"):

    NUM_JUMP_LANE_ITEMS = 2

    def __init__(self,jumpLaneState:FastBeltPathLaneState):
        self.jumpLaneState = jumpLaneState

@dataclass
class BeltReaderSimulationState(GenericSimulationState,serializationID="BeltReaderState"):
    inputLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@dataclass
class ControlledSignalReceiverState(GenericSimulationState,serializationID="ControlledSignalReceiverState"):
    inputConductorState:SignalConductorInputState

@dataclass
class ControlledSignalTransmitterState(GenericSimulationState,serializationID="ControlledSignalTransmitterState"):
    inputConductorState:SignalConductorInputState

@dataclass
class ConverterHubProducerSimulationState(GenericSimulationState,serializationID="ConverterHubProducerState"):
    outputLaneState:BeltLaneState
    numProducedItems:int

@dataclass
class ConverterSimulationState(GenericSimulationState,serializationID="ConverterState"):
    inputLaneStates:list[BeltLaneState]
    processingReceiverStates:list[BeltLaneState]
    processingLaneStates:list[BeltLaneState]
    outputLaneStates:list[BeltLaneState]

@dataclass
class ConveyorSimulationState(GenericSimulationState,serializationID="ConveyorState"):
    slot0:BeltSlotState
    slot1:BeltSlotState

@dataclass
class CrystalGeneratorSimulationState(GenericSimulationState,serializationID="CrystalGeneratorState"):
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

@dataclass
class DisplaySimulationState(GenericSimulationState,serializationID="DisplayState"):
    inputConductorState:SignalConductorInputState

@dataclass
class ExtractorSimulationState(GenericSimulationState,serializationID="ExtractorState"):
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@dataclass
class FluidPortReceiverDisabledState(GenericSimulationState,serializationID="FluidPortReceiverDisabledState"):
    outputContainer:FluidContainerState

@dataclass
class FluidPortSenderBlockedState(GenericSimulationState,serializationID="FluidPortSenderBlockedState"):
    inputContainer:FluidContainerState

@dataclass
class FluidPortSenderDiscardState(GenericSimulationState,serializationID="FluidPortSenderDiscardState"):
    inputContainer:FluidContainerState

@dataclass
class FluidPortSenderToSpacePipeSimulationState(GenericSimulationState,serializationID="FluidPortSenderToSpacePipeState"):
    inputContainer:FluidContainerState
    launchState:FluidPackageLaunchState

@dataclass
class FluidPortTransferState(GenericSimulationState,serializationID="FluidPortTransferState"):
    inputContainer:FluidContainerState
    launchState:FluidPackageLaunchState
    outputContainer:FluidContainerState

@dataclass
class FluidStorageSimulationState(GenericSimulationState,serializationID="FluidStorageState"):
    containerState:FluidContainerState

@dataclass
class FullCutterSimulationState(GenericSimulationState,serializationID="FullCutterState"):
    inputLaneState:BeltLaneState
    leftLaneState:BeltLaneState
    rightLaneState:BeltLaneState
    leftOutputLaneState:BeltLaneState
    rightOutputLaneState:BeltLaneState
    leftCollapseResult:ShapeCollapseResult|None
    rightCollapseResult:ShapeCollapseResult|None

@dataclass
class HalfCutterSimulationState(GenericSimulationState,serializationID="HalfCutterState"):
    inputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    currentWaste:ShapeCollapseResult|None
    currentCollapseResult:ShapeCollapseResult|None
    producingEmptyShape:bool

@dataclass
class HalvesSwapperSimulationState(GenericSimulationState,serializationID="HalvesSwapperState"):
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

@dataclass
class ItemProducerSimulationState(GenericSimulationState,serializationID="ItemProducerState"):
    outputLaneState:BeltLaneState

@dataclass
class Lift1LayerSimulationState(GenericSimulationState,serializationID="Lift1LayerState"):
    inputLaneState:BeltLaneState
    verticalLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@dataclass
class Lift2LayerSimulationState(GenericSimulationState,serializationID="Lift2LayerState"):
    inputLaneState:BeltLaneState
    verticalLane0State:BeltLaneState
    verticalLane1State:BeltLaneState
    outputLaneState:BeltLaneState

@dataclass
class LogicGate2In1OutSimulationState(GenericSimulationState,serializationID="LogicGate2In1OutState"):
    input0ConductorState:SignalConductorInputState
    Input1ConductorState:SignalConductorInputState

@dataclass
class LogicGateCompareSimulationState(GenericSimulationState,serializationID="LogicGateCompareState"):
    input0ConductorState:SignalConductorInputState
    input1ConductorState:SignalConductorInputState

@dataclass
class LogicGateIfSimulationState(GenericSimulationState,serializationID="LogicGateIfState"):
    inputConductorState:SignalConductorInputState
    gateConductorState:SignalConductorInputState

@dataclass
class LogicGateNotSimulationState(GenericSimulationState,serializationID="LogicGateNotState"):
    inputConductorState:SignalConductorInputState

@dataclass
class MergerSimulationState(GenericSimulationState,serializationID="MergerState"):
    inputLaneStates:list[BeltLaneState]
    outputLaneState:BeltLaneState
    currentInputIndex:int
    preferredInputIndex:int

@dataclass
class MixerSimulationState(GenericSimulationState,serializationID="MixerState"):
    input0ContainerState:FluidContainerState
    input1ContainerState:FluidContainerState
    chamber0ContainerState:FluidContainerState
    chamber1ContainerState:FluidContainerState
    outputContainerState:FluidContainerState
    mixingState:MixerSimulationMixingState
    mixingProgress:SimulationTicks
    mixingResult:gameObjects.GenericFluid|None

@dataclass
class PainterSimulationState(GenericSimulationState,serializationID="PainterState"):
    inputLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    containerState:FluidContainerState
    currentProcessingPaint:gameObjects.GenericFluid|None
    fluidAmountDuringLastUpdate:gameObjects.FluidUnit
    excessTicks:SimulationTicks
    ticksSinceLastPaint:SimulationTicks
    ticksSinceItemEntered:SimulationTicks

@dataclass
class PinPusherSimulationState(GenericSimulationState,serializationID="PinPusherState"):
    inputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    currentWaste:gameObjects.ShapeItem|None
    currentResult:ShapeCollapseResult|None

@dataclass
class PipeGateSimulationState(GenericSimulationState,serializationID="PipeGateState"):
    containerState:FluidContainerState
    inputConductorState:SignalConductorInputState

@dataclass
class RotatorSimulationState(GenericSimulationState,serializationID="RotatorState"):
    inputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState

@dataclass
class PrioritySplitterSimulationState(GenericSimulationState,serializationID="PrioritySplitterState"):
    inputLaneState:BeltLaneState
    outputLaneStates:list[BeltLaneState]
    prioritizedIndex:int

@dataclass
class SignalPortSenderBlockedState(GenericSimulationState,serializationID="SignalPortSenderBlockedState"):
    inputConductorState:SignalConductorInputState

@dataclass
class SignalPortTransferState(GenericSimulationState,serializationID="SignalPortTransferState"):
    inputConductorState:SignalConductorInputState

@dataclass
class SpaceConverterHubSimulationState(GenericSimulationState,serializationID="ConverterHubState"):
    outputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]

@dataclass
class SpaceConverterSimulationState(GenericSimulationState,serializationID="SpaceConverterState"):
    inputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]
    simulationBundleState:BundleState[ConverterSimulationState]
    outputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]
    conversionCount:int

@dataclass
class SpaceConveyorSimulationState(GenericSimulationState,serializationID="SpaceConveyorState"):
    pathBundleState:BundleState[FastBeltPathLaneState]

@dataclass
class SpaceMergerSimulationState(GenericSimulationState,serializationID="SpaceMergerState"):
    mergerSimulationBundleState:BundleState[PathMergerSimulationState]
    inputLaneBundleStates:list[BundleState[FastBeltPathLaneState]]

@dataclass
class SpacePathToBeltPortReceiverSimulationState(GenericSimulationState,serializationID="SpacePathToBeltPortReceiverState"):
    inputLaneState:BeltLaneState
    pathLaneState:FastBeltPathLaneState
    bufferState:BeltItemSimulationBufferState

@dataclass
class SpacePipeToFluidPortReceiverSimulationState(GenericSimulationState,serializationID="SpacePipeToFluidPortReceiverState"):
    outputContainer:FluidContainerState
    launchState:FluidPackageLaunchState
    bufferState:BeltItemSimulationBufferState
    inputLaneState:BeltLaneState

@dataclass
class SpaceResearchStationSimulationState(GenericSimulationState,serializationID="ResearchStationState"):
    inputBundleState:BundleState[FastBeltPathLaneState]
    processingBundleState:BundleState[FastBeltPathLaneState]
    outputBundleState:BundleState[FastBeltPathLaneState]

@dataclass
class SpaceSplitterSimulationState(GenericSimulationState,serializationID="SpaceSplitterState"):
    splitterSimulationBundleState:BundleState[PathSplitterSimulationState]

@dataclass
class SpaceTrashSimulationState(GenericSimulationState,serializationID="SpaceTrashState"):
    inputBundleState:BundleState[FastBeltPathLaneState]

@dataclass
class SplitterSimulationState(GenericSimulationState,serializationID="SplitterState"):
    inputLaneState:BeltLaneState
    outputLaneStates:list[BeltLaneState]

@dataclass
class StackerSimulationState(GenericSimulationState,serializationID="StackerState"):
    lowerInputLaneState:BeltLaneState
    upperInputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    currentCollapseResult:ShapeCollapseResult|None

class TrashSimulationState(GenericSimulationState,serializationID="TrashState"):

    NUM_LANES = 4

    def __init__(self,laneStates:list[BeltLaneState]):
        self.laneStates = laneStates

@dataclass
class Virtual1InSimulationState(GenericSimulationState,serializationID="Virtual1InSimulationState"):
    inputConductorState:SignalConductorInputState

@dataclass
class Virtual2InSimulationState(GenericSimulationState,serializationID="Virtual2InSimulationState"):
    input0ConductorState:SignalConductorInputState
    input1ConductorState:SignalConductorInputState

#endregion