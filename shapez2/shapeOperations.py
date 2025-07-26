from . import gameObjects
from .gameObjects import Shape, ShapePart, Color

import math
import typing
from dataclasses import dataclass
from collections.abc import Callable

class InvalidOperationInputs(ValueError): ...

@dataclass
class ShapeOperationConfig:
    maxShapeLayers:int
    shapesConfig:gameObjects.ShapesConfiguration

def _gravityConnected(part1:ShapePart,part2:ShapePart) -> bool:
    if None in (part1.type,part2.type):
        return False
    return part1.type.connectsHorizontally and part2.type.connectsHorizontally

def _crystalsFused(part1:ShapePart,part2:ShapePart) -> bool:
    if None in (part1.type,part2.type):
        return False
    return part1.type.crystalBehavior and part2.type.crystalBehavior

def _getCorrectedIndex(list:list,index:int) -> int:
    if index > len(list)-1:
        return index - len(list)
    if index < 0:
        return len(list) + index
    return index

def _getConnectedSingleLayer(
    layer:list[ShapePart],
    index:int,
    connectedFunc:Callable[[ShapePart,ShapePart],bool]
) -> list[int]:

    if layer[index].type is None:
        return []

    connected = [index]
    previousIndex = index

    for i in range(index+1,len(layer)+index):
        curIndex = _getCorrectedIndex(layer,i)
        if not connectedFunc(layer[previousIndex],layer[curIndex]):
            break
        connected.append(curIndex)
        previousIndex = curIndex

    previousIndex = index
    for i in range(index-1,-len(layer)+index,-1):
        curIndex = _getCorrectedIndex(layer,i)
        if curIndex in connected:
            break
        if not connectedFunc(layer[previousIndex],layer[curIndex]):
            break
        connected.append(curIndex)
        previousIndex = curIndex

    return connected

def _getConnectedMultiLayer(
    layers:list[list[ShapePart]],
    layerIndex:int,
    partIndex:int,
    connectedFunc:Callable[[ShapePart,ShapePart],bool]
) -> list[tuple[int,int]]:

    if layers[layerIndex][partIndex].type is None:
        return []

    connected = [(layerIndex,partIndex)]
    for curLayer,curPart in connected:

        # same layer
        for partIndex in _getConnectedSingleLayer(layers[curLayer],curPart,connectedFunc):
            if (curLayer,partIndex) not in connected:
                connected.append((curLayer,partIndex))

        # layer below
        toCheckLayer, toCheckPart = curLayer-1, curPart
        if (curLayer > 0) and ((toCheckLayer,toCheckPart) not in connected):
            if connectedFunc(layers[curLayer][curPart],layers[toCheckLayer][toCheckPart]):
                connected.append((toCheckLayer,toCheckPart))

        # layer above
        toCheckLayer, toCheckPart = curLayer+1, curPart
        if (curLayer < (len(layers)-1)) and ((toCheckLayer,toCheckPart) not in connected):
            if connectedFunc(layers[curLayer][curPart],layers[toCheckLayer][toCheckPart]):
                connected.append((toCheckLayer,toCheckPart))

    return connected

def _breakCrystals(layers:list[list[ShapePart]],layerIndex:int,partIndex:int) -> None:
    for curLayer,curPart in _getConnectedMultiLayer(layers,layerIndex,partIndex,_crystalsFused):
        layers[curLayer][curPart] = ShapePart(None,None)

