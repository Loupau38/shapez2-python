from . import gameObjects, utils, islands, buildings, shapeCodes
from .buildings import BuildingIds

import fixedint
import enum
from collections.abc import Callable
import typing
import inspect
import types

def checkpointHash(checkpointId:str) -> int:
    h = fixedint.UInt32(523423)
    for c in checkpointId:
        char = fixedint.UInt32(ord(c))
        h += char
        h += h << fixedint.Int32(10)
        h ^= h >> fixedint.Int32(6)
    h += h << fixedint.Int32(3)
    h ^= h >> fixedint.Int32(11)
    h += h << fixedint.Int32(15)
    return int(h)

class Checkpoint(enum.Enum):
    blobStart = checkpointHash("blob:start")
    blobEnd = checkpointHash("blob:end")
    island = checkpointHash("island")
    buildings = checkpointHash("buildings")
    building = checkpointHash("building")

class InvalidSerializedData(Exception): ...
class EndOfStreamError(InvalidSerializedData): ...

class BinaryStreamReader:

    def __init__(self,content:bytes,checkpoints:bool):
        self._content = content
        self._checkpoints = checkpoints
        self.pos = 0

    def read(self,numBytes:int) -> bytes:

        if (self.pos+numBytes) > len(self._content):
            raise EndOfStreamError("Not enough data to read")

        result = self._content[self.pos:self.pos+numBytes+1]
        self.pos += numBytes
        return result

    def readBool(self) -> bool:
        return self.read(1) != bytes([0])

    def _readGenericInt(self,numBytes:int,signed:bool) -> int:
        return int.from_bytes(self.read(numBytes),"little",signed=signed)

    def readShort(self) -> int:
        return self._readGenericInt(2,True)

    def readUShort(self) -> int:
        return self._readGenericInt(2,False)

    def readInt(self) -> int:
        return self._readGenericInt(4,True)

    def readUInt(self) -> int:
        return self._readGenericInt(4,False)

    def readLong(self) -> int:
        return self._readGenericInt(8,True)

    def readULong(self) -> int:
        return self._readGenericInt(8,False)

    def readInt1(self) -> int:
        return self.read(1)[0]

    def readString(self) -> str|None:
        l = self.readShort()
        if l < -1:
            raise InvalidSerializedData(f"Invalid string length : {l}")
        if l == -1:
            return None
        if l == 0:
            return ""
        return self.read(l).decode()

    def assertCheckpoint(self,checkpoint:Checkpoint) -> None:
        if not self._checkpoints:
            return
        read = self.readUInt()
        if read != checkpoint.value:
            raise InvalidSerializedData(
                f"Checkpoint mismatch, excpected {checkpoint.value} ({checkpoint.name}), got {read}"
            )

    def readBlob(self,callback:Callable[[],None]) -> None:

        self.assertCheckpoint(Checkpoint.blobStart)
        blobLen = self.readInt()
        startPos = self.pos

        callback()

        if self.pos != startPos+blobLen:
            raise InvalidSerializedData("Blob isn't the expected length")

        self.assertCheckpoint(Checkpoint.blobEnd)

