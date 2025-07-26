from . import(
    gameObjects,
    islands,
    shapeCodes,
    utils,
    ingameData
)
from .blueprints import BuildingIds, BlueprintError, _checkStringLength

import enum
from dataclasses import dataclass
import typing

_RAIL_PATH_TYPES = [
    "Forward",
    "LeftTurn",
    "RightTurn",
    "LeftFwdSplitter",
    "RightFwdSplitter",
    "YSplitter",
    "YSplitterFlipped",
    "TripleSplitter",
    "TripleSplitterFlipped",
    "RightFwdMerger",
    "LeftFwdMerger",
    "YMerger",
    "TripleMerger"
]

_ISLAND_IDS = {
    "rails" : [
        islands.allIslands[f"Rail_{path}"].id
        for path in _RAIL_PATH_TYPES
    ],
    "disableableTrainUnloadingLanes" : [
        islands.allIslands[f"Layout_Train{pt}_{ct}{s}{f}"].id
        for ct in ("Shape","Fluid")
        for pt,s in (("Unloader","s"),("Transfer",""))
        for f in ("","_Flipped")
    ]
}

_NUM_CONNECTIONS_PER_RAIL = {
    "Forward" : 1,
    "LeftTurn" : 1,
    "RightTurn" : 1,
    "LeftFwdSplitter" : 2,
    "RightFwdSplitter" : 2,
    "YSplitter" : 2,
    "YSplitterFlipped" : 2,
    "TripleSplitter" : 3,
    "TripleSplitterFlipped" : 3,
    "RightFwdMerger" : 2,
    "LeftFwdMerger" : 2,
    "YMerger" : 2,
    "TripleMerger" : 3
}



class ShapeGeneratorType(enum.Enum):
    empty = "empty"
    shape = "shape"

class ShapeGenerator:

    def __init__(self,genType:ShapeGeneratorType,shape:gameObjects.Shape|None=None) -> None:
        self.genType = genType
        if genType == ShapeGeneratorType.shape:
            self.shape:gameObjects.Shape = shape

class FluidGeneratorType(enum.Enum):
    empty = "empty"
    paint = "paint"

class FluidGenerator:

    def __init__(self,genType:FluidGeneratorType,color:gameObjects.Color|None=None) -> None:
        self.genType = genType
        if genType == FluidGeneratorType.paint:
            self.color:gameObjects.Color = color

class SignalGeneratorType(enum.Enum):
    empty = "empty"
    null = "null"
    conflict = "conflict"
    number = "number"
    shape = "shape"
    fluid = "fluid"

class CompareMode(enum.Enum):
    Equal = 1
    GreaterEqual = 2
    Greater = 3
    Less = 4
    LessEqual = 5
    NotEqual = 6



@dataclass
class LabelExtraData:
    text:str

class SignalProducerExtraData:

    def __init__(
        self,
        signalType:SignalGeneratorType,
        *,
        number:int|None=None,
        shapeGen:ShapeGenerator|None=None,
        fluidGen:FluidGenerator|None=None
    ) -> None:
        self.signalType = signalType
        if signalType == SignalGeneratorType.number:
            self.number:int = number
        elif signalType == SignalGeneratorType.shape:
            self.shapeGen:ShapeGenerator = shapeGen
        elif signalType == SignalGeneratorType.fluid:
            self.fluidGen:FluidGenerator = fluidGen

@dataclass
class ItemProducerExtraData:
    shapeGen:ShapeGenerator

@dataclass
class FluidProducerExtraData:
    fluidGen:FluidGenerator

@dataclass
class ButtonExtraData:
    activated:bool

@dataclass
class ComparisonGateExtraData:
    compareMode:CompareMode

@dataclass
class OperatorSignalReceiverExtraData:
    channel:typing.Literal[0,1]

type BuildingExtraData = (
    LabelExtraData
    | SignalProducerExtraData
    | ItemProducerExtraData
    | FluidProducerExtraData
    | ButtonExtraData
    | ComparisonGateExtraData
    | OperatorSignalReceiverExtraData
)

