from . import gameObjects, ingameData

LAYER_SEPARATOR = ":"
EMPTY_CHAR = "-"

def isShapeCodeValid(
    potentialShapeCode:str,
    shapesConfig:gameObjects.ShapesConfiguration|None,
    emptyShapeInvalid:bool=False
) -> tuple[bool,str|None,gameObjects.ShapesConfiguration|None]:

    def inner() -> bool:
        nonlocal errorMsg, shapesConfig

        layers = potentialShapeCode.split(LAYER_SEPARATOR)
        layersLen = len(layers[0])

        for layerIndex,layer in enumerate(layers):

            if layer == "":
                errorMsg = f"Layer {layerIndex+1} is empty"
                return False

            if len(layer)%2 != 0:
                errorMsg = f"Layer {layerIndex+1} doesn't have an even length"
                return False

            if len(layer) != layersLen:
                errorMsg = f"Layer {layerIndex+1} isn't the expected length ({layersLen})"
                return False

        def checkShapeTypesAndColors(shapesConfig:gameObjects.ShapesConfiguration) -> bool:
            nonlocal errorMsg
            for layerIndex,layer in enumerate(layers):

                for charIndex, char in enumerate(layer):

                    if charIndex%2 == 0:
                        if char == EMPTY_CHAR:
                            nextIsColor = False
                        else:
                            if shapesConfig.partsByCode.get(char) is None:
                                errorMsg = f"Invalid shape : {char}"
                                return False
                            nextIsColor = shapesConfig.partsByCode[char].hasColor

                    else:
                        if nextIsColor:
                            if ingameData.DEFAULT_COLOR_SCHEME.colorsByCode.get(char) is None:
                                errorMsg = f"Invalid color : {char}"
                                return False
                        else:
                            if char != EMPTY_CHAR:
                                errorMsg = f"Color in layer {layerIndex+1} at character {charIndex+1} must be '{EMPTY_CHAR}'"
                                return False

            return True

        finalShapesConfig = None
        for testShapesConfig in (
            [ingameData.QUAD_SHAPES_CONFIG,ingameData.HEX_SHAPES_CONFIG]
            if shapesConfig is None else
            [shapesConfig]
        ):
            if checkShapeTypesAndColors(testShapesConfig):
                finalShapesConfig = testShapesConfig
                break

        if finalShapesConfig is None:
            return False
        shapesConfig = finalShapesConfig

        if emptyShapeInvalid and gameObjects.Shape.fromShapeCode(potentialShapeCode,shapesConfig).isEmpty():
            errorMsg = "Shape is fully empty"
            return False

        return True

    errorMsg = None
    result = inner()
    return result, errorMsg, shapesConfig