class BinaryStreamWriter:

    def __init__(self,checkpoints:bool):
        self._checkpoints = checkpoints
        self._content = bytearray()
        self.pos = 0

    def write(self,data:bytes) -> None:
        dataLen = len(data)
        self._content[self.pos:self.pos+dataLen] = data
        self.pos += dataLen

    def toBytes(self) -> bytes:
        return bytes(self._content)

    def writeBool(self,v:bool) -> None:
        self.write(bytes([v]))

    def _writeGenericInt(self,v:int,numBytes:int,signed:bool) -> None:
        self.write(v.to_bytes(numBytes,"little",signed=signed))

    def writeShort(self,v:int) -> None:
        self._writeGenericInt(v,2,True)

    def writeUShort(self,v:int) -> None:
        self._writeGenericInt(v,2,False)

    def writeInt(self,v:int) -> None:
        self._writeGenericInt(v,4,True)

    def writeUInt(self,v:int) -> None:
        self._writeGenericInt(v,4,False)

    def writeLong(self,v:int) -> None:
        self._writeGenericInt(v,8,True)

    def writeULong(self,v:int) -> None:
        self._writeGenericInt(v,8,False)

    def writeInt1(self,v:int) -> None:
        self.write(bytes([v]))

    def writeString(self,string:str|None) -> None:
        if string is None:
            self.writeShort(-1)
            return
        if len(string) == 0:
            self.writeShort(0)
            return
        encoded = string.encode()
        self.writeShort(len(encoded))
        self.write(encoded)

    def writeCheckpoint(self,checkpoint:Checkpoint) -> None:
        if not self._checkpoints:
            return
        self.writeUInt(checkpoint.value)

    def writeBlob(self,callback:Callable[[],None]) -> None:

        self.writeCheckpoint(Checkpoint.blobStart)
        startPos = self.pos
        self.writeInt(0) # reserve space for the length

        callback()

        endPos = self.pos
        blobLen = endPos - startPos - 4
        self.pos = startPos
        self.writeInt(blobLen)
        self.pos = endPos
        self.writeCheckpoint(Checkpoint.blobEnd)

class StringLUTReadWrite:

    NULL_INDEX = -(2**31)

    def __init__(self):
        self._strings:list[str] = []
        self._stringToIndex:dict[str,int] = []

    def serialize(self,writer:BinaryStreamWriter) -> None:
        writer.writeInt(len(self._strings))
        for s in self._strings:
            encoded = s.encode()
            writer.writeInt(len(encoded))
            writer.write(encoded)

    def deserialize(self,reader:BinaryStreamReader) -> None:
        self._strings.clear()
        self._stringToIndex.clear()
        for i in range(reader.readInt()):
            string = reader.read(reader.readInt()).decode()
            self._strings.append(string)
            self._stringToIndex[string] = i

    def getIndex(self,string:str|None) -> int:
        if string is None:
            return self.NULL_INDEX
        if self._stringToIndex.get(string) is not None:
            return self._stringToIndex[string]
        i = len(self._strings)
        self._strings.append(string)
        self._stringToIndex[string] = i
        return i

    def getString(self,index:int) -> str|None:
        if index == self.NULL_INDEX:
            return None
        if (index < 0) or (index > len(self._strings)):
            raise InvalidSerializedData(f"LUT index {index} out of range [0;{len(self._strings)}[")
        return self._strings[index]

class BinaryStreamReaderWithStringLUT(BinaryStreamReader):

    def __init__(self,content:bytes,checkpoints:bool,stringLUT:StringLUTReadWrite):
        super().__init__(content,checkpoints)
        self._stringLUT = stringLUT

    def readString(self) -> str|None:
        return self._stringLUT.getString(self.readInt())

class BinaryStreamWriterWithStringLUT(BinaryStreamWriter):

    def __init__(self,checkpoints:bool,stringLUT:StringLUTReadWrite):
        super().__init__(checkpoints)
        self._stringLUT = stringLUT

    def writeString(self,string:str|None) -> None:
        self.writeInt(self._stringLUT.getIndex(string))

def serializationId(id:str):
    def wrapper(cls):
        cls._serializationId = id
        return cls
    return wrapper

class PolymorphicSerializer[T]:

    def __init__(self,supportedTypes:list[type[T]],serializer:"GameObjectsSerializer"):

        self.serializer = serializer

        for t in supportedTypes:
            if not hasattr(t,"_serializationId"):
                raise ValueError(f"{t.__name__} doesn't have a serialization ID")

        self.idsByType:dict[type[T],str] = {t:t._serializationId for t in supportedTypes}
        self.typesById:dict[str,type[T]] = {t._serializationId:t for t in supportedTypes}

    def deserialize(self,reader:BinaryStreamReader) -> T|None:

        objTypeId = reader.readString()

        if objTypeId is None:
            return None

        objType = self.typesById.get(objTypeId)

        if objType is None:
            raise InvalidSerializedData(f"Unknown serialization class ID : {objTypeId}")

        obj:T
        @reader.readBlob
        def _():
            nonlocal obj
            obj = self.serializer.deserialize(reader,objType)

        return obj

    def serialize(self,writer:BinaryStreamWriter,obj:T|None) -> None:

        if obj is None:
            writer.writeString(None)
            return

        objType = type(obj)
        objTypeId = self.idsByType.get(objType)

        if objTypeId is None:
            raise ValueError(f"Unknown type for polymorphic serialization : {objType.__name__}")

        writer.writeString(objTypeId)

        @writer.writeBlob
        def _():
            self.serializer.serialize(writer,obj)