# this is the best solution I found to have correct type hints,
# while not having to do extra work in other parts of the code,
# so instead of
# extra:LabelExtraData = building.extra
# it's
# extra = building.extra.label
class BuildingExtraDataHolder:

    def __init__(self,value:BuildingExtraData) -> None:
        if isinstance(value,LabelExtraData):
            self.label = value
        elif isinstance(value,SignalProducerExtraData):
            self.signalProducer = value
        elif isinstance(value,ItemProducerExtraData):
            self.itemProducer = value
        elif isinstance(value,FluidProducerExtraData):
            self.fluidProducer = value
        elif isinstance(value,ButtonExtraData):
            self.button = value
        elif isinstance(value,ComparisonGateExtraData):
            self.comparisonGate = value
        elif isinstance(value,OperatorSignalReceiverExtraData):
            self.operatorSignalReceiver = value
        else:
            raise ValueError(f"Invalid building extra data class : {value.__class__.__name__}")



@dataclass
class RailConnectionAllowedColors:
    b:bool
    g:bool
    r:bool
    w:bool
    c:bool
    m:bool
    y:bool

@dataclass
class RailExtraData:
    connectionColors:list[RailConnectionAllowedColors]

@dataclass
class DisableableTrainUnloadingLanesExtraData:
    disabledLanes:list[int]

type IslandExtraData = (
    RailExtraData
    | DisableableTrainUnloadingLanesExtraData
)

class IslandExtraDataHolder:
    def __init__(self,value:IslandExtraData) -> None:
        if isinstance(value,RailExtraData):
            self.rail = value
        elif isinstance(value,DisableableTrainUnloadingLanesExtraData):
            self.disableableTrainUnloadingLanes = value
        else:
            raise ValueError(f"Invalid island extra data class : {value.__class__.__name__}")



