from . import (
    utils,
    shapeCodes,
    islands,
    buildings,
    versions,
    gameObjects
)
from .utils import Rotation, Pos, Size

import gzip
import base64
import json
import typing
import math
import binascii
import enum
import importlib.resources
from collections.abc import Callable

_T = typing.TypeVar("_T")
_T1 = typing.TypeVar("_T1")
_T2 = typing.TypeVar("_T2")



#region classes

PREFIX = "SHAPEZ2"
SEPARATOR = "-"
SUFFIX = "$"

ISLAND_ROTATION_CENTER = utils.FloatPos(*([(islands.ISLAND_SIZE/2)-.5]*2))

NUM_BP_ICONS = 4

# use variables instead of string literals and make potential ID changes not go unnoticed at the same time
# note : when changing an ID, make sure the migration functions still work as intended
_b = buildings.allBuildingInternalVariants
class BuildingIds(enum.StrEnum):
    label = _b["LabelDefaultInternalVariant"].id
    signalProducer = _b["ConstantSignalDefaultInternalVariant"].id
    itemProducer = _b["SandboxItemProducerDefaultInternalVariant"].id
    fluidProducer = _b["SandboxFluidProducerDefaultInternalVariant"].id
    button = _b["ButtonDefaultInternalVariant"].id
    compareGate = _b["LogicGateCompareInternalVariant"].id
    compareGateMirrored = _b["LogicGateCompareInternalVariantMirrored"].id
    globalSignalSender = _b["ControlledSignalTransmitterInternalVariant"].id
    globalSignalReceiver = _b["ControlledSignalReceiverInternalVariant"].id
    globalSignalReceiverMirrored = _b["ControlledSignalReceiverInternalVariantMirrored"].id
    operatorSignalRceiver = _b["WireGlobalTransmitterReceiverInternalVariant"].id
    beltTMerger = _b["MergerTShapeInternalVariant"].id
    painter = _b["PainterDefaultInternalVariant"].id
    painterMirrored = _b["PainterDefaultInternalVariantMirrored"].id
    crystalGenerator = _b["CrystalGeneratorDefaultInternalVariant"].id
    crystalGeneratorMirrored = _b["CrystalGeneratorDefaultInternalVariantMirrored"].id
del _b

class BlueprintError(Exception): ...

# ----- circular import workaround
def _checkStringLength(string:bytes,length:int) -> None:
    if len(string) < length:
        raise BlueprintError(f"String must be at least {length} bytes long")
from . import blueprintsExtraData
from .blueprintsExtraData import (
    BuildingExtraData,
    BuildingExtraDataHolder,
    IslandExtraData,
    IslandExtraDataHolder
)
# -----

class BlueprintType(enum.Enum):
    building = "Building"
    island = "Island"

class BlueprintIconType(enum.Enum):
    empty = "empty"
    icon = "icon"
    shape = "shape"

class BlueprintIcon:

    def __init__(
        self,
        type:BlueprintIconType,
        *,
        icon:str|None=None,
        shape:gameObjects.Shape|None=None
    ) -> None:
        self.type = type
        if type == BlueprintIconType.icon:
            self.icon:str = icon
        elif type == BlueprintIconType.shape:
            self.shape:gameObjects.Shape = shape

    @classmethod
    def decode(cls,raw:str|None) -> typing.Self:
        if raw is None:
            return cls(BlueprintIconType.empty)
        if raw.startswith("icon:"):
            return cls(BlueprintIconType.icon,icon=raw.removeprefix("icon:"))
        shapeCode = raw.removeprefix("shape:")
        validShapeCode, _, shapesConfig = shapeCodes.isShapeCodeValid(shapeCode,None,True)
        if validShapeCode:
            return cls(
                BlueprintIconType.shape,
                shape=gameObjects.Shape.fromShapeCode(shapeCode,shapesConfig)
            )
        return cls(BlueprintIconType.empty)

    def encode(self) -> str|None:
        if self.type == BlueprintIconType.empty:
            return None
        if self.type == BlueprintIconType.icon:
            return f"icon:{self.icon}"
        return f"shape:{self.shape.toShapeCode()}"

def _encodeEntryExtraData(extra:BuildingExtraDataHolder|IslandExtraDataHolder|None,entryType:str) -> str|None:
    encoded = blueprintsExtraData.encodeEntryExtraData(extra,entryType)
    if encoded is None:
        return None
    return base64.b64encode(encoded).decode()

class BuildingEntry:

    def __init__(
        self,
        pos:Pos,
        rotation:Rotation,
        type:buildings.BuildingInternalVariant,
        extra:BuildingExtraData|BuildingExtraDataHolder|None=None
    ) -> None:
        self.pos = pos
        self.rotation = rotation
        self.type = type
        if extra is None:
            extra = blueprintsExtraData.getDefaultEntryExtraData(type.id)
        if extra is None:
            self.extra = None
        elif isinstance(extra,BuildingExtraDataHolder):
            self.extra = extra
        else:
            self.extra = BuildingExtraDataHolder(extra)

    def encode(self) -> dict:
        toReturn = {
            "T" : self.type.id
        }
        _omitKeyIfDefault(toReturn,"X",self.pos.x)
        _omitKeyIfDefault(toReturn,"Y",self.pos.y)
        _omitKeyIfDefault(toReturn,"L",self.pos.z)
        _omitKeyIfDefault(toReturn,"R",self.rotation.value)
        _omitKeyIfDefault(toReturn,"C",_encodeEntryExtraData(self.extra,self.type.id))
        return toReturn

