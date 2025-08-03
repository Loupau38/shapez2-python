import typing
from dataclasses import dataclass

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
        parts:list[ShapePartType]
    ) -> None:
        self.id = id
        self.numPartsPerLayer = numPartsPerLayer
        self.pinPart = pinPart
        self.crystalPart = crystalPart
        self.parts = parts
        self.partsByCode = {p.code:p for p in parts}

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,ShapesConfiguration):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

@dataclass
class ShapePart:
    type:ShapePartType|None
    color:Color|None

    def toString(self) -> str:
        return (
            (shapeCodes.EMPTY_CHAR if self.type is None else self.type.code)
            + (shapeCodes.EMPTY_CHAR if self.color is None else self.color.code)
        )

from . import ingameData, shapeCodes # circular import workaround

class Shape:

    def __init__(self,layers:list[list[ShapePart]]) -> None:
        self.layers = layers
        self.numLayers = len(layers)
        self.numParts = len(layers[0])

    @classmethod
    def fromShapeCode(
        cls,
        shapeCode:str,
        shapesConfig:ShapesConfiguration,
        colorScheme:ColorScheme=ingameData.DEFAULT_COLOR_SCHEME
    ) -> typing.Self:
        return cls([
            [
                ShapePart(
                    shapesConfig.partsByCode.get(l[i*2]),
                    colorScheme.colorsByCode.get(l[(i*2)+1])
                )
                for i in range(len(l)//2)
            ]
            for l in shapeCode.split(shapeCodes.LAYER_SEPARATOR)
        ])

    def toShapeCode(self) -> str:
        return shapeCodes.LAYER_SEPARATOR.join("".join(p.toString() for p in l) for l in self.layers)
    
    def isEmpty(self) -> bool:
        return all(p.type is None for l in self.layers for p in l)

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,Shape):
            return NotImplemented
        return self.toShapeCode() == other.toShapeCode()

    def __hash__(self) -> int:
        return hash(self.toShapeCode())