def decodeEntryExtraData(rawDecoded:bytes,entryType:str) -> BuildingExtraData|IslandExtraData|None:

    def standardDecode(rawDecoded:bytes,emptyIsLengthNegative1:bool) -> str:
        try:
            decodedBytes = utils.decodeStringWithLen(rawDecoded,emptyIsLengthNegative1=emptyIsLengthNegative1)
        except ValueError as e:
            raise BlueprintError(f"Error while decoding string : {e}")
        try:
            return decodedBytes.decode()
        except UnicodeDecodeError:
            raise BlueprintError(f"Can't decode from bytes")

    def getValidShapeGenerator(rawString:bytes) -> ShapeGenerator:

        _checkStringLength(rawString,1)

        if rawString[0] == 0:
            return ShapeGenerator(ShapeGeneratorType.empty)

        _checkStringLength(rawString,2)

        if (rawString[0] != 1) or (rawString[1] != 1):
            raise BlueprintError("First two bytes of shape generation string aren't '\\x01'")

        shapeCode = standardDecode(rawString[2:],True)
        valid, error, shapesConfig = shapeCodes.isShapeCodeValid(shapeCode,None,True)

        if not valid:
            raise BlueprintError(f"Invalid shape code : {error}")

        return ShapeGenerator(ShapeGeneratorType.shape,gameObjects.Shape.fromShapeCode(shapeCode,shapesConfig))

    def getValidFluidGenerator(rawString:bytes) -> FluidGenerator:

        _checkStringLength(rawString,1)

        if rawString[0] == 0:
            return FluidGenerator(FluidGeneratorType.empty)

        _checkStringLength(rawString,2)

        if rawString[0] != 1:
            raise BlueprintError("First byte of fluid generation string isn't '\\x01'")

        try:
            color = rawString[1:2].decode()
        except UnicodeDecodeError:
            raise BlueprintError("Invalid color")

        if ingameData.DEFAULT_COLOR_SCHEME.colorsByCode.get(color) is None:
            raise BlueprintError(f"Unknown color : '{color}'")

        return FluidGenerator(FluidGeneratorType.paint,ingameData.DEFAULT_COLOR_SCHEME.colorsByCode[color])

    if entryType == BuildingIds.label:
        return LabelExtraData(standardDecode(rawDecoded,False))

    if entryType == BuildingIds.signalProducer:

        _checkStringLength(rawDecoded,1)
        signalType = rawDecoded[0]

        if signalType > 7:
            raise BlueprintError(f"Unknown signal type : {signalType}")

        if signalType in (0,1,2): # empty, null, conflict
            return SignalProducerExtraData({
                0 : SignalGeneratorType.empty,
                1 : SignalGeneratorType.null,
                2 : SignalGeneratorType.conflict
            }[signalType])

        if signalType in (4,5): # bool
            return SignalProducerExtraData(
                SignalGeneratorType.number,
                number = 0 if signalType == 4 else 1
            )

        signalValue = rawDecoded[1:]

        if signalType == 3: # integer
            if len(signalValue) != 4:
                raise BlueprintError("Signal value must be 4 bytes long for integer signal type")
            return SignalProducerExtraData(
                SignalGeneratorType.number,
                number = int.from_bytes(signalValue,"little",signed=True)
            )

        if signalType == 6: # shape
            try:
                return SignalProducerExtraData(
                    SignalGeneratorType.shape,
                    shapeGen = getValidShapeGenerator(signalValue)
                )
            except BlueprintError as e:
                raise BlueprintError(f"Error while decoding shape signal value : {e}")

        # fluid
        try:
            return SignalProducerExtraData(
                SignalGeneratorType.fluid,
                fluidGen = getValidFluidGenerator(signalValue)
            )
        except BlueprintError as e:
            raise BlueprintError(f"Error while decoding fluid signal value : {e}")

    if entryType == BuildingIds.itemProducer:
        try:
            return ItemProducerExtraData(getValidShapeGenerator(rawDecoded))
        except BlueprintError as e:
            raise BlueprintError(f"Error while decoding shape generation string : {e}")

    if entryType == BuildingIds.fluidProducer:
        try:
            return FluidProducerExtraData(getValidFluidGenerator(rawDecoded))
        except BlueprintError as e:
            raise BlueprintError(f"Error while decoding fluid generation string : {e}")

    if entryType == BuildingIds.button:

        _checkStringLength(rawDecoded,1)

        return ButtonExtraData(rawDecoded[0] != 0)

    if entryType in (BuildingIds.compareGate,BuildingIds.compareGateMirrored):

        _checkStringLength(rawDecoded,1)

        compareMode = rawDecoded[0]

        if (compareMode < 1) or (compareMode > 6):
            raise BlueprintError(f"Unknown compare mode : {compareMode}")

        return ComparisonGateExtraData(CompareMode(compareMode))

    if entryType in (BuildingIds.globalSignalReceiver,BuildingIds.globalSignalReceiverMirrored):

        if rawDecoded != bytes([0,0,0,2]):
            raise BlueprintError("Must be '\\x00\\x00\\x00\\x02'")

        return None

    if entryType == BuildingIds.operatorSignalRceiver:

        if rawDecoded not in (bytes([0,0,0,2]),bytes([1,0,0,2])):
            raise BlueprintError("Must be '\\x00\\x00\\x00\\x02' or '\\x01\\x00\\x00\\x02'")

        return OperatorSignalReceiverExtraData(rawDecoded[0])

    # islands

    if entryType in _ISLAND_IDS["rails"]:

        numConnections = _NUM_CONNECTIONS_PER_RAIL[entryType.removeprefix("Rail_")]

        _checkStringLength(rawDecoded,1)

        numConnectionsInData = rawDecoded[0]
        if numConnectionsInData < numConnections:
            raise BlueprintError(f"Must have at least {numConnections} color information")

        colorData = rawDecoded[1:]
        if len(colorData) != 4*numConnectionsInData:
            raise BlueprintError("Color data isn't the indicated length")

        colorInts = [int.from_bytes(colorData[i*4:(i+1)*4],"little") for i in range(numConnectionsInData)]
        return RailExtraData([RailConnectionAllowedColors(*((c & (2**i)) != 0 for i in range(7))) for c in colorInts])

    if entryType in _ISLAND_IDS["disableableTrainUnloadingLanes"]:

        _checkStringLength(rawDecoded,4)

        numDisabledLanes = int.from_bytes(rawDecoded[:4],"little",signed=True)

        if numDisabledLanes < 0:
            raise BlueprintError("Number of disabled lanes must be positive")

        rawDisabledLanes = rawDecoded[4:]

        if len(rawDisabledLanes) < (numDisabledLanes*4):
            raise BlueprintError(f"Disabled lanes data must be at least {numDisabledLanes*4} bytes long")

        return DisableableTrainUnloadingLanesExtraData([
            int.from_bytes(rawDisabledLanes[i*4:(i+1)*4],"little",signed=True)
            for i in range(numDisabledLanes)
        ])

    return None