class BuildingBlueprint:

    def __init__(
        self,
        entries:list[BuildingEntry],
        icons:list[BlueprintIcon]|None=None
    ) -> None:
        self.entries = entries
        if icons is None:
            self.icons = getDefaultBlueprintIcons(BlueprintType.building)
        else:
            self.icons = icons

    def toTileDict(self) -> dict[Pos,"TileEntry[BuildingEntry]"]:
        return _getTileDictFromEntryList(self.entries)

    def getSize(self) -> Size:
        return _genericGetSize(self)

    def getBuildingCount(self) -> int:
        return len(self.entries)

    def getBuildingCounts(self) -> dict[buildings.BuildingInternalVariant,int]:
        return _genericGetCounts(self)

    def getTileCount(self) -> int:
        return len(self.toTileDict())

    def getValidIcons(self) -> list[BlueprintIcon]:
        return _genericGetValidIcons(self)

    def encode(self) -> dict:
        return {
            "$type" : BlueprintType.building.value,
            "Icon" : {
                "Data" : [i.encode() for i in self.icons]
            },
            "Entries" : [e.encode() for e in self.entries],
            "BinaryVersion" : versions.LATEST_GAME_VERSION # encoding always uses the latest format
        }

class IslandEntry:

    def __init__(
        self,pos:Pos,
        rotation:Rotation,
        type:islands.Island,
        extra:IslandExtraData|IslandExtraDataHolder|None=None,
        buildingBP:BuildingBlueprint|None=None
    ) -> None:
        self.pos = pos
        self.rotation = rotation
        self.type = type
        self.buildingBP = buildingBP
        if extra is None:
            extra = blueprintsExtraData.getDefaultEntryExtraData(type.id)
        if extra is None:
            self.extra = None
        elif isinstance(extra,IslandExtraDataHolder):
            self.extra = extra
        else:
            self.extra = IslandExtraDataHolder(extra)

    def encode(self) -> dict:
        toReturn:dict[str,typing.Any] = {
            "T" : self.type.id
        }
        _omitKeyIfDefault(toReturn,"X",self.pos.x)
        _omitKeyIfDefault(toReturn,"Y",self.pos.y)
        _omitKeyIfDefault(toReturn,"Z",self.pos.z)
        _omitKeyIfDefault(toReturn,"R",self.rotation.value)
        _omitKeyIfDefault(toReturn,"S",_encodeEntryExtraData(self.extra,self.type.id))
        if self.buildingBP is not None:
            toReturn["B"] = self.buildingBP.encode()
        return toReturn

class IslandBlueprint:

    def __init__(
        self,
        entries:list[IslandEntry],
        icons:list[BlueprintIcon]|None=None
    ) -> None:
        self.entries = entries
        if icons is None:
            self.icons = getDefaultBlueprintIcons(BlueprintType.island)
        else:
            self.icons = icons

    def toTileDict(self) -> dict[Pos,"TileEntry[IslandEntry]"]:
        return _getTileDictFromEntryList(self.entries)

    def getSize(self) -> Size:
        return _genericGetSize(self)

    def getIslandCount(self) -> int:
        return len(self.entries)

    def getIslandCounts(self) -> dict[islands.Island,int]:
        return _genericGetCounts(self)

    def getTileCount(self) -> int:
        return len(self.toTileDict())

    def getValidIcons(self) -> list[BlueprintIcon]:
        return _genericGetValidIcons(self)

    def encode(self) -> dict:
        return {
            "$type" : BlueprintType.island.value,
            "Icons" : {
                "Data" : [i.encode() for i in self.icons]
            },
            "Entries" : [e.encode() for e in self.entries]
        }

class Blueprint:

    def __init__(
        self,
        blueprint:BuildingBlueprint|IslandBlueprint,
        majorVersion:int=versions.LATEST_MAJOR_VERSION,
        version:int=versions.LATEST_GAME_VERSION
    ) -> None:
        self.innerBlueprint = blueprint
        self.majorVersion = majorVersion
        self.version = version
        if isinstance(blueprint,BuildingBlueprint):
            self.type = BlueprintType.building
            self.buildingBP = blueprint
            self.islandBP = None
        else:
            self.type = BlueprintType.island
            self.islandBP = blueprint
            tempBuildingList = []
            for island in blueprint.entries:
                if island.buildingBP is None:
                    continue
                for building in island.buildingBP.entries:
                    tempBuildingList.append(BuildingEntry(
                        Pos(
                            (island.pos.x*islands.ISLAND_SIZE) + building.pos.x,
                            (island.pos.y*islands.ISLAND_SIZE) + building.pos.y,
                            (island.pos.z*islands.ISLAND_SIZE) + building.pos.z
                        ),
                        building.rotation,
                        building.type,
                        building.extra
                    ))
            if tempBuildingList == []:
                self.buildingBP = None
            else:
                self.buildingBP = BuildingBlueprint(tempBuildingList,blueprint.icons)

    def getCost(self) -> int:
        # bp cost formula : last updated : alpha 15.2
        # note to self : dnSpy > BuildingBlueprint > ComputeCost() / ComputeTotalCost()
        if self.buildingBP is None:
            return 0
        buildingCount = self.buildingBP.getBuildingCount()
        if buildingCount <= 1:
            return 0
        try:
            return math.ceil((buildingCount-1) ** 1.3)
        except OverflowError:
            raise BlueprintError("Failed to compute blueprint cost")

    def getIslandUnitCost(self) -> int|float:
        if self.islandBP is None:
            return 0
        return sum(island.type.islandUnitCost for island in self.islandBP.entries)

    def encode(self) -> dict:
        return {
            "V" : versions.LATEST_GAME_VERSION, # encoding always uses the latest format
            "BP" : self.innerBlueprint.encode()
        }

class TileEntry[T:BuildingEntry|IslandEntry]:
    def __init__(self,referTo:T) -> None:
        self.referTo = referTo

def _genericGetSize(bp:BuildingBlueprint|IslandBlueprint) -> Size:
    (minX,minY,minZ), (maxX,maxY,maxZ) = [[func(getattr(e,k) for e in bp.toTileDict().keys()) for k in ("x","y","z")] for func in (min,max)]
    return Size(
        maxX - minX + 1,
        maxY - minY + 1,
        maxZ - minZ + 1
    )

def _genericGetCounts(
    bp:BuildingBlueprint|IslandBlueprint
) -> dict[buildings.BuildingInternalVariant|islands.Island,int]:
    output = {}
    for entry in bp.entries:
        entryType = entry.type
        if output.get(entryType) is None:
            output[entryType] = 1
        else:
            output[entryType] += 1
    return output

