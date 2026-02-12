from . import gameObjects

LAYER_SEPARATOR = ":"
EMPTY_CHAR = "-"

def isShapeCodeValid(
    potentialShapeCode:str,
    shapesConfig:gameObjects.ShapesConfiguration|list[gameObjects.ShapesConfiguration],
    colorScheme:gameObjects.ColorScheme|list[gameObjects.ColorScheme],
    emptyShapeInvalid:bool=False
) -> tuple[bool,str,list[gameObjects.ShapesConfiguration],list[gameObjects.ColorScheme]]:

    if isinstance(shapesConfig,gameObjects.ShapesConfiguration):
        shapesConfig = [shapesConfig]
    possibleShapesConfigs = []
    if isinstance(colorScheme,gameObjects.ColorScheme):
        colorScheme = [colorScheme]
    possibleColorSchemes = []

    def inner() -> bool:
        nonlocal errorMsg

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

        def checkShapeTypes(shapesConfig:gameObjects.ShapesConfiguration) -> bool:
            nonlocal errorMsg
            for layerIndex,layer in enumerate(layers):

                for charIndex in range(0,len(layer),2):
                    shapeChar = layer[charIndex]
                    colorChar = layer[charIndex+1]

                    if shapeChar == EMPTY_CHAR:
                        nextIsColor = False
                    else:
                        curShape = shapesConfig.partsByCode.get(shapeChar)
                        if curShape is None:
                            errorMsg = f"Invalid shape : {shapeChar}"
                            return False
                        nextIsColor = curShape.hasColor

                    if (not nextIsColor) and colorChar != EMPTY_CHAR:
                        errorMsg = f"Color in layer {layerIndex+1} at character {charIndex+2} must be '{EMPTY_CHAR}'"
                        return False

            return True

        for testShapesConfig in shapesConfig:
            if checkShapeTypes(testShapesConfig):
                possibleShapesConfigs.append(testShapesConfig)

        if len(possibleShapesConfigs) == 0:
            return False

        colors = [c for layer in layers for c in layer[1::2]]

        def checkColors(colorScheme:gameObjects.ColorScheme) -> bool:
            nonlocal errorMsg
            for c in colors:
                if (c != EMPTY_CHAR) and (colorScheme.colorsByCode.get(c) is None):
                    errorMsg = f"Invalid color : {c}"
                    return False
            return True

        for testColorScheme in colorScheme:
            if checkColors(testColorScheme):
                possibleColorSchemes.append(testColorScheme)

        if len(possibleColorSchemes) == 0:
            return False

        if emptyShapeInvalid and all(c == EMPTY_CHAR for layer in layers for c in layer[::2]):
            errorMsg = "Shape is fully empty"
            return False

        return True

    errorMsg = ""
    result = inner()
    return result, errorMsg, possibleShapesConfigs, possibleColorSchemes