def _makeLayersFall(layers:list[list[ShapePart]]) -> list[list[ShapePart]]:

    def sepInGroups(layer:list[ShapePart]) -> list[list[int]]:
        handledIndexes = []
        groups = []
        for partIndex,_ in enumerate(layer):
            if partIndex in handledIndexes:
                continue
            group = _getConnectedSingleLayer(layer,partIndex,_gravityConnected)
            if group != []:
                groups.append(group)
                handledIndexes.extend(group)
        return groups

    def isPartSupported(layerIndex:int,partIndex:int,visitedParts:list[tuple[int,int]]) -> bool:

        if supportedPartStates[layerIndex][partIndex] is not None:
            return supportedPartStates[layerIndex][partIndex]

        curPart = layers[layerIndex][partIndex]

        def inner() -> bool:

            if layers[layerIndex][partIndex].type is None:
                return False

            if layerIndex == 0:
                return True

            toGiveVisitedParts = visitedParts + [(layerIndex,partIndex)]

            partUnderneath = layerIndex-1, partIndex
            if (
                (partUnderneath not in visitedParts)
                and isPartSupported(*partUnderneath,toGiveVisitedParts)
            ):
                return True

            nextPartPos = layerIndex, _getCorrectedIndex(layers[layerIndex],partIndex+1)
            if (
                (nextPartPos not in visitedParts)
                and _gravityConnected(curPart,layers[nextPartPos[0]][nextPartPos[1]])
                and isPartSupported(*nextPartPos,toGiveVisitedParts)
            ):
                return True

            prevPartPos = layerIndex, _getCorrectedIndex(layers[layerIndex],partIndex-1)
            if (
                (prevPartPos not in visitedParts)
                and _gravityConnected(curPart,layers[prevPartPos[0]][prevPartPos[1]])
                and isPartSupported(*prevPartPos,toGiveVisitedParts)
            ):
                return True

            partAbove = layerIndex+1, partIndex
            if (
                (partAbove[0] < len(layers))
                and (partAbove not in visitedParts)
                and (_crystalsFused(curPart,layers[partAbove[0]][partAbove[1]]))
                and isPartSupported(*partAbove,toGiveVisitedParts)
            ):
                return True

            return False

        result = inner()
        supportedPartStates[layerIndex][partIndex] = result
        return result

    # first pass of calculating supported parts
    supportedPartStates:list[list[bool|None]] = [[None for _ in range(len(layers[0]))] for _ in range(len(layers))]
    for layerIndex,layer in enumerate(layers):
        for partIndex in range(len(layer)):
            isPartSupported(layerIndex,partIndex,[])

    # if a crystal is marked as unsupported it will fall and thus break
    for layerIndex,layer in enumerate(layers):
        for partIndex,part in enumerate(layer):
            if (
                (part.type is not None)
                and (part.type.crystalBehavior)
                and (not supportedPartStates[layerIndex][partIndex])
            ):
                layer[partIndex] = ShapePart(None,None)

    # second pass of calculating supported parts since crystals breaking could have changed the state of other parts
    supportedPartStates:list[list[bool|None]] = [[None for _ in range(len(layers[0]))] for _ in range(len(layers))]
    for layerIndex,layer in enumerate(layers):
        for partIndex in range(len(layer)):
            isPartSupported(layerIndex,partIndex,[])

    for layerIndex,layer in enumerate(layers):

        if layerIndex == 0:
            continue

        for group in sepInGroups(layer):

            if any(supportedPartStates[layerIndex][p] for p in group):
                continue

            for fallToLayerIndex in range(layerIndex,-1,-1):
                if fallToLayerIndex == 0:
                    break
                fall = True
                for partIndex in group:
                    if layers[fallToLayerIndex-1][partIndex].type is not None:
                        fall = False
                        break
                if not fall:
                    break

            for partIndex in group:
                layers[fallToLayerIndex][partIndex] = layers[layerIndex][partIndex]
                layers[layerIndex][partIndex] = ShapePart(None,None)

    return layers

def _cleanUpEmptyUpperLayers(layers:list[list[ShapePart]]) -> list[list[ShapePart]]:
    for i in range(len(layers)-1,-1,-1):
        if any((p.type is not None) for p in layers[i]):
            break
    return layers[:i+1]

def _differentNumPartsUnsupported(func:Callable[...,typing.Any]):
    def wrapper(*args,**kwargs):
        shapes:list[Shape] = []
        for arg in args:
            if type(arg) == Shape:
                shapes.append(arg)
        if shapes != []:
            expected = shapes[0].numParts
            for shape in shapes[1:]:
                if shape.numParts != expected:
                    raise InvalidOperationInputs(
                        f"Shapes with differing number of parts per layer are not supported for operation '{func.__name__}'")
        return func(*args,**kwargs)
    return wrapper

def cut(shape:Shape,*,config:ShapeOperationConfig) -> list[Shape]:
    takeParts = math.ceil(shape.numParts/2)
    cutPoints = [(0,shape.numParts-1),(shape.numParts-takeParts,shape.numParts-takeParts-1)]
    layers = shape.layers
    for layerIndex,layer in enumerate(layers):
        for cutPoint in cutPoints:
            if _crystalsFused(layer[cutPoint[0]],layer[cutPoint[1]]):
                _breakCrystals(layers,layerIndex,cutPoint[0])
    shapeA = []
    shapeB = []
    for layer in layers:
        shapeA.append([*([ShapePart(None,None)]*(shape.numParts-takeParts)),*(layer[-takeParts:])])
        shapeB.append([*(layer[:-takeParts]),*([ShapePart(None,None)]*(takeParts))])
    shapeA, shapeB = [_cleanUpEmptyUpperLayers(_makeLayersFall(s)) for s in (shapeA,shapeB)]
    return [Shape(shapeA),Shape(shapeB)]