def _genericGetValidIcons(bp:BuildingBlueprint|IslandBlueprint) -> list[BlueprintIcon]:
    validIcons = []
    for icon in bp.icons[:NUM_BP_ICONS]:
        if icon.type == BlueprintIconType.empty:
            validIcons.append(icon)
            continue
        if icon.type == BlueprintIconType.icon:
            if (icon.icon in VALID_BP_ICONS) and (icon.icon != "Empty"):
                validIcons.append(icon)
            else:
                validIcons.append(BlueprintIcon(BlueprintIconType.empty))
            continue
        validIcons.append(icon)
    validIcons += [BlueprintIcon(BlueprintIconType.empty)] * (NUM_BP_ICONS-len(validIcons))
    return validIcons

def _omitKeyIfDefault(dict:dict,key:str,value:int|str|None) -> None:
    if value not in (None,0,""):
        dict[key] = value

_BuildingOrIslandT = typing.TypeVar("_BuildingOrIslandT",bound=BuildingEntry|IslandEntry)
def _getTileDictFromEntryList(entryList:list[_BuildingOrIslandT]) -> dict[Pos,TileEntry[_BuildingOrIslandT]]:
    tileDict:dict[Pos,TileEntry[_BuildingOrIslandT]] = {}
    for entry in entryList:
        if isinstance(entry,BuildingEntry):
            curTiles = entry.type.tiles
        else:
            curTiles = [t.pos for t in entry.type.tiles]
        curTiles = [t.rotateCW(entry.rotation) for t in curTiles]
        curTiles = [Pos(entry.pos.x+t.x,entry.pos.y+t.y,entry.pos.z+t.z) for t in curTiles]
        for curTile in curTiles:
            tileDict[curTile] = TileEntry(entry)
    return tileDict

def _getDefaultRawIcons(bpType:BlueprintType) -> list[str|None]:
    return [
        "icon:" + ("Buildings" if bpType == BlueprintType.building else "Platforms"),
        None,
        None,
        "shape:" + ("Cu"*4 if bpType == BlueprintType.building else "Ru"*4)
    ]

def _loadIcons() -> list[str]:
    with importlib.resources.files(__package__).joinpath("gameFiles/icons.json").open(encoding="utf-8") as f:
        return json.load(f)["Icons"]
VALID_BP_ICONS = _loadIcons()

#endregion



#region top level

_ERR_MSG_PATH_SEP = ">"
_ERR_MSG_PATH_START = "'"
_ERR_MSG_PATH_END = "' : "
_defaultObj = object()

def _getKeyValue(dict:dict[str,typing.Any],key:str,expectedValueType:type[_T1],*default:_T2) -> _T1|_T2:

    value = dict.get(key,_defaultObj)

    if value is _defaultObj:
        if len(default) == 0:
            raise BlueprintError(f"{_ERR_MSG_PATH_END}Missing '{key}' key")
        return default[0]

    valueType = type(value)
    if valueType != expectedValueType:
        raise BlueprintError(
            f"{_ERR_MSG_PATH_SEP}{key}{_ERR_MSG_PATH_END}Incorrect value type, expected '{expectedValueType.__name__}', got '{valueType.__name__}'")

    return value

def _decodeBlueprintFirstPart(rawBlueprint:str) -> tuple[dict,int]:

    try:

        sepCount = rawBlueprint.count(SEPARATOR)
        if sepCount != 2:
            raise BlueprintError(f"Expected 2 separators, got {sepCount}")

        prefix, majorVersion, codeAndSuffix = rawBlueprint.split(SEPARATOR)

        if prefix != PREFIX:
            raise BlueprintError("Incorrect prefix")

        if not utils.isNumber(majorVersion):
            raise BlueprintError("Version not a number")
        majorVersion = int(majorVersion)

        if not codeAndSuffix.endswith(SUFFIX):
            raise BlueprintError("Doesn't end with suffix")

        encodedBP = codeAndSuffix.removesuffix(SUFFIX)

        if encodedBP == "":
            raise BlueprintError("Empty encoded section")

        try:
            encodedBP = base64.b64decode(encodedBP,validate=True)
        except binascii.Error:
            raise BlueprintError("Can't decode from base64")
        try:
            encodedBP = gzip.decompress(encodedBP)
        except Exception as e:
            raise BlueprintError(f"Can't gzip decompress ({e.__class__.__name__})")
        try:
            decodedBP = json.loads(encodedBP)
        except Exception as e:
            raise BlueprintError(f"Can't parse json ({e.__class__.__name__})")

        if type(decodedBP) != dict:
            raise BlueprintError("Decoded value isn't a json object")

        try:
            _getKeyValue(decodedBP,"V",int)
            _getKeyValue(decodedBP,"BP",dict)
        except BlueprintError as e:
            raise BlueprintError(f"Error in {_ERR_MSG_PATH_START}blueprint json object{e}")

    except BlueprintError as e:
        raise BlueprintError(f"Error while decoding blueprint string : {e}")

    return decodedBP, majorVersion

def _encodeBlueprintLastPart(blueprint:dict) -> str:
    blueprintB64 = base64.b64encode(gzip.compress(json.dumps(blueprint,separators=(",",":")).encode())).decode()
    blueprintStr = (
        PREFIX
        + SEPARATOR
        + str(versions.LATEST_MAJOR_VERSION) # encoding always uses the latest format
        + SEPARATOR
        + blueprintB64
        + SUFFIX
    )
    return blueprintStr

#endregion



#region migration

def _standardExtraDataMigration(
    entry:dict,
    func:Callable[[bytes],None],
    errMsgBase:str,
    extraDataMinLength:int|None,
    extraDataKey:str="C"
) -> None:

    try:
        extraData = _getKeyValue(entry,extraDataKey,str)
    except BlueprintError as e:
        raise BlueprintError(f"{_ERR_MSG_PATH_SEP}{errMsgBase}{e}")

    try:

        try:
            rawDecoded = base64.b64decode(extraData,validate=True)
        except binascii.Error:
            raise BlueprintError("Can't decode from base64")

        if extraDataMinLength is not None:
            _checkStringLength(rawDecoded,extraDataMinLength)

        func(rawDecoded)

    except BlueprintError as e:
        raise BlueprintError(f"{_ERR_MSG_PATH_SEP}{extraDataKey}{_ERR_MSG_PATH_SEP}{errMsgBase}{_ERR_MSG_PATH_END}{e}")