class GameObjectsSerializer:

    def __init__(
        self,
        shapesConfig:gameObjects.ShapesConfiguration|list[gameObjects.ShapesConfiguration],
        colorScheme:gameObjects.ColorScheme|list[gameObjects.ColorScheme]
    ):
        if isinstance(shapesConfig,gameObjects.ShapesConfiguration):
            self.shapesConfigs = [shapesConfig]
        else:
            self.shapesConfigs = shapesConfig
        if isinstance(colorScheme,gameObjects.ColorScheme):
            self.colorSchemes = [colorScheme]
        else:
            self.colorSchemes = colorScheme

        self.simulationStateSerializer = PolymorphicSerializer(
            gameObjects.GenericSimulationState.__subclasses__(),
            self
        )

    def _processColorCode(self,colorCode:str) -> gameObjects.Color:
        possibleColorSchemes:list[gameObjects.ColorScheme] = []
        for testColorScheme in self.colorSchemes:
            if colorCode in testColorScheme.colorsByCode:
                possibleColorSchemes.append(testColorScheme)
        if len(possibleColorSchemes) == 0:
            raise InvalidSerializedData(f"Unknown color code : {colorCode}")
        self.colorSchemes = possibleColorSchemes
        return self.colorSchemes[0].colorsByCode[colorCode]

    def _processShapeCode(self,shapeCode:str|None) -> gameObjects.Shape:
        if shapeCode is None:
            raise InvalidSerializedData("Shape code can't be null")
        valid, error, shapeConfigs, colorSchemes = shapeCodes.isShapeCodeValid(
            shapeCode,self.shapesConfigs,self.colorSchemes,True
        )
        if not valid:
            raise InvalidSerializedData(f"Invalid shape code : {error}")
        self.shapesConfigs = shapeConfigs
        self.colorSchemes = colorSchemes
        return shapeCodes.parseShape(
            shapeCode,
            self.shapesConfigs[0],
            self.colorSchemes[0]
        )

    def _autoDeserialize[T](self,reader:BinaryStreamReader,into:type[T]) -> T:
        args = []
        for attrType in inspect.get_annotations(into).values():
            if isinstance(attrType,types.UnionType):
                if (
                    (len(attrType.__args__) != 2)
                    or (attrType.__args__[1] != types.NoneType)
                ):
                    raise ValueError(
                        f"Invalid union type for auto deserialization : {attrType}"
                    )
                actualType = attrType.__args__[0]
            else:
                actualType = attrType
            if actualType == bool:
                attrValue = reader.readBool()
            else:
                attrValue = self.deserialize(reader,actualType)
            args.append(attrValue)
        return into(*args)

    def deserialize[T](self,reader:BinaryStreamReader,into:type[T]) -> T:

        # general game objects

        if into == gameObjects.GlobalChunkCoordinate:
            return gameObjects.GlobalChunkCoordinate(
                reader.readInt(),
                reader.readInt(),
                reader.readShort()
            )

        if into == gameObjects.IslandTileCoordinate:
            return gameObjects.IslandTileCoordinate(
                reader.readShort(),
                reader.readShort(),
                reader.readInt1()
            )

        if into == gameObjects.GlobalTileCoordinate:
            return gameObjects.GlobalTileCoordinate(
                reader.readInt(),
                reader.readInt(),
                reader.readShort()
            )

        if into == utils.Rotation:
            return utils.Rotation(reader.readInt1())

        # game objects for config

        if into == gameObjects.GenericSignal:
            signalType = reader.readInt1()
            if signalType == 0:
                return None
            if signalType == 1:
                return gameObjects.NullSignal()
            if signalType == 2:
                return gameObjects.ConflictSignal()
            if signalType == 3:
                return gameObjects.IntegerSignal(reader.readInt())
            if signalType == 4:
                return gameObjects.IntegerSignal(0)
            if signalType == 5:
                return gameObjects.IntegerSignal(1)
            if signalType == 6:
                return gameObjects.BeltItemSignal.fromBeltItem(
                    self.deserialize(reader,gameObjects.GenericBeltItem)
                )
            if signalType == 7:
                return gameObjects.FluidSignal.fromFluid(
                    self.deserialize(reader,gameObjects.GenericFluid)
                )
            raise InvalidSerializedData(f"Unknown signal type : {signalType}")

        if into == gameObjects.GenericBeltItem:
            itemType = reader.readInt1()
            if itemType == 0:
                return None
            if itemType == 1:
                return self.deserialize(reader,gameObjects.ShapeItem)
            if itemType == 2:
                return self.deserialize(reader,gameObjects.FluidPackageItem)
            if itemType == 3:
                return self.deserialize(reader,gameObjects.FluidPackageOnTrack)
            if itemType == 4:
                return self.deserialize(reader,gameObjects.ShapePackageOnTrack)
            raise InvalidSerializedData(f"Unknown belt item type : {itemType}")

        if into == gameObjects.ShapeItem:
            if not reader.readBool():
                return None
            return gameObjects.ShapeItem(
                self._processShapeCode(reader.readString())
            )

        if into == gameObjects.FluidPackageItem:
            return self._autoDeserialize(reader,gameObjects.FluidPackageItem)

        if into == gameObjects.GenericFluid:
            fluidType = reader.readInt1()
            if fluidType == 0:
                return None
            if fluidType == 1:
                return gameObjects.ColorFluid(
                    self._processColorCode(chr(reader.readInt1()))
                )
            raise InvalidSerializedData(f"Unknown fluid type : {fluidType}")

        if into == gameObjects.FluidUnit:
            return gameObjects.FluidUnit(reader.readLong())

        if into == gameObjects.FluidPackageOnTrack:
            amount = reader.readShort()
            return gameObjects.FluidPackageOnTrack(
                amount,
                None if amount == 0 else self.deserialize(reader,gameObjects.GenericFluid)
            )

        if into == gameObjects.ShapePackageOnTrack:
            amount = reader.readShort()
            return gameObjects.ShapePackageOnTrack(
                amount,
                None if amount == 0 else self.deserialize(reader,gameObjects.ShapeItem)
            )

        if into == gameObjects.SignalChannelId:
            return gameObjects.SignalChannelId(reader.readInt())

        # island config

        if into == gameObjects.RailConfig:
            return gameObjects.RailConfig([
                gameObjects.RailConnectionColorFilter(reader.readInt())
                for _ in range(reader.readInt())
            ])

        if into == gameObjects.DisableableTrainUnloadingLanesConfig:
            return gameObjects.DisableableTrainUnloadingLanesConfig(reader.readInt())

        # building config

        if into == gameObjects.LabelConfig:
            return gameObjects.LabelConfig(reader.readString())

        if into == gameObjects.SignalProducerConfig:
            return self._autoDeserialize(reader,gameObjects.SignalProducerConfig)

        if into == gameObjects.ItemProducerConfig:
            return self._autoDeserialize(reader,gameObjects.ItemProducerConfig)

        if into == gameObjects.FluidProducerConfig:
            return self._autoDeserialize(reader,gameObjects.FluidProducerConfig)

        if into == gameObjects.ButtonConfig:
            return gameObjects.ButtonConfig(reader.readBool())

        if into == gameObjects.CompareGateConfig:
            compareMode = reader.readInt1()
            if (compareMode < 1) or (compareMode > 6):
                raise InvalidSerializedData(f"Unknown compare mode : {compareMode}")
            return gameObjects.CompareGateConfig(
                gameObjects.CompareMode(compareMode)
            )

        if into == gameObjects.GlobalSignalReceiverConfig:
            return self._autoDeserialize(reader,gameObjects.GlobalSignalReceiverConfig)

        # specific cases

        if into == islands.Island:
            islandId = reader.readString()
            island = islands.allIslands.get(islandId)
            if island is None:
                raise InvalidSerializedData(f"Unknown island ID : {islandId}")
            return island

        if into == buildings.BuildingInternalVariant:
            buildingId = reader.readString()
            building = buildings.allBuildingInternalVariants.get(buildingId)
            if building is None:
                raise InvalidSerializedData(f"Unknown building internal variant ID : {buildingId}")
            return building

        # simulation states

        if into == gameObjects.SimulationSteps:
            return gameObjects.SimulationSteps(reader.readLong())

        if into == gameObjects.BeltSlotState:
            if reader.readBool():
                return gameObjects.BeltSlotState(
                    self.deserialize(reader,gameObjects.GenericBeltItem),
                    self.deserialize(reader,gameObjects.SimulationSteps)
                )
            return gameObjects.BeltSlotState(None,gameObjects.SimulationSteps(0))

        if into == gameObjects.BeltLaneState:
            if reader.readBool():
                return gameObjects.BeltLaneState(
                    self.deserialize(reader,gameObjects.GenericBeltItem),
                    self.deserialize(reader,gameObjects.SimulationSteps)
                )
            return gameObjects.BeltLaneState(None,gameObjects.SimulationSteps(0))

        if into == gameObjects.FluidContainerState:
            return self._autoDeserialize(reader,gameObjects.FluidContainerState)

        if into == gameObjects.SimulationTicks:
            return gameObjects.SimulationTicks(reader.readLong())

        if into == gameObjects.ShapeCollapseResult:
            count = reader.readInt1()
            if count == 0:
                return None
            if reader.readBool():
                resultShape = self._processShapeCode(reader.readString())
            else:
                resultShape = None
            return gameObjects.ShapeCollapseResult(
                [
                    gameObjects.ShapeCollapseResultEntry(
                        self._processShapeCode(reader.readString()),
                        reader.readInt1(),
                        reader.readBool()
                    )
                    for _ in range(count)
                ],
                resultShape
            )

        if into == gameObjects.SignalTicks:
            return gameObjects.SignalTicks(reader.readLong())

        if into == gameObjects.SignalBuffer:
            arrayLen = reader.readInt()
            readCount = min(arrayLen,gameObjects.SignalBuffer.ARRAY_SIZE)
            values = [
                self.deserialize(reader,gameObjects.GenericSignal)
                for _ in range(readCount)
            ]
            [
                self.deserialize(reader,gameObjects.GenericSignal)
                for _ in range(max(arrayLen-readCount,0))
            ]
            return gameObjects.SignalBuffer(
                values,
                self.deserialize(reader,gameObjects.SimulationTicks),
                self.deserialize(reader,gameObjects.SignalTicks),
                reader.readBool()
            )

        if into == gameObjects.SignalConductorInputState:
            self._autoDeserialize(reader,gameObjects.SignalConductorInputState)



        if into == gameObjects.GenericSimulationState:
            return self.simulationStateSerializer.deserialize(reader)

        for cls in [
            gameObjects.ConveyorSimulationState,
            gameObjects.CrystalGeneratorSimulationState,
            gameObjects.FluidStorageSimulationState,
            gameObjects.FullCutterSimulationState,
            gameObjects.HalfCutterSimulationState,
            gameObjects.HalvesSwapperSimulationState,
            gameObjects.ItemProducerSimulationState,
            gameObjects.Lift1LayerSimulationState,
            gameObjects.Lift2LayerSimulationState,
            gameObjects.LogicGate2In1OutSimulationState,
            gameObjects.LogicGateCompareSimulationState,
            gameObjects.LogicGateIfSimulationState,
            gameObjects.LogicGateNotSimulationState
        ]:
            if into == cls:
                return self._autoDeserialize(reader,cls)

        raise ValueError(f"Unknown type for deserialization : {into}")

    def _autoSerialize(self,writer:BinaryStreamWriter,obj:typing.Any) -> None:
        for attrName,attrType in inspect.get_annotations(type(obj)).items():
            kwargs = {}
            if isinstance(attrType,types.UnionType):
                if (
                    (len(attrType.__args__) != 2)
                    or (attrType.__args__[1] != types.NoneType)
                ):
                    raise ValueError(
                        f"Invalid union type for auto serialization : {attrType}"
                    )
                kwargs["objTypeOverride"] = attrType.__args__[0]
            elif attrType.__name__.startswith("Generic"):
                kwargs["objTypeOverride"] = attrType
            attrValue = getattr(obj,attrName)
            if attrType == bool:
                writer.writeBool(attrValue)
            else:
                self.serialize(writer,attrValue,**kwargs)

    def serialize(self,writer:BinaryStreamWriter,obj:typing.Any,objTypeOverride:type|None=None) -> None:
        """Specify a type override when serializing a generic or if 'obj' can be None !"""

        if objTypeOverride is None:
            if obj is None:
                raise ValueError("Specify a type override when 'obj' can be None")
            objType = type(obj)
        else:
            objType = objTypeOverride

        typeMatch = None
        def f(func:Callable[[typing.Any],None],funcTypeOverride:type|None=None) -> None:
            nonlocal typeMatch
            if funcTypeOverride is None:
                funcType = inspect.get_annotations(func)["obj"]
            else:
                funcType = funcTypeOverride
            if objType == funcType:
                if typeMatch is not None:
                    raise ValueError(f"Attempt to serialize twice ('{typeMatch}' and '{funcType}')")
                typeMatch = funcType
                func(obj)

        # general game objects

        @f
        def _(obj:gameObjects.GlobalChunkCoordinate):
            writer.writeInt(obj.x)
            writer.writeInt(obj.y)
            writer.writeShort(obj.z)

        @f
        def _(obj:gameObjects.IslandTileCoordinate):
            writer.writeShort(obj.x)
            writer.writeShort(obj.y)
            writer.writeInt1(obj.z)

        @f
        def _(obj:gameObjects.GlobalTileCoordinate):
            writer.writeInt(obj.x)
            writer.writeInt(obj.y)
            writer.writeShort(obj.z)

        @f
        def _(obj:utils.Rotation):
            writer.writeInt1(obj.value)

        # game objects for config

        @f
        def _(obj:gameObjects.GenericSignal):
            if obj is None:
                writer.writeInt1(0)
                return
            if isinstance(obj,gameObjects.NullSignal):
                writer.writeInt1(1)
                return
            if isinstance(obj,gameObjects.ConflictSignal):
                writer.writeInt1(2)
                return
            if isinstance(obj,gameObjects.IntegerSignal):
                v = obj.value
                if v == 0:
                    writer.writeInt1(4)
                elif v == 1:
                    writer.writeInt1(5)
                else:
                    writer.writeInt1(3)
                    writer.writeInt(v)
                return
            if isinstance(obj,gameObjects.BeltItemSignal):
                writer.writeInt1(6)
                self.serialize(writer,obj.beltItem,gameObjects.GenericBeltItem)
                return
            if isinstance(obj,gameObjects.FluidSignal):
                writer.writeInt1(7)
                self.serialize(writer,obj.fluid,gameObjects.GenericFluid)
                return
            raise ValueError(f"Unknown signal type : {type(obj)}")

        @f
        def _(obj:gameObjects.GenericBeltItem):
            if obj is None:
                writer.writeInt1(0)
                return
            if isinstance(obj,gameObjects.ShapeItem):
                writer.writeInt1(1)
                self.serialize(writer,obj)
                return
            if isinstance(obj,gameObjects.FluidPackageItem):
                writer.writeInt1(2)
                self.serialize(writer,obj)
                return
            if isinstance(obj,gameObjects.FluidPackageOnTrack):
                writer.writeInt1(3)
                self.serialize(writer,obj)
                return
            if isinstance(obj,gameObjects.ShapePackageOnTrack):
                writer.writeInt1(4)
                self.serialize(writer,obj)
                return
            raise ValueError(f"Unknown belt item type : {type(obj)}")

        @f
        def _(obj:gameObjects.ShapeItem):
            if obj is None:
                writer.writeBool(False)
            else:
                writer.writeBool(True)
                writer.writeString(obj.shape.toShapeCode())

        @f
        def _(obj:gameObjects.FluidPackageItem):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:gameObjects.GenericFluid):
            if obj is None:
                writer.writeInt1(0)
                return
            if isinstance(obj,gameObjects.ColorFluid):
                writer.writeInt1(1)
                writer.writeInt1(ord(obj.color.code))
                return
            raise ValueError(f"Unknown fluid type : {type(obj)}")

        @f
        def _(obj:gameObjects.FluidUnit):
            writer.writeLong(obj.units)

        @f
        def _(obj:gameObjects.FluidPackageOnTrack):
            writer.writeShort(obj.amount)
            if obj.amount != 0:
                self.serialize(writer,obj.fluid,gameObjects.GenericFluid)

        @f
        def _(obj:gameObjects.ShapePackageOnTrack):
            writer.writeShort(obj.amount)
            if obj.amount != 0:
                self.serialize(writer,obj.shape,gameObjects.ShapeItem)

        @f
        def _(obj:gameObjects.SignalChannelId):
            writer.writeInt(obj.uid)

        # island config

        @f
        def _(obj:gameObjects.RailConfig):
            writer.writeInt1(len(obj.connectionFilters))
            for colorFilter in obj.connectionFilters:
                writer.writeInt(colorFilter.mask)

        @f
        def _(obj:gameObjects.DisableableTrainUnloadingLanesConfig):
            writer.writeInt(obj.mask)

        # building config

        @f
        def _(obj:gameObjects.LabelConfig):
            writer.writeString(obj.text)

        @f
        def _(obj:gameObjects.SignalProducerConfig):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:gameObjects.ItemProducerConfig):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:gameObjects.FluidProducerConfig):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:gameObjects.ButtonConfig):
            writer.writeBool(obj.activated)

        @f
        def _(obj:gameObjects.CompareGateConfig):
            writer.writeInt1(obj.compareMode.value)

        @f
        def _(obj:gameObjects.GlobalSignalReceiverConfig):
            self._autoSerialize(writer,obj)

        # specifc cases

        @f
        def _(obj:islands.Island):
            writer.writeString(obj.id)

        @f
        def _(obj:buildings.BuildingInternalVariant):
            writer.writeString(obj.id)

        # simulation states

        @f
        def _(obj:gameObjects.SimulationSteps):
            writer.writeLong(obj.steps)

        @f
        def _(obj:gameObjects.BeltSlotState):
            if obj.item is None:
                writer.writeBool(False)
            else:
                writer.writeBool(True)
                self.serialize(writer,obj.item,gameObjects.GenericBeltItem)
                self.serialize(writer,obj.progress)

        @f
        def _(obj:gameObjects.BeltLaneState):
            if obj.item is None:
                writer.writeBool(False)
            else:
                writer.writeBool(True)
                self.serialize(writer,obj.item,gameObjects.GenericBeltItem)
                self.serialize(writer,obj.progress)

        @f
        def _(obj:gameObjects.FluidContainerState):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:gameObjects.SimulationTicks):
            writer.writeLong(obj.value)

        @f
        def _(obj:gameObjects.ShapeCollapseResult):
            if (obj is None) or (len(obj.entries) == 0):
                writer.writeInt1(0)
                return
            assert len(obj.entries) < 255 # ingame bug, should be '<='
            writer.writeInt1(len(obj.entries))
            if obj.shape is None:
                writer.writeBool(False)
            else:
                writer.writeBool(True)
                writer.writeString(obj.shape.toShapeCode())
            for entry in obj.entries:
                writer.writeString(entry.shape.toShapeCode())
                writer.writeInt1(entry.fallDownLayers)
                writer.writeBool(entry.vanish)

        @f
        def _(obj:gameObjects.SignalTicks):
            writer.writeLong(obj.value)

        @f
        def _(obj:gameObjects.SignalBuffer):
            writer.writeInt(gameObjects.SignalBuffer.ARRAY_SIZE)
            for i in range(gameObjects.SignalBuffer.ARRAY_SIZE):
                self.serialize(writer,obj.values[i],gameObjects.GenericSignal)
            self.serialize(writer,obj.lastStartTicks)
            self.serialize(writer,obj.lastSignalTick)
            writer.writeBool(obj.wasPushedThisStartTick)

        @f
        def _(obj:gameObjects.SignalConductorInputState):
            self._autoSerialize(writer,obj)



        @f
        def _(obj:gameObjects.GenericSimulationState):
            self.simulationStateSerializer.serialize(writer,obj)

        for cls in [
            gameObjects.ConveyorSimulationState,
            gameObjects.CrystalGeneratorSimulationState,
            gameObjects.FluidStorageSimulationState,
            gameObjects.FullCutterSimulationState,
            gameObjects.HalfCutterSimulationState,
            gameObjects.HalvesSwapperSimulationState,
            gameObjects.ItemProducerSimulationState,
            gameObjects.Lift1LayerSimulationState,
            gameObjects.Lift2LayerSimulationState,
            gameObjects.LogicGate2In1OutSimulationState,
            gameObjects.LogicGateCompareSimulationState,
            gameObjects.LogicGateIfSimulationState,
            gameObjects.LogicGateNotSimulationState
        ]:
            def func(obj):
                self._autoSerialize(writer,obj)
            f(func,cls)

        if typeMatch is None:
            raise ValueError(f"Unknown type for serialization : {objType}")

