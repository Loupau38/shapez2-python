from . import utils

import typing
from dataclasses import dataclass
import enum

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



class GenericIslandConfig: ...

@dataclass
class RailConfig(GenericIslandConfig):
    connectionFilters:list[RailConnectionColorFilter]

@dataclass
class DisableableTrainUnloadingLanesConfig(GenericIslandConfig):
    disabledLanes:list[int]

class GlobalChunkCoordinate(utils.Pos): ...

class IslandTileCoordinate(utils.Pos): ...