def _standardEntryTypeMigration(entry:dict,convertion:dict[str,str]) -> None:
    entry["T"] = convertion.get(entry["T"],entry["T"])

def _migrationV1024(entry:dict) -> None:
    if entry["T"] == BuildingIds.beltTMerger:
        entry["R"] = (entry.get("R",0)-1) % 4
    if entry["T"] == "StackerDefaultInternalVariant":
        entry["T"] = "StackerStraightInternalVariant"

def _migrationV1040(entry:dict) -> None:
    if entry["T"] == "LayoutMinerCompact":
        entry["T"] = "ShapeMinerLayout"

def _migrationV1045(entry:dict) -> None:

    _standardEntryTypeMigration(entry,{
        "Layout_1"                    : "Layout_Normal_1",
        "Layout_1_Forward"            : "Layout_Normal_1",
        "Layout_1_LeftTurn"           : "Layout_Normal_1",
        "Layout_1_RightTurn"          : "Layout_Normal_1",
        "LayoutTunnelEntrance"        : "Layout_SpaceBeltTunnel_Entrance",
        "LayoutTunnelExit"            : "Layout_SpaceBeltTunnel_Exit",
        "ShapeMinerLayout"            : "Layout_ShapeMiner",
        "ChainMiner"                  : "Layout_ShapeMinerExtension",
        "TrainProducer"               : "Layout_TrainProducer_Blue",
        "Layout_2"                    : "Layout_Normal_2",
        "LayoutFluidExtractor"        : "Layout_FluidMiner",
        "Layout_3_L"                  : "Layout_Normal_3_L",
        "Layout_4_Quad_TwoNotches"    : "Layout_Normal_4_2x2",
        "Layout_4_T"                  : "Layout_Normal_4_T",
        "Layout_5_Cross"              : "Layout_Normal_5_Cross",
        "Layout_9_Quad_TopAllNotches" : "Layout_Normal_9_3x3"
    })

    def inner(rawDecoded:bytes) -> None:

        def shapeGen(data:bytes) -> bytes:
            try:
                shape = utils.decodeStringWithLen(data)
            except ValueError as e:
                raise BlueprintError(f"Error while decoding shape generator string : {e}")
            if shape == b"":
                return data
            if shape.startswith((b"shapecrate:",b"fluidcrate:")):
                newShape = b"shape:CuCuCuCu"
            elif shape.startswith(b"shape:"):
                newShape = b"shape:" + shape.removeprefix(b"shape:").replace(b"p",b"m")
            else:
                raise BlueprintError("No valid prefix in shape generator")
            return utils.encodeStringWithLen(newShape)

        def fluidGen(data:bytes) -> bytes:
            try:
                fluid = utils.decodeStringWithLen(data)
            except ValueError as e:
                raise BlueprintError(f"Error while decoding fluid generator string : {e}")
            return utils.encodeStringWithLen(fluid.replace(b"p",b"m"))

        if entry["T"] == BuildingIds.itemProducer:
            newData = shapeGen(rawDecoded)
        elif entry["T"] == BuildingIds.fluidProducer:
            newData = fluidGen(rawDecoded)
        else:
            _checkStringLength(rawDecoded,1)
            signalType = rawDecoded[0]
            signalValue = rawDecoded[1:]
            if signalType == 6:
                newData = (6).to_bytes() + shapeGen(signalValue)
            elif signalType == 7:
                newData = (7).to_bytes() + fluidGen(signalValue)
            else:
                return

        entry["C"] = base64.b64encode(newData).decode()

    if entry["T"] in (
        BuildingIds.itemProducer,
        BuildingIds.fluidProducer,
        BuildingIds.signalProducer
    ):
        _standardExtraDataMigration(entry,inner,"item/fluid/signal producer migration to v1045",None)

def _migrationV1057(entry:dict) -> None:

    def inner(rawDecoded:bytes) -> None:

        def shapeGen(data:bytes) -> bytes:
            try:
                shape = utils.decodeStringWithLen(data)
            except ValueError as e:
                raise BlueprintError(f"Error while decoding shape generator string : {e}")
            if shape == b"":
                return (0).to_bytes()
            if not shape.startswith(b"shape:"):
                raise BlueprintError("No 'shape:' prefix in shape generator")
            return bytes([1,1]) + utils.encodeStringWithLen(
                shape.removeprefix(b"shape:").replace(b"k",b"u")
            )

        def fluidGen(data:bytes) -> bytes:
            try:
                fluid = utils.decodeStringWithLen(data)
            except ValueError as e:
                raise BlueprintError(f"Error while decoding fluid generator string : {e}")
            if fluid == b"":
                return (0).to_bytes()
            if not fluid.startswith(b"color-"):
                raise BlueprintError("No 'color-' prefix in fluid generator")
            return (1).to_bytes() + fluid.removeprefix(b"color-").replace(b"k",b"u")

        if entry["T"] == BuildingIds.itemProducer:
            newData = shapeGen(rawDecoded)
        elif entry["T"] == BuildingIds.fluidProducer:
            newData = fluidGen(rawDecoded)
        else:
            _checkStringLength(rawDecoded,1)
            signalType = rawDecoded[0]
            signalValue = rawDecoded[1:]
            if signalType == 6:
                newData = (6).to_bytes() + shapeGen(signalValue)
            elif signalType == 7:
                newData = (7).to_bytes() + fluidGen(signalValue)
            else:
                return

        entry["C"] = base64.b64encode(newData).decode()

    if entry["T"] in (
        BuildingIds.itemProducer,
        BuildingIds.fluidProducer,
        BuildingIds.signalProducer
    ):
        _standardExtraDataMigration(entry,inner,"item/fluid/signal producer migration to v1057",None)

