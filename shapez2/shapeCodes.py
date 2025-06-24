from . import gameData

SHAPE_CONFIG_QUAD = gameData.SHAPE_CONFIG_QUAD
SHAPE_CONFIG_HEX = gameData.SHAPE_CONFIG_HEX
COLOR_SHAPES = {
    SHAPE_CONFIG_QUAD : ["C","R","S","W","c"],
    SHAPE_CONFIG_HEX : ["H","F","G","c"]
}
NO_COLOR_SHAPES = {
    SHAPE_CONFIG_QUAD : ["P"],
    SHAPE_CONFIG_HEX : ["P"]
}
COLORS = gameData.SHAPE_COLORS
NOTHING_CHAR = gameData.SHAPE_NOTHING_CHAR

def _separateInLayers(potentialShapeCode:str) -> tuple[str|list[str],bool]:
    if gameData.SHAPE_LAYER_SEPARATOR in potentialShapeCode:
        layers = potentialShapeCode.split(gameData.SHAPE_LAYER_SEPARATOR)
        for i,layer in enumerate(layers):
            if layer == "":
                return f"Layer {i+1} empty",False
    else:
        if potentialShapeCode == "":
            return "Empty shape code",False
        layers = [potentialShapeCode]
    return layers,True

def _verifyOnlyValidChars(layers:list[str],shapeConfig:str) -> tuple[str|None,bool]:
    for layerIndex,layer in enumerate(layers):
        for charIndex,char in enumerate(layer):
            if char not in [*COLOR_SHAPES[shapeConfig],*NO_COLOR_SHAPES[shapeConfig],*COLORS,NOTHING_CHAR]:
                return f"Invalid character in layer {layerIndex+1} ({layer}), at character {charIndex+1} : '{char}'",False
    return None,True

def _verifyShapesAndColorsInRightPos(layers:list[str],shapeConfig:str) -> tuple[str|None,bool]:
    for layerIndex,layer in enumerate(layers):
        shapeMode = True
        lastChar = len(layer)-1
        for charIndex,char in enumerate(layer):
            errorMsgStart = f"Character in layer {layerIndex+1} ({layer}) at character {charIndex+1} ({char})"
            if shapeMode:
                if char not in [*COLOR_SHAPES[shapeConfig],*NO_COLOR_SHAPES[shapeConfig],NOTHING_CHAR]:
                    return f"{errorMsgStart} must be a shape or empty",False
                if charIndex == lastChar:
                    return f"{errorMsgStart} should have a color but is end of layer",False
                if char in [*NO_COLOR_SHAPES[shapeConfig],NOTHING_CHAR]:
                    nextMustBeColor = False
                else:
                    nextMustBeColor = True
                shapeMode = False
            else:
                if char not in [*COLORS,NOTHING_CHAR]:
                    return f"{errorMsgStart} must be a color or empty",False
                if nextMustBeColor and (char not in COLORS):
                    return f"{errorMsgStart} must be a color",False
                if (not nextMustBeColor) and (char != NOTHING_CHAR):
                    return f"{errorMsgStart} must be empty",False
                shapeMode = True
    return None,True

def _verifyAllLayersHaveSameLen(layers:list[str]) -> tuple[str|None,bool]:
    expectedLayerLen = len(layers[0])
    for layerIndex,layer in enumerate(layers[1:]):
        if len(layer) != expectedLayerLen:
            return f"Layer {layerIndex+2} ({layer}){f' (or 1 ({layers[0]}))' if layerIndex == 0 else ''} doesn't have the expected number of parts",False
    return None,True

def _isShapeEmpty(layers:list[str]) -> bool:
    return all(all(c == NOTHING_CHAR for c in l) for l in layers)

def isShapeCodeValid(potentialShapeCode:str,shapeConfig:str|None,emptyShapeInvalid:bool=False) -> tuple[None|str,bool]:

    layersResult = _separateInLayers(potentialShapeCode)
    if not layersResult[1]:
        return layersResult[0],False
    layers:list[str] = layersResult[0]

    if shapeConfig is None:
        for testShapeConfig in (SHAPE_CONFIG_QUAD,SHAPE_CONFIG_HEX):
            validCharsResult = _verifyOnlyValidChars(layers,testShapeConfig)
            if validCharsResult[1]:
                shapeConfig = testShapeConfig
                break
        if shapeConfig is None:
            return validCharsResult[0],False
    else:
        validCharsResult = _verifyOnlyValidChars(layers,shapeConfig)
        if not validCharsResult[1]:
            return validCharsResult[0],False

    shapesAndColorsInRightPosResult = _verifyShapesAndColorsInRightPos(layers,shapeConfig)
    if not shapesAndColorsInRightPosResult[1]:
        return shapesAndColorsInRightPosResult[0],False

    allLayersHaveSameLenResult = _verifyAllLayersHaveSameLen(layers)
    if not allLayersHaveSameLenResult[1]:
        return allLayersHaveSameLenResult[0],False

    if emptyShapeInvalid and _isShapeEmpty(layers):
        return "Shape is fully empty",False

    return None,True