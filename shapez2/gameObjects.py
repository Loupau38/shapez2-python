from . import utils, islands
from ._gameObjectsSerializer import serializationId as _serializationId

import typing
from dataclasses import dataclass
import enum



#region misc

@dataclass
class Color:
    code:str

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,Color):
            return NotImplemented
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)

@dataclass
class ColorSkin:
    id:str
    colors:dict[Color,tuple[int,int,int]]

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,ColorSkin):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

@dataclass
class ColorMode:
    id:str
    colorSkin:ColorSkin
    colorblindPatterns:bool

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,ColorMode):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

class ColorScheme:

    def __init__(
        self,
        id:str,
        primaryColors:list[Color],
        secondaryColors:list[Color],
        tertiaryColors:list[Color],
        defaultColor:Color,
        colorModes:list[ColorMode],
        mixingRecipes:dict[frozenset[Color],Color]
    ) -> None:
        self.id = id
        self.primaryColors = primaryColors
        self.secondaryColors = secondaryColors
        self.tertiaryColors = tertiaryColors
        self.defaultColor = defaultColor
        self.colorModes = colorModes
        self.mixingRecipes = mixingRecipes
        self.colors = [defaultColor] + primaryColors + secondaryColors + tertiaryColors
        self.colorsByCode = {c.code:c for c in self.colors}
        self.colorModesById = {cm.id:cm for cm in colorModes}

    def getMixResult(self,color1:Color,color2:Color) -> Color:
        return self.mixingRecipes[frozenset((color1,color2))]

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,ColorScheme):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

@dataclass
class ShapePartType:
    code:str
    hasColor:bool=True
    canChangeColor:bool=True
    connectsHorizontally:bool=True
    crystalBehavior:bool=False
    replacedByCrystal:bool=False

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,ShapePartType):
            return NotImplemented
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)

class ShapesConfiguration:

    def __init__(
        self,
        id:str,
        numPartsPerLayer:int,
        pinPart:ShapePartType,
        crystalPart:ShapePartType,
        parts:list[tuple[ShapePartType,typing.Literal[0,1,2,3]]]
    ) -> None:
        self.id = id
        self.numPartsPerLayer = numPartsPerLayer
        self.pinPart = pinPart
        self.crystalPart = crystalPart
        self.mapGenerationCommonParts = [p[0] for p in parts if p[1] == 0]
        self.mapGenerationRareParts = [p[0] for p in parts if p[1] == 1]
        self.mapGenerationVeryRareParts = [p[0] for p in parts if p[1] == 2]
        self.parts = [p[0] for p in parts]
        self.partsByCode = {p.code:p for p in self.parts}

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,ShapesConfiguration):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

from . import shapeCodes # circular import workaround

@dataclass
class ShapePart:
    type:ShapePartType|None
    color:Color|None

    def toString(self) -> str:
        return shapeCodes.fromShapePart(self)

    def copy(self) -> typing.Self:
        return ShapePart(self.type,self.color)

class Shape:

    def __init__(self,layers:list[list[ShapePart]]) -> None:
        self.layers = layers
        self.numLayers = len(layers)
        self.numParts = len(layers[0])

    @staticmethod
    def fromShapeCode(
        shapeCode:str,
        shapesConfig:ShapesConfiguration,
        colorScheme:ColorScheme
    ) -> typing.Self:
        return shapeCodes.parseShape(shapeCode,shapesConfig,colorScheme)

    def toShapeCode(self) -> str:
        return shapeCodes.fromShape(self)
    
    def isEmpty(self) -> bool:
        return all(p.type is None for l in self.layers for p in l)

    def copy(self) -> typing.Self:
        return Shape([[p.copy() for p in l] for l in self.layers])

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,Shape):
            return NotImplemented
        return self.toShapeCode() == other.toShapeCode()

    def __hash__(self) -> int:
        return hash(self.toShapeCode())

class GenericFluid: ...

@dataclass
class ColorFluid(GenericFluid):
    color:Color

class FluidUnit:

    UNITS_PER_LITER = 38419920000

    def __init__(self,units:int):
        self.units = units

    @classmethod
    def fromLiters(cls,liters:int) -> typing.Self:
        return cls(liters*cls.UNITS_PER_LITER)

    def toLiters(self) -> float:
        return self.units / self.UNITS_PER_LITER

class GenericBeltItem: ...

@dataclass
class ShapeItem(GenericBeltItem):
    shape:Shape

@dataclass
class FluidPackageItem(GenericBeltItem):
    fluid:GenericFluid|None
    size:FluidUnit

@dataclass
class ShapePackageOnTrack(GenericBeltItem):
    amount:int
    shape:ShapeItem|None

@dataclass
class FluidPackageOnTrack(GenericBeltItem):
    amount:int
    fluid:GenericFluid|None

class GenericSignal: ...

class NullSignal(GenericSignal): ...

class ConflictSignal(GenericSignal): ...

@dataclass
class IntegerSignal(GenericSignal):
    value:int

@dataclass
class BeltItemSignal(GenericSignal):
    beltItem:GenericBeltItem|None

    @classmethod
    def fromBeltItem(cls,beltItem:GenericBeltItem|None) -> GenericSignal:
        if beltItem is None:
            return NullSignal()
        return cls(beltItem)