def _migrationV1064(entry:dict) -> None:
    _standardEntryTypeMigration(entry,{
        "BeltDefaultRightInternalVariant"    : "BeltDefaultLeftInternalVariantMirrored",
        "Splitter1To2RInternalVariant"       : "Splitter1To2LInternalVariantMirrored",
        "Merger2To1RInternalVariant"         : "Merger2To1LInternalVariantMirrored",
        "Lift1DownRightInternalVariant"      : "Lift1DownLeftInternalVariantMirrored",
        "Lift1UpRightInternalVariant"        : "Lift1UpLeftInternalVariantMirrored",
        "Lift2DownRightInternalVariant"      : "Lift2DownLeftInternalVariantMirrored",
        "Lift2UpRightInternalVariant"        : "Lift2UpLeftInternalVariantMirrored",
        "CutterMirroredInternalVariant"      : "CutterDefaultInternalVariantMirrored",
        "StackerMirroredInternalVariant"     : "StackerDefaultInternalVariantMirrored",
        "PipeRightInternalVariant"           : "PipeLeftInternalVariantMirrored",
        "PipeUpRightInternalVariant"         : "PipeUpLeftInternalVariantMirrored",
        "Pipe2UpRightInternalVariant"        : "Pipe2UpLeftInternalVariantMirrored",
        "WireDefaultRightInternalVariant"    : "WireDefaultLeftInternalVariantMirrored",
        "WireDefault1UpRightInternalVariant" : "WireDefault1UpLeftInternalVariantMirrored",
        "WireDefault2UpRightInternalVariant" : "WireDefault2UpLeftInternalVariantMirrored"
    })

def _migrationV1067(entry:dict) -> None:

    SPACE_BELT_ID = "Layout_SpaceBeltNode"
    SPACE_PIPE_ID = "Layout_SpacePipeNode"
    RAIL_ID = "Layout_RailNode"

    _standardEntryTypeMigration(entry,{
        "FluidBridgeSenderInternalVariant"   : "FluidPortSenderInternalVariant",
        "FluidBridgeReceiverInternalVariant" : "FluidPortReceiverInternalVariant"
    })

    def inner(rawDecoded:bytes) -> None:
        if entry["T"] == RAIL_ID:
            new = (10).to_bytes() + rawDecoded
        else:
            new = (20).to_bytes() + rawDecoded
        entry["C"] = base64.b64encode(new).decode()

    if entry["T"] in (SPACE_BELT_ID,SPACE_PIPE_ID,RAIL_ID):
        _standardExtraDataMigration(entry,inner,"space belt/pipe/rail migration to v1067",None)

def _migrationV1082(entry:dict) -> None:

    GLOBAL_WIRE_RECEIVER_ID = "WireGlobalTransmitterReceiverInternalVariant"

    def inner(rawDecoded:bytes) -> None:
        entry["C"] = base64.b64encode(rawDecoded+(2).to_bytes()).decode()

    if entry["T"] == GLOBAL_WIRE_RECEIVER_ID:
        _standardExtraDataMigration(entry,inner,"global wire receiver migration to v1082",None)
    elif entry["T"] in (
        BuildingIds.painter,
        BuildingIds.painterMirrored,
        BuildingIds.crystalGenerator,
        BuildingIds.crystalGeneratorMirrored
    ):
        r = entry.get("R",0)
        if r == 0:
            offsets = (0,-1)
        elif r == 1:
            offsets = (1,0)
        elif r == 2:
            offsets = (0,1)
        else:
            offsets = (-1,0)
        if entry["T"] in (BuildingIds.painterMirrored,BuildingIds.crystalGeneratorMirrored):
            offsets = (-offsets[0],-offsets[1])
        entry["X"] = entry.get("X",0) + offsets[0]
        entry["Y"] = entry.get("Y",0) + offsets[1]