def deserializeBuildingConfig(
    buildingId:str,
    reader:BinaryStreamReader,
    serializer:GameObjectsSerializer,
    canBeNone:bool
) -> gameObjects.GenericBuildingConfig|None:

    data:dict[BuildingIds,type[gameObjects.GenericBuildingConfig]] = {
        BuildingIds.label : gameObjects.LabelConfig,
        BuildingIds.signalProducer : gameObjects.SignalProducerConfig,
        BuildingIds.itemProducer : gameObjects.ItemProducerConfig,
        BuildingIds.fluidProducer : gameObjects.FluidProducerConfig,
        BuildingIds.button : gameObjects.ButtonConfig,
        BuildingIds.compareGate : gameObjects.CompareGateConfig,
        BuildingIds.compareGateMirrored : gameObjects.CompareGateConfig,
        BuildingIds.globalSignalReceiver : gameObjects.GlobalSignalReceiverConfig,
        BuildingIds.globalSignalReceiverMirrored : gameObjects.GlobalSignalReceiverConfig,
        BuildingIds.operatorSignalRceiver : gameObjects.GlobalSignalReceiverConfig
    }

    for id,cls in data.items():
        if buildingId == id:
            return serializer.deserialize(reader,cls)

    if canBeNone:
        return None

    raise InvalidSerializedData(f"Attempt to deserialize config of '{buildingId}' which shouldn't have any")

def deserializeIslandConfig(
    islandId:str,
    reader:BinaryStreamReader,
    serializer:GameObjectsSerializer,
    canBeNone:bool
) -> gameObjects.GenericIslandConfig|None:

    data:list[tuple[list[str],type[gameObjects.GenericIslandConfig]]] = [
        (islands.ISLAND_IDS["rails"],gameObjects.RailConfig),
        (islands.ISLAND_IDS["disableableTrainUnloadingLanes"],gameObjects.DisableableTrainUnloadingLanesConfig)
    ]

    for ids,cls in data:
        if islandId in ids:
            return serializer.deserialize(reader,cls)

    if canBeNone:
        return None

    raise InvalidSerializedData(f"Attempt to deserialize config of '{islandId}' which shouldn't have any")