@dataclass
class FluidSignal(GenericSignal):
    fluid:GenericFluid|None

    @classmethod
    def fromFluid(cls,fluid:GenericFluid|None) -> GenericSignal:
        if fluid is None:
            return NullSignal()
        return cls(fluid)

class CompareMode(enum.Enum):
    Equal = 1
    GreaterEqual = 2
    Greater = 3
    Less = 4
    LessEqual = 5
    NotEqual = 6

@dataclass
class SignalChannelId:
    uid:int

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

@dataclass
class RailConnectionColorFilter:
    mask:int

    @classmethod
    def none(cls) -> typing.Self:
        return cls(0)

    @classmethod
    def all(cls,colorCount:int) -> typing.Self:
        return cls((1 << colorCount)-1)

    def containsColor(self,colorIndex:int) -> bool:
        return (self.mask & (1 << colorIndex)) != 0

    def addColor(self,colorIndex:int) -> None:
        self.mask |= 1 << colorIndex

    def removeColor(self,colorIndex:int) -> None:
        # classic way would be self.mask &= ~(1 << colorIndex)
        # but I don't want to deal with binary not on arbitrary sized ints
        if self.containsColor(colorIndex):
            self.mask -= 1 << colorIndex

#endregion



#region configs

class GenericBuildingConfig: ...

@dataclass
class LabelConfig(GenericBuildingConfig):
    text:str|None

@dataclass
class SignalProducerConfig(GenericBuildingConfig):
    signal:GenericSignal|None

@dataclass
class ItemProducerConfig(GenericBuildingConfig):
    beltItem:GenericBeltItem|None

@dataclass
class FluidProducerConfig(GenericBuildingConfig):
    fluid:GenericFluid|None

@dataclass
class ButtonConfig(GenericBuildingConfig):
    activated:bool

@dataclass
class CompareGateConfig(GenericBuildingConfig):
    compareMode:CompareMode

@dataclass
class GlobalSignalReceiverConfig(GenericBuildingConfig):
    channelId:SignalChannelId



class GenericIslandConfig: ...

@dataclass
class RailConfig(GenericIslandConfig):
    connectionFilters:list[RailConnectionColorFilter]

@dataclass
class DisableableTrainUnloadingLanesConfig(GenericIslandConfig):
    mask:int

    @classmethod
    def none(cls) -> typing.Self:
        return cls(0)

    @classmethod
    def all(cls,numLayers:int) -> typing.Self:
        return cls((1 << numLayers)-1)

    def laneDisabled(self,layer:int) -> bool:
        return (self.mask & (1 << layer)) != 0

    def disableLane(self,layer:int) -> None:
        self.mask |= 1 << layer

    def enableLane(self,layer:int) -> None:
        # classic way would be self.mask &= ~(1 << layer)
        # but I don't want to deal with binary not on arbitrary sized ints
        if self.laneDisabled(layer):
            self.mask -= 1 << layer

#endregion



#region states

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
    item:GenericBeltItem|None
    progress:SimulationSteps

@dataclass
class BeltLaneState:
    item:GenericBeltItem|None
    progress:SimulationSteps

@dataclass
class FluidContainerState:
    value:FluidUnit
    fluid:GenericFluid|None

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
    shape:Shape
    fallDownLayers:int
    vanish:bool

@dataclass
class ShapeCollapseResult:
    entries:list[ShapeCollapseResultEntry]
    shape:Shape|None

class SignalTicks:

    TICKS_PER_SECOND = 12

    def __init__(self,value:int):
        self.value = value

    @classmethod
    def fromSeconds(cls,seconds:int) -> typing.Self:
        return cls(seconds*cls.TICKS_PER_SECOND)

    def toSeconds(self) -> float:
        return self.value / self.TICKS_PER_SECOND

class SignalBuffer:

    ARRAY_SIZE = 4

    def __init__(
        self,
        values:list[GenericSignal],
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
    item:GenericBeltItem # not None
    nextItemDistance:SimulationSteps

@dataclass
class FastBeltPathLaneState:
    itemCapacity:int
    compressedItemsAfterFirst:int
    firstItemDistance:SimulationSteps
    items:list[ItemOnBelt]

class BundleState[T]:

    ENTRIES_PER_BUNDLE = 12

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
    currentProcessingPaint:GenericFluid|None
    currentSourceShape:ShapeItem|None
    currentCrystalOnlyShape:ShapeItem|None
    fluidAmountDuringLastUpdate:FluidUnit
    excessTicks:SimulationTicks
    ticksSinceLastCrystallization:SimulationTicks
    ticksSinceItemEntered:SimulationTicks

@_serializationId("DisplayState")
@dataclass
class DisplaySimulationState(GenericSimulationState):
    inputConductorState:SignalConductorInputState

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
    lowerFinalResult:ShapeItem|None
    upperFinalResult:ShapeItem|None

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
    mixingResult:GenericFluid|None

@_serializationId("PainterState")
@dataclass
class PainterSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    containerState:FluidContainerState
    currentProcessingPaint:GenericFluid|None
    fluidAmountDuringLastUpdate:FluidUnit
    excessTicks:SimulationTicks
    ticksSinceLastPaint:SimulationTicks
    ticksSinceItemEntered:SimulationTicks

@_serializationId("PinPusherState")
@dataclass
class PinPusherSimulationState(GenericSimulationState):
    inputLaneState:BeltLaneState
    processingLaneState:BeltLaneState
    outputLaneState:BeltLaneState
    currentWaste:ShapeItem|None
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