def _migrationV1103(entry:dict) -> None:

    SPACE_BELT_ID = "Layout_SpaceBeltNode"
    SPACE_PIPE_ID = "Layout_SpacePipeNode"
    RAIL_ID = "Layout_RailNode"
    GLOBAL_WIRE_SENDER_ID = "WireGlobalTransmitterSenderInternalVariant"
    GLOBAL_WIRE_RECEIVER_ID = "WireGlobalTransmitterReceiverInternalVariant"

    def spaceBeltPipeRail() -> None:

        def fs(*args:_T) -> frozenset[_T]:
            return frozenset(args)

        conversionTable:dict[frozenset[tuple[int,int]],str] = {
            fs((0,0)) : "Forward",
            fs((0,3)) : "LeftTurn",
            fs((0,1)) : "RightTurn",
            fs((0,0),(0,3)) : "LeftFwdSplitter",
            fs((0,0),(0,1)) : "RightFwdSplitter",
            fs((0,3),(0,1)) : "YSplitter",
            fs((0,0),(0,3),(0,1)) : "TripleSplitter",
            fs((0,0),(1,0)) : "RightFwdMerger",
            fs((0,0),(3,0)) : "LeftFwdMerger",
            fs((1,0),(3,0)) : "YMerger",
            fs((0,0),(1,0),(3,0)) : "TripleMerger"
        }

        railColorOrder = {
            "Forward" : [(0,0)],
            "LeftTurn" : [(0,3)],
            "RightTurn" : [(0,1)],
            "LeftFwdSplitter" : [(0,0),(0,3)],
            "RightFwdSplitter" : [(0,0),(0,1)],
            "YSplitter" : [(0,1),(0,3)],
            "TripleSplitter" : [(0,0),(0,1),(0,3)],
            # order for the mergers made up as not easily checkable ingame and doesn't matter in game-generated blueprints
            "RightFwdMerger" : [(0,0),(1,0)],
            "LeftFwdMerger" : [(0,0),(3,0)],
            "YMerger" : [(3,0),(1,0)],
            "TripleMerger" : [(0,0),(3,0),(1,0)]
        }

        isRail = entry["T"] == RAIL_ID

        def inner(rawDecoded:bytes) -> None:

            layoutHeader = rawDecoded[0]
            if (not isRail) and (layoutHeader != 20):
                raise BlueprintError("First byte of space belt/pipe layout isn't '\\x14'")
            if (isRail) and (layoutHeader != 10):
                raise BlueprintError("First byte of rail layout isn't '\\x0a'")

            layoutType = rawDecoded[1]
            if (layoutType < 1) or (layoutType > 3):
                raise BlueprintError(f"Invalid layout type : {layoutType}")

            layoutData = rawDecoded[2:]
            dataLen = (6*layoutType) if isRail else (2*layoutType)
            if len(layoutData) != dataLen:
                raise BlueprintError("Incorrect layout data length")

            if isRail:
                connections = [(layoutData[i*6],layoutData[(i*6)+1]) for i in range(layoutType)]
                colorData = [layoutData[(i*6)+2:(i+1)*6] for i in range(layoutType)]
            else:
                connections = [(layoutData[i*2],layoutData[(i*2)+1]) for i in range(layoutType)]

            newLayoutType = None
            for newRotation in range(4):
                connectionsRotated = [((i-newRotation)%4,(o-newRotation)%4) for i,o in connections]
                connectionsFS = frozenset(connectionsRotated)
                potentialLayout = conversionTable.get(connectionsFS)
                if potentialLayout is not None:
                    newLayoutType = potentialLayout
                    break
            if newLayoutType is None:
                raise BlueprintError("Invalid layout data")

            entry["T"] = (
                ("Rail" if isRail else ("SpaceBelt" if entry["T"] == SPACE_BELT_ID else "SpacePipe"))
                + "_"
                + newLayoutType
            )
            entry["R"] = newRotation

            if not isRail:
                # entry["S"] intentionally not set
                return

            colorDataOrdered:list[bytes] = []
            for connection in railColorOrder[newLayoutType]:
                colorDataOrdered.append(colorData[connectionsRotated.index(connection)])

            entry["S"] = base64.b64encode(bytes([layoutType])+b"".join(colorDataOrdered)).decode()

        _standardExtraDataMigration(entry,inner,"space belt/pipe/rail migration to v1103",2)

    def globalWireTransmitter() -> None:

        isReceiver = entry["T"] == GLOBAL_WIRE_RECEIVER_ID

        def inner(rawDecoded:bytes) -> None:

            channel = int.from_bytes(rawDecoded[:4],"little",signed=True)

            if (channel < 0) or (channel > 7):
                raise BlueprintError("Channel out of range")

            encodedChannel = channel.to_bytes(3,"little")

            if isReceiver:
                isROS = rawDecoded[4] == 1
                entry["C"] = base64.b64encode(encodedChannel+bytes([2 if isROS else 1])).decode()
                return

            entry["C"] = base64.b64encode(encodedChannel).decode() + "AQQAAAABAQEBAAAAAAAAAIAAAAAAAAAAgAA="

        _standardExtraDataMigration(
            entry,
            inner,
            "global wire transmitter migration to v1103",
            5 if isReceiver else 4
        )

    if entry["T"] in (SPACE_BELT_ID,SPACE_PIPE_ID,RAIL_ID):
        spaceBeltPipeRail()
    elif entry["T"] in (GLOBAL_WIRE_SENDER_ID,GLOBAL_WIRE_RECEIVER_ID):
        globalWireTransmitter()

def _migrationV1118(entry:dict) -> None:
    _standardEntryTypeMigration(entry,{
        "Layout_Normal_1"       : "Foundation_1x1",
        "Layout_Normal_2"       : "Foundation_1x2",
        "Layout_Normal_3x1"     : "Foundation_1x3",
        "Layout_Normal_3_L"     : "Foundation_L3",
        "Layout_Normal_4_2x2"   : "Foundation_2x2",
        "Layout_Normal_4_T"     : "Foundation_T4",
        "Layout_Normal_3x2"     : "Foundation_2x3",
        "Layout_Normal_5_Cross" : "Foundation_C5",
        "Layout_Normal_9_3x3"   : "Foundation_3x3"
    })

def _migrationV1119(entry:dict,advanced:bool) -> None:

    GLOBAL_WIRE_SENDER_ID = "WireGlobalTransmitterSenderInternalVariant"
    GLOBAL_WIRE_RECEIVER_ID = "WireGlobalTransmitterReceiverInternalVariant"

    if entry["T"] == GLOBAL_WIRE_SENDER_ID:
        if not advanced:
            return
        entry["T"] = BuildingIds.globalSignalSender.value
        entry.pop("C",None)
        return

    def inner(rawDecoded:bytes) -> None:

        channel = int.from_bytes(rawDecoded[:3],"little")

        # set to a regular channel
        if (rawDecoded[3] == 1) and advanced:
            entry["T"] = BuildingIds.globalSignalReceiver.value
            entry["C"] = "AAAAAg=="
            return

        # set to a ROS channel
        if (rawDecoded[3] == 2) and (channel in (0,1)):
            newData = rawDecoded[:4]
        # regular channel or invalid, reset
        else:
            newData = bytes([0,0,0,2])

        entry["C"] = base64.b64encode(newData).decode()

    if entry["T"] == GLOBAL_WIRE_RECEIVER_ID:
        _standardExtraDataMigration(
            entry,
            inner,
            f"global wire receiver {"advanced" if advanced else "regular"} migration to v1119",
            4
        )

def _applyMigrationToEntry(bpVersion:int,entry:dict,advanced:bool) -> None:

    if bpVersion == 99999: # alpha 22.4-wiretest1
        bpVersion = 1075 # in between alpha 22.4 and 23

    data:list[tuple[
        Callable[[dict],None]|Callable[[dict,bool],None],
        bool|None
    ]] = [
        (_migrationV1024,True), # alpha 8
        (_migrationV1040,True), # alpha 17
        (_migrationV1045,True), # alpha 19
        (_migrationV1057,True), # alpha 20
        (_migrationV1064,True), # alpha 21
        (_migrationV1067,True), # alpha 22.2
        (_migrationV1082,True), # alpha 23
        (_migrationV1103,False), # 0.0.9
        (_migrationV1118,False), # 0.1.0-pre1
        (_migrationV1119,None) # 0.1.0-pre2
    ]

    for func,isFuncAdvanced in data:
        if bpVersion < int(func.__name__.removeprefix("_migrationV")):
            if isFuncAdvanced:
                if advanced:
                    func(entry)
            elif isFuncAdvanced is None:
                func(entry,advanced)
            else: # isFuncAdvanced is False
                if not advanced:
                    func(entry)