def halfCut(shape:Shape,*,config:ShapeOperationConfig) -> list[Shape]:
    return [cut(shape,config=config)[1]]

def rotate90CW(shape:Shape,*,config:ShapeOperationConfig) -> list[Shape]:
    newLayers = []
    for layer in shape.layers:
        newLayers.append([layer[-1],*(layer[:-1])])
    return [Shape(newLayers)]

def rotate90CCW(shape:Shape,*,config:ShapeOperationConfig) -> list[Shape]:
    newLayers = []
    for layer in shape.layers:
        newLayers.append([*(layer[1:]),layer[0]])
    return [Shape(newLayers)]

def rotate180(shape:Shape,*,config:ShapeOperationConfig) -> list[Shape]:
    takeParts = math.ceil(shape.numParts/2)
    newLayers = []
    for layer in shape.layers:
        newLayers.append([*(layer[takeParts:]),*(layer[:takeParts])])
    return [Shape(newLayers)]

@_differentNumPartsUnsupported
def swapHalves(shapeA:Shape,shapeB:Shape,*,config:ShapeOperationConfig) -> list[Shape]:
    numLayers = max(shapeA.numLayers,shapeB.numLayers)
    takeParts = math.ceil(shapeA.numParts/2)
    shapeACut, shapeBCut = cut(shapeA,config=config), cut(shapeB,config=config)
    shapeACut = [[*s.layers,*([[ShapePart(None,None)]*shapeA.numParts]*(numLayers-len(s.layers)))] for s in shapeACut]
    shapeBCut = [[*s.layers,*([[ShapePart(None,None)]*shapeB.numParts]*(numLayers-len(s.layers)))] for s in shapeBCut]
    returnShapeA = []
    returnShapeB = []
    for layerA0,layerA1,layerB0,layerB1 in zip(*shapeACut,*shapeBCut):
        returnShapeA.append([*(layerA1[:-takeParts]),*(layerB0[-takeParts:])])
        returnShapeB.append([*(layerB1[:-takeParts]),*(layerA0[-takeParts:])])
    returnShapeA, returnShapeB = _cleanUpEmptyUpperLayers(returnShapeA),_cleanUpEmptyUpperLayers(returnShapeB)
    return [Shape(returnShapeA),Shape(returnShapeB)]

@_differentNumPartsUnsupported
def stack(bottomShape:Shape,topShape:Shape,*,config:ShapeOperationConfig) -> list[Shape]:
    newLayers = bottomShape.layers + [[ShapePart(None,None) for _ in range(bottomShape.numParts)]] + topShape.layers
    newLayers = _cleanUpEmptyUpperLayers(_makeLayersFall(newLayers))
    newLayers = newLayers[:config.maxShapeLayers]
    return [Shape(newLayers)]

def topPaint(shape:Shape,color:Color,*,config:ShapeOperationConfig) -> list[Shape]:
    newLayers = shape.layers[:-1]
    newLayers.append([
        (
            ShapePart(p.type,color)
            if (p.type is not None) and p.type.canChangeColor else
            p
        )
        for p in shape.layers[-1]
    ])
    return [Shape(newLayers)]

def pushPin(shape:Shape,*,config:ShapeOperationConfig) -> list[Shape]:

    layers = shape.layers
    addedPins = []

    for part in layers[0]:
        if part.type is None:
            addedPins.append(ShapePart(None,None))
        else:
            addedPins.append(ShapePart(config.shapesConfig.pinPart,None))

    if len(layers) < config.maxShapeLayers:
        newLayers = [addedPins,*layers]
    else:
        newLayers = [addedPins,*(layers[:config.maxShapeLayers-1])]
        removedLayer = layers[config.maxShapeLayers-1]
        for partIndex,part in enumerate(newLayers[-1]):
            if _crystalsFused(part,removedLayer[partIndex]):
                _breakCrystals(newLayers,config.maxShapeLayers-1,partIndex)

    newLayers = _cleanUpEmptyUpperLayers(_makeLayersFall(newLayers))

    return [Shape(newLayers)]

def genCrystal(shape:Shape,color:Color,*,config:ShapeOperationConfig) -> list[Shape]:
    return [Shape([
        [
            (
                ShapePart(config.shapesConfig.crystalPart,color)
                if (p.type is None) or (p.type.replacedByCrystal) else
                p
            )
            for p in l
        ]
        for l in shape.layers
    ])]