def encodeEntryExtraData(extra:BuildingExtraDataHolder|IslandExtraDataHolder|None,entryType:str) -> bytes|None:

    def standardEncode(string:str,emptyIsLengthNegative1:bool) -> bytes:
        return utils.encodeStringWithLen(string.encode(),emptyIsLengthNegative1=emptyIsLengthNegative1)

    def encodeShapeGen(shapeGen:ShapeGenerator) -> bytes:
        if shapeGen.genType == ShapeGeneratorType.empty:
            return (0).to_bytes()
        return bytes([1,1]) + utils.encodeStringWithLen(shapeGen.shape.toShapeCode().encode())

    def encodeFluidGen(fluidGen:FluidGenerator) -> bytes:
        if fluidGen.genType == FluidGeneratorType.empty:
            return (0).to_bytes()
        return (1).to_bytes() + fluidGen.color.code.encode()

    if entryType == BuildingIds.label:
        return standardEncode(extra.label.text,False)

    if entryType == BuildingIds.signalProducer:

        data = extra.signalProducer

        for type,byteValue in [
            (SignalGeneratorType.empty,0),
            (SignalGeneratorType.null,1),
            (SignalGeneratorType.conflict,2)
        ]:
            if data.signalType == type:
                return bytes([byteValue])

        if data.signalType == SignalGeneratorType.number:
            if data.number == 0:
                return (4).to_bytes()
            if data.number == 1:
                return (5).to_bytes()
            return (3).to_bytes() + data.number.to_bytes(4,"little",signed=True)

        if data.signalType == SignalGeneratorType.shape:
            return (6).to_bytes() + encodeShapeGen(data.shapeGen)

        if data.signalType == SignalGeneratorType.fluid:
            return (7).to_bytes() + encodeFluidGen(data.fluidGen)

    if entryType == BuildingIds.itemProducer:
        return encodeShapeGen(extra.itemProducer.shapeGen)

    if entryType == BuildingIds.fluidProducer:
        return encodeFluidGen(extra.fluidProducer.fluidGen)

    if entryType == BuildingIds.button:
        return int(extra.button.activated).to_bytes()

    if entryType in (BuildingIds.compareGate,BuildingIds.compareGateMirrored):
        return extra.comparisonGate.compareMode.value.to_bytes()

    if entryType in (BuildingIds.globalSignalReceiver,BuildingIds.globalSignalReceiverMirrored):
        return bytes([0,0,0,2])

    if entryType == BuildingIds.operatorSignalRceiver:
        return bytes([extra.operatorSignalReceiver.channel,0,0,2])

    # islands

    if entryType in _ISLAND_IDS["rails"]:
        colorInts:list[int] = []
        for color in extra.rail.connectionColors:
            encodedColor = 0
            if color.y:
                encodedColor += 64
            if color.m:
                encodedColor += 32
            if color.c:
                encodedColor += 16
            if color.w:
                encodedColor += 8
            if color.r:
                encodedColor += 4
            if color.g:
                encodedColor += 2
            if color.b:
                encodedColor += 1
            colorInts.append(encodedColor)
        return len(colorInts).to_bytes() + b"".join(c.to_bytes(4,"little") for c in colorInts)

    if entryType in _ISLAND_IDS["disableableTrainUnloadingLanes"]:
        lanes = extra.disableableTrainUnloadingLanes.disabledLanes
        return (
            len(lanes).to_bytes(4,"little",signed=True)
            + b"".join(l.to_bytes(4,"little",signed=True) for l in lanes)
        )

    if extra is None:
        return None

    raise ValueError(f"Attempt to encode extra data of entry that shouldn't have any ({entryType})")

def getDefaultEntryExtraData(entryType:str) -> BuildingExtraData|IslandExtraData|None:

    if entryType == BuildingIds.label:
        return LabelExtraData("Label")

    if entryType == BuildingIds.signalProducer:
        return SignalProducerExtraData(SignalGeneratorType.null)

    if entryType == BuildingIds.itemProducer:
        return ItemProducerExtraData(ShapeGenerator(ShapeGeneratorType.empty))

    if entryType == BuildingIds.fluidProducer:
        return FluidProducerExtraData(FluidGenerator(
            FluidGeneratorType.paint,
            ingameData.DEFAULT_COLOR_SCHEME.colorsByCode["r"]
        ))

    if entryType == BuildingIds.button:
        return ButtonExtraData(False)

    if entryType in (BuildingIds.compareGate,BuildingIds.compareGateMirrored):
        return ComparisonGateExtraData(CompareMode.Equal)

    if entryType == BuildingIds.operatorSignalRceiver:
        return OperatorSignalReceiverExtraData(0)

    # islands

    if entryType in _ISLAND_IDS["rails"]:
        return RailExtraData([
            RailConnectionAllowedColors(*(False for _ in range(7)))
            for _ in range(_NUM_CONNECTIONS_PER_RAIL[entryType.removeprefix("Rail_")])
        ])

    if entryType in _ISLAND_IDS["disableableTrainUnloadingLanes"]:
        return DisableableTrainUnloadingLanesExtraData([])

    return None