#endregion migration



#region decoding

def _getValidBlueprint(
    blueprint:dict,
    mainBPVersion:int,
    *,
    mustBeBuildingBP:bool=False,
    migrate:bool=False,
    emptyAfterMigrationIsInvalid:bool=True
) -> dict|None:

    validBP = {}

    bpTypeDefault:list[str] = []
    if migrate and (mainBPVersion < 1071): # older than alpha 22.3
        bpTypeDefault.append(BlueprintType.building.value)
    bpType = _getKeyValue(blueprint,"$type",str,*bpTypeDefault)

    if bpType not in BlueprintType:
        raise BlueprintError(f"{_ERR_MSG_PATH_SEP}$type{_ERR_MSG_PATH_END}Unknown blueprint type : '{bpType}'")

    bpTypeEnum = BlueprintType(bpType)
    isBuildingBP = bpTypeEnum == BlueprintType.building

    if mustBeBuildingBP and (not isBuildingBP):
        raise BlueprintError(f"{_ERR_MSG_PATH_SEP}$type{_ERR_MSG_PATH_END}Must be a building blueprint")

    validBP["$type"] = bpType

    bpIcons = _getKeyValue(blueprint,"Icon",dict,{"Data":_getDefaultRawIcons(bpTypeEnum)})

    try:

        bpIconsData = _getKeyValue(bpIcons,"Data",list,[])

        validIcons = []

        for i,icon in enumerate(bpIconsData):
            try:

                iconType = type(icon)

                if iconType in (dict,list):
                    raise BlueprintError(f"{_ERR_MSG_PATH_END}Incorrect value type")

                if iconType in (bool,int,float):
                    continue

                if icon == "":
                    icon = None

                if icon is None:
                    validIcons.append(icon)
                    continue

                icon:str

                if not icon.startswith(("icon:","shape:")):
                    continue

                if icon.startswith("icon:") and (len(icon.removeprefix("icon:")) in (0,1)):
                    continue

                validIcons.append(icon)

            except BlueprintError as e:
                raise BlueprintError(f"{_ERR_MSG_PATH_SEP}Data{_ERR_MSG_PATH_SEP}{i}{e}")

    except BlueprintError as e:
        raise BlueprintError(f"{_ERR_MSG_PATH_SEP}Icon{e}")

    validBP["Icon"] = {
        "Data" : validIcons
    }

    bpEntries = _getKeyValue(blueprint,"Entries",list)

    if bpEntries == []:
        raise BlueprintError(f"{_ERR_MSG_PATH_SEP}Entries{_ERR_MSG_PATH_END}Empty list")

    if isBuildingBP:
        versionForMigration = _getKeyValue(blueprint,"BinaryVersion",int,mainBPVersion)
    else:
        versionForMigration = mainBPVersion

    allowedEntryTypes = (
        buildings.allBuildingInternalVariants.keys()
        if isBuildingBP else
        islands.allIslands.keys()
    )
    layerKey = "L" if isBuildingBP else "Z"
    extraDataKey = "C" if isBuildingBP else "S"

    validBPEntries = []

    for i,entry in enumerate(bpEntries):
        deducedEntryType = None
        try:

            entryType = type(entry)
            if entryType != dict:
                raise BlueprintError(f"{_ERR_MSG_PATH_END}Incorrect value type, expected 'dict', got '{entryType.__name__}'")

            x, y, z, r = (_getKeyValue(entry,k,int,0) for k in ("X","Y",layerKey,"R"))

            if (r < 0) or (r > 3):
                raise BlueprintError(f"{_ERR_MSG_PATH_SEP}R{_ERR_MSG_PATH_END}Rotation must be in range from 0 to 3")

            deducedEntryType = t = _getKeyValue(entry,"T",str)

            _applyMigrationToEntry(versionForMigration,entry,migrate)

            # if migration changed the values
            deducedEntryType = t = entry["T"]
            x, y, z, r = (entry.get(k,0) for k in ("X","Y",layerKey,"R"))

            if t not in allowedEntryTypes:
                if migrate:
                    continue
                raise BlueprintError(f"{_ERR_MSG_PATH_SEP}T{_ERR_MSG_PATH_END}Unknown entry type '{t}'")

            validEntry = {
                "X" : x,
                "Y" : y,
                layerKey : z,
                "R" : r,
                "T" : t
            }

            extraRaw = _getKeyValue(entry,extraDataKey,str,"")
            try:
                try:
                    extraBytes = base64.b64decode(extraRaw,validate=True)
                except binascii.Error:
                    raise BlueprintError("Can't decode from base64")
                extraDecoded = blueprintsExtraData.decodeEntryExtraData(extraBytes,t)
            except BlueprintError as e:
                raise BlueprintError(f"{_ERR_MSG_PATH_SEP}{extraDataKey}{_ERR_MSG_PATH_END}{e}")
            validEntry[extraDataKey] = extraDecoded

            if not isBuildingBP:
                b = entry.get("B",_defaultObj)
                if b is not _defaultObj:
                    b = _getKeyValue(entry,"B",dict)
                    try:
                        validB = _getValidBlueprint(b,mainBPVersion,mustBeBuildingBP=True,migrate=migrate,emptyAfterMigrationIsInvalid=False)
                    except BlueprintError as e:
                        raise BlueprintError(f"{_ERR_MSG_PATH_SEP}B{e}")
                    if validB is not None:
                        validEntry["B"] = validB

            validBPEntries.append(validEntry)

        except BlueprintError as e:
            if deducedEntryType is None:
                entryTypeInfo = ""
            else:
                entryTypeInfo = f" ({deducedEntryType})"
            raise BlueprintError(f"{_ERR_MSG_PATH_SEP}Entries{_ERR_MSG_PATH_SEP}{i}{entryTypeInfo}{e}")

    if validBPEntries == []:
        assert migrate
        if emptyAfterMigrationIsInvalid:
            raise BlueprintError(f"{_ERR_MSG_PATH_SEP}Entries{_ERR_MSG_PATH_END}Empty list")
        return None

    validBP["Entries"] = validBPEntries

    return validBP

def _decodeBuildingBP(rawBuildings:list[dict[str,typing.Any]],icons:list[str|None]) -> BuildingBlueprint:

    entryList:list[BuildingEntry] = []
    occupiedTiles:set[Pos] = set()

    for building in rawBuildings:

        curTiles = [t.rotateCW(building["R"]) for t in buildings.allBuildingInternalVariants[building["T"]].tiles]
        curTiles = [Pos(building["X"]+t.x,building["Y"]+t.y,building["L"]+t.z) for t in curTiles]

        for curTile in curTiles:

            if curTile in occupiedTiles:
                raise BlueprintError(f"Error while placing tile of '{building['T']}' at {curTile} : another tile is already placed there")

            occupiedTiles.add(curTile)

    for b in rawBuildings:
        entryList.append(BuildingEntry(
            Pos(b["X"],b["Y"],b["L"]),
            Rotation(b["R"]),
            buildings.allBuildingInternalVariants[b["T"]],
            b["C"]
        ))

    return BuildingBlueprint(entryList,[BlueprintIcon.decode(i) for i in icons])

def _decodeIslandBP(rawIslands:list[dict[str,typing.Any]],icons:list[str|None]) -> IslandBlueprint:

    entryList:list[IslandEntry] = []
    occupiedTiles:set[Pos] = set()

    for island in rawIslands:

        curTiles = [t.pos.rotateCW(island["R"]) for t in islands.allIslands[island["T"]].tiles]
        curTiles = [Pos(island["X"]+t.x,island["Y"]+t.y,island["Z"]+t.z) for t in curTiles]

        for curTile in curTiles:

            if curTile in occupiedTiles:
                raise BlueprintError(f"Error while placing tile of '{island['T']}' at {curTile} : another tile is already placed there")

            occupiedTiles.add(curTile)

    for island in rawIslands:

        islandEntryInfos:dict[str,Pos|int|islands.Island|IslandExtraData|None] = {
            "pos" : Pos(island["X"],island["Y"],island["Z"]),
            "r" : island["R"],
            "t" : islands.allIslands[island["T"]],
            "s" : island["S"]
        }

        if island.get("B") is None:
            entryList.append(IslandEntry(
                islandEntryInfos["pos"],
                Rotation(islandEntryInfos["r"]),
                islandEntryInfos["t"],
                islandEntryInfos["s"],
                None
            ))
            continue

        try:
            curBuildingBP = _decodeBuildingBP(island["B"]["Entries"],island["B"]["Icon"]["Data"])
        except BlueprintError as e:
            raise BlueprintError(
                f"Error while creating building blueprint representation of '{islandEntryInfos['t'].id}' at {islandEntryInfos['pos']} : {e}")

        curIslandBuildArea = [a.rotateCW(islandEntryInfos["r"],ISLAND_ROTATION_CENTER) for a in islandEntryInfos["t"].totalBuildArea]

        for pos,b in curBuildingBP.toTileDict().items():

            curBuilding = b.referTo

            inArea = False
            for area in curIslandBuildArea:
                if area.containsPos(pos) and (pos.z >= 0) and (pos.z < islands.ISLAND_SIZE):
                    inArea = True
                    break
            if not inArea:
                raise BlueprintError(
                    f"Error in '{islandEntryInfos['t'].id}' at {islandEntryInfos['pos']} : tile of building '{curBuilding.type.id}' at {pos} is not inside its platform build area")

        entryList.append(IslandEntry(
            islandEntryInfos["pos"],
            Rotation(islandEntryInfos["r"]),
            islandEntryInfos["t"],
            islandEntryInfos["s"],
            curBuildingBP
        ))

    return IslandBlueprint(entryList,[BlueprintIcon.decode(i) for i in icons])

#endregion



#region public functions

def getBlueprintVersion(blueprint:str) -> int:
    return _decodeBlueprintFirstPart(blueprint)[0]["V"]

def decodeBlueprint(rawBlueprint:str,migrate:bool=False) -> Blueprint:
    decodedBP, majorVersion = _decodeBlueprintFirstPart(rawBlueprint)
    version = decodedBP["V"]

    try:
        validBP = _getValidBlueprint(decodedBP["BP"],version,migrate=migrate)
    except BlueprintError as e:
        raise BlueprintError(f"Error in {_ERR_MSG_PATH_START}blueprint json object{_ERR_MSG_PATH_SEP}BP{e}")

    if validBP["$type"] == BlueprintType.building.value:
        func = _decodeBuildingBP
        text = "building"
    else:
        func = _decodeIslandBP
        text = "platform"

    try:
        decodedDecodedBP = func(validBP["Entries"],validBP["Icon"]["Data"])
    except BlueprintError as e:
        raise BlueprintError(f"Error while creating {text} blueprint representation : {e}")
    return Blueprint(decodedDecodedBP,majorVersion,version)

def encodeBlueprint(blueprint:Blueprint) -> str:
    return _encodeBlueprintLastPart(blueprint.encode())

def getPotentialBPCodesInString(string:str) -> list[str]:

    if PREFIX not in string:
        return []

    bps = string.split(PREFIX)[1:]

    bpCodes = []

    for bp in bps:

        if SUFFIX not in bp:
            continue

        bp = bp.split(SUFFIX)[0]

        bpCodes.append(PREFIX+bp+SUFFIX)

    return bpCodes

def getDefaultBlueprintIcons(bpType:BlueprintType) -> list[BlueprintIcon]:
    return [BlueprintIcon.decode(i) for i in _getDefaultRawIcons(bpType)]

#endregion