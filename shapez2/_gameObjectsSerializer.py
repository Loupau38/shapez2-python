from . import gameObjects, utils, islands, buildings, shapeCodes, savegameObjects
from .buildings import BuildingIds

import fixedint
import enum
from collections.abc import Callable
import typing
import inspect
import types
import struct
from dataclasses import dataclass

#region binary data

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
    fastBeltPathStart = checkpointHash("fast-belt-path:start")
    fastBeltPathEnd = checkpointHash("fast-belt-path:end")
    beltPathStateStart = checkpointHash("belt-path-state:start")
    beltPathStateEnd = checkpointHash("belt-path-state:end")
    trainData = checkpointHash("TrainData")
    superChunkStart = checkpointHash("super-chunk")
    superChunkShapeResources = checkpointHash("super-chunk:shape-resources")
    superChunkFluidResources = checkpointHash("super-chunk:fluid-resources")

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

    def readFloat(self) -> float:
        return struct.unpack("<f",self.read(4))[0]

    def readString(self) -> str|None:
        l = self.readShort()
        if l < -1:
            raise InvalidSerializedData(f"Invalid string length : {l}")
        if l == -1:
            return None
        if l == 0:
            return ""
        encoded = self.read(l)
        try:
            decoded = encoded.decode()
        except UnicodeDecodeError as e:
            raise InvalidSerializedData(f"Error while decoding string : {e}")
        return decoded

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

    def writeFloat(self,v:float) -> None:
        self.write(struct.pack("<f",v))

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
            encodedString = reader.read(reader.readInt())
            try:
                string = encodedString.decode()
            except UnicodeDecodeError as e:
                raise InvalidSerializedData(f"Error while decoding LUT string : {e}")
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



#region polymorphic

def serializationId(id:str):
    def wrapper(cls):
        # stop type hints from thinking that `cls` is strictly
        # `GenericSimulationState` and that it can't be a subclass
        if not typing.TYPE_CHECKING:
            if not issubclass(cls,savegameObjects.GenericSimulationState):
                raise ValueError(
                    cls.__name__
                    + " doesn't inherit from "
                    + savegameObjects.GenericSimulationState.__name__
                )
        cls._serializationId = id
        return cls
    return wrapper

class PolymorphicSerializer[T]:

    def __init__(self,supportedTypes:list[type[T]],serializer:"GameObjectsSerializer"):

        self.serializer = serializer

        seenIds = []
        for t in supportedTypes:
            if not hasattr(t,"_serializationId"):
                raise ValueError(f"{t.__name__} doesn't have a serialization ID")
            curId = t._serializationId
            if curId in seenIds:
                raise ValueError(f"Serialization ID registered twice : {curId}")
            seenIds.append(curId)

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

#endregion



#region special

# check for None not included so type hint still discards None from deduced type
def needsContainedType(cls:type) -> typing.NoReturn:
    raise ValueError(f"{cls.__name__} needs a contained type")

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
            savegameObjects.GenericSimulationState.__subclasses__(),
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


#endregion



#region deserialization

    def _autoDeserialize[T](self,reader:BinaryStreamReader,into:type[T]) -> T:
        args = []
        for attrType in inspect.get_annotations(into).values():
            if typing.get_origin(attrType) == types.UnionType:
                unionArgs = typing.get_args(attrType)
                if (
                    (len(unionArgs) != 2)
                    or (unionArgs[1] != types.NoneType)
                ):
                    raise ValueError(
                        f"Invalid union type for auto deserialization : {attrType}"
                    )
                actualType = unionArgs[0]
            else:
                actualType = attrType
            if actualType == bool:
                attrValue = reader.readBool()
            else:
                attrValue = self.deserialize(reader,actualType)
            args.append(attrValue)
        return into(*args)

    def deserialize[T](self,reader:BinaryStreamReader,into:type[T]) -> T:

        typeOrigin = typing.get_origin(into)
        if typeOrigin is None:
            containedType = None
        else:
            containedType = typing.get_args(into)[0]
            into = typeOrigin

#region general game objects

        if into == savegameObjects.GlobalChunkCoordinate:
            return savegameObjects.GlobalChunkCoordinate(
                reader.readInt(),
                reader.readInt(),
                reader.readShort()
            )

        if into == savegameObjects.IslandTileCoordinate:
            return savegameObjects.IslandTileCoordinate(
                reader.readShort(),
                reader.readShort(),
                reader.readInt1()
            )

        if into == savegameObjects.GlobalTileCoordinate:
            return savegameObjects.GlobalTileCoordinate(
                reader.readInt(),
                reader.readInt(),
                reader.readShort()
            )

        if into == utils.Rotation:
            return utils.Rotation(reader.readInt1())

#endregion
#region objects for config

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
                return gameObjects.PackageOnTrack(self.deserialize(
                    reader,
                    gameObjects.CargoPackage[gameObjects.GenericFluid] # FluidId ingame
                ))
            if itemType == 4:
                return gameObjects.PackageOnTrack(self.deserialize(
                    reader,
                    gameObjects.CargoPackage[gameObjects.ShapeItem] # ShapeId ingame
                ))
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

        if into == gameObjects.CargoPackage:
            if containedType is None:
                needsContainedType(gameObjects.CargoPackage)
            amount = reader.readShort()
            return gameObjects.CargoPackage(
                amount,
                None if amount == 0 else self.deserialize(reader,containedType),
                containedType
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

#endregion
#region misc

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

        if into == savegameObjects.LayeredWagonCargo:
            if containedType is None:
                needsContainedType(savegameObjects.LayeredWagonCargo)
            return savegameObjects.LayeredWagonCargo([
                self.deserialize(reader,containedType)
                for _ in range(reader.readInt1())
            ])

        if into == savegameObjects.CargoContainer:
            if containedType is None:
                needsContainedType(savegameObjects.CargoContainer)
            numPackages = reader.readShort()
            maxPackages = reader.readShort()
            return savegameObjects.CargoContainer(
                [
                    self.deserialize(reader,gameObjects.CargoPackage[containedType])
                    for _ in range(numPackages)
                ],
                maxPackages
            )

        # to use when ShapeDefinition is used ingame
        if into == gameObjects.Shape:
            return self._processShapeCode(reader.readString())

#endregion
#region simulation states

        if into == savegameObjects.SimulationSteps:
            return savegameObjects.SimulationSteps(reader.readLong())

        if into == savegameObjects.BeltSlotState:
            if reader.readBool():
                return savegameObjects.BeltSlotState(
                    self.deserialize(reader,gameObjects.GenericBeltItem),
                    self.deserialize(reader,savegameObjects.SimulationSteps)
                )
            return savegameObjects.BeltSlotState(None,savegameObjects.SimulationSteps(0))

        if into == savegameObjects.BeltLaneState:
            if reader.readBool():
                return savegameObjects.BeltLaneState(
                    self.deserialize(reader,gameObjects.GenericBeltItem),
                    self.deserialize(reader,savegameObjects.SimulationSteps)
                )
            return savegameObjects.BeltLaneState(None,savegameObjects.SimulationSteps(0))

        if into == savegameObjects.FluidContainerState:
            return self._autoDeserialize(reader,savegameObjects.FluidContainerState)

        if into == savegameObjects.SimulationTicks:
            return savegameObjects.SimulationTicks(reader.readLong())

        if into == savegameObjects.ShapeCollapseResult:
            count = reader.readInt1()
            if count == 0:
                return None
            if reader.readBool():
                resultShape = self._processShapeCode(reader.readString())
            else:
                resultShape = None
            return savegameObjects.ShapeCollapseResult(
                [
                    savegameObjects.ShapeCollapseResultEntry(
                        self._processShapeCode(reader.readString()),
                        reader.readInt1(),
                        reader.readBool()
                    )
                    for _ in range(count)
                ],
                resultShape
            )

        if into == savegameObjects.SignalTicks:
            return savegameObjects.SignalTicks(reader.readLong())

        if into == savegameObjects.SignalBuffer:
            arrayLen = reader.readInt()
            readCount = min(arrayLen,savegameObjects.SignalBuffer.ARRAY_SIZE)
            values = [
                self.deserialize(reader,gameObjects.GenericSignal)
                for _ in range(readCount)
            ]
            [
                self.deserialize(reader,gameObjects.GenericSignal)
                for _ in range(max(arrayLen-readCount,0))
            ]
            return savegameObjects.SignalBuffer(
                values,
                self.deserialize(reader,savegameObjects.SimulationTicks),
                self.deserialize(reader,savegameObjects.SignalTicks),
                reader.readBool()
            )

        if into == savegameObjects.SignalConductorInputState:
            self._autoDeserialize(reader,savegameObjects.SignalConductorInputState)

        if into == savegameObjects.FastBeltPathLaneState:

            reader.assertCheckpoint(Checkpoint.fastBeltPathStart)

            itemCapacity = reader.readShort()
            compressedItemsAfterFirst = reader.readShort()
            firstItemDistance:savegameObjects.SimulationSteps
            items:list[savegameObjects.ItemOnBelt] = []

            @reader.readBlob
            def _():
                nonlocal firstItemDistance

                count = reader.readInt()
                firstItemDistance = self.deserialize(reader,savegameObjects.SimulationSteps)

                if count <= 0:
                    return

                for _ in range(count):

                    item = self.deserialize(reader,gameObjects.GenericBeltItem)
                    nextItemDistance = self.deserialize(reader,savegameObjects.SimulationSteps)

                    if len(items) >= itemCapacity:
                        raise InvalidSerializedData(
                            "Too many items in "
                            + savegameObjects.FastBeltPathLaneState.__name__
                            + f" ({itemCapacity=})"
                        )
                    if item is None:
                        raise InvalidSerializedData(
                            "Item can't be None in "
                            + savegameObjects.FastBeltPathLaneState.__name__
                        )

                    items.append(savegameObjects.ItemOnBelt(item,nextItemDistance))

            reader.assertCheckpoint(Checkpoint.fastBeltPathEnd)

            return savegameObjects.FastBeltPathLaneState(
                itemCapacity,
                compressedItemsAfterFirst,
                firstItemDistance,
                items
            )

        if into == savegameObjects.BundleState:
            if containedType is None:
                needsContainedType(savegameObjects.BundleState)
            return savegameObjects.BundleState([
                self.deserialize(reader,containedType)
                for _ in range(savegameObjects.BundleState.ENTRIES_PER_BUNDLE)
            ])

        if into == savegameObjects.PathMergerSimulationState:
            return savegameObjects.PathMergerSimulationState(
                [
                    [
                        self.deserialize(reader,savegameObjects.BeltLaneState)
                        for _ in range(
                            savegameObjects.PathMergerSimulationState.NUM_ITEMS_PER_LANE
                        )
                    ]
                    for _ in range(reader.readInt1())
                ],
                reader.readShort(),
                reader.readInt1()
            )

        if into == savegameObjects.BeltPathLaneState:
            reader.assertCheckpoint(Checkpoint.beltPathStateStart)
            slots = []
            for _ in range(reader.readInt()):
                slots.append(self.deserialize(reader,savegameObjects.BeltSlotState))
            reader.assertCheckpoint(Checkpoint.beltPathStateEnd)
            return savegameObjects.BeltPathLaneState(slots)

        if into == savegameObjects.PathSplitterSimulationState:
            return savegameObjects.PathSplitterSimulationState(
                [
                    self.deserialize(reader,savegameObjects.BeltPathLaneState)
                    for _ in range(reader.readInt1())
                ],
                reader.readInt1()
            )

        if into == savegameObjects.SimulationBufferState:

            if containedType is None:
                needsContainedType(savegameObjects.SimulationBufferState)

            numItems = reader.readInt()
            if numItems < 0:
                raise InvalidSerializedData(
                    "Invalid number of items in queue for "
                    + savegameObjects.SimulationBufferState.__name__
                    + f" : {numItems}"
                )
            queue:list[savegameObjects.SimulationTimedBufferItem] = []

            @reader.readBlob
            def _():

                for _ in range(numItems):
                    item = self.deserialize(reader,containedType)
                    selfExcess = self.deserialize(reader,savegameObjects.SimulationTicks)
                    if item is None:
                        raise InvalidSerializedData(
                            f"Item can't be None in {savegameObjects.SimulationBufferState.__name__}"
                        )
                    queue.append(savegameObjects.SimulationTimedBufferItem(item,selfExcess))

                # pretty sure this isn't supposed to be here
                # but kept to be accurate to the game
                queue.reverse()

            return savegameObjects.SimulationBufferState(queue)

        if into == savegameObjects.BeltItemSimulationBufferState:
            return savegameObjects.BeltItemSimulationBufferState(
                self.deserialize(
                    reader,
                    savegameObjects.SimulationBufferState[gameObjects.GenericBeltItem]
                ).queue
            )

        if into == savegameObjects.FluidPackageData:
            return self._autoDeserialize(reader,savegameObjects.FluidPackageData)

        if into == savegameObjects.FluidPackageLaunchData:
            return self._autoDeserialize(reader,savegameObjects.FluidPackageLaunchData)

        if into == savegameObjects.FluidPackageLaunchState:
            return self._autoDeserialize(reader,savegameObjects.FluidPackageLaunchState)

        if into == savegameObjects.TrainCargoFillingContainerState:
            if containedType is None:
                needsContainedType(savegameObjects.TrainCargoFillingContainerState)
            return savegameObjects.TrainCargoFillingContainerState(
                self.deserialize(reader,gameObjects.CargoPackage[containedType])
            )

        if into == savegameObjects.TrainCargoExchangerState:

            if containedType is None:
                needsContainedType(savegameObjects.TrainCargoExchangerState)

            numSlots = reader.readInt1()
            if numSlots != savegameObjects.TrainCargoExchangerState.NUM_LOADING_PATH_SLOTS:
                raise InvalidSerializedData(
                    "Unsupported number of loading path slots for "
                    + savegameObjects.TrainCargoExchangerState.__name__
                    + f" : {numSlots}"
                )

            loadingPaths:savegameObjects.BundleState[savegameObjects.BeltPathLaneState]

            @reader.readBlob
            def _():
                nonlocal loadingPaths
                # ingame the deserialization code for the BundleState is duplicated here
                loadingPaths = self.deserialize(
                    reader,
                    savegameObjects.BundleState[savegameObjects.BeltPathLaneState]
                )

            fillingContainer = [
                self.deserialize(
                    reader,
                    savegameObjects.TrainCargoFillingContainerState[containedType]
                )
                for _ in range(savegameObjects.TrainCargoExchangerState.NUM_LAYERS)
            ]

            cargoOnTrack = [
                self.deserialize(reader,savegameObjects.BeltPathLaneState)
                for _ in range(savegameObjects.TrainCargoExchangerState.NUM_LAYERS)
            ]

            if not reader.readBool():
                raise InvalidSerializedData(
                    "Containers on bridge not serialized unsupported for "
                    + savegameObjects.TrainCargoExchangerState.__name__
                )

            cargoOnBridge = [
                self.deserialize(reader,savegameObjects.BeltPathLaneState)
                for _ in range(savegameObjects.TrainCargoExchangerState.NUM_LAYERS)
            ]

            return savegameObjects.TrainCargoExchangerState(
                loadingPaths,
                fillingContainer,
                cargoOnTrack,
                cargoOnBridge
            )

        if into == savegameObjects.TrainCargoTransferState:
            # contained type ingored because unused
            return savegameObjects.TrainCargoTransferState(
                *[
                    [
                        self.deserialize(reader,savegameObjects.BeltPathLaneState)
                        for _ in range(savegameObjects.TrainCargoTransferState.NUM_LAYERS)
                    ]
                    for _ in range(3)
                ]
            )

        if into == savegameObjects.SignalChannelRingBufferState:

            arrayLen = reader.readInt()
            print(f"This should be 24 : {arrayLen}") # remove when checked
            readCount = min(arrayLen,savegameObjects.SignalChannelRingBuffer.SIGNAL_ARRAY_SIZE)

            if readCount < arrayLen:
                raise InvalidSerializedData(
                    "Array length bigger than "
                    + f"{savegameObjects.SignalChannelRingBuffer.SIGNAL_ARRAY_SIZE}"
                    + " unsupported for "
                    + savegameObjects.SignalChannelRingBufferState.__name__
                    + f" : {arrayLen}"
                )

            array = [
                savegameObjects.TimedSignal(
                    gameObjects.NullSignal(),
                    savegameObjects.SignalTicks(savegameObjects.SignalTicks.MIN_VALUE)
                )
                for _ in range(savegameObjects.SignalChannelRingBuffer.SIGNAL_ARRAY_SIZE)
            ]

            for i in range(readCount):
                array[i] = self._autoDeserialize(reader,savegameObjects.TimedSignal)

            return savegameObjects.SignalChannelRingBufferState(array)

#endregion
#region simulation states with polymorphic

        if into == savegameObjects.GenericSimulationState:
            return self.simulationStateSerializer.deserialize(reader)

        for cls in [
            savegameObjects.BeltPortReceiverDisabledState,
            savegameObjects.BeltPortSenderBlockedState,
            savegameObjects.BeltPortSenderDiscardState,
            savegameObjects.BeltPortSenderToHubSimulationState,
            savegameObjects.BeltPortSenderToSpacePathSimulationState,
            savegameObjects.BeltReaderSimulationState,
            savegameObjects.ControlledSignalReceiverState,
            savegameObjects.ControlledSignalTransmitterState,
            savegameObjects.ConveyorSimulationState,
            savegameObjects.CrystalGeneratorSimulationState,
            savegameObjects.DisplaySimulationState,
            savegameObjects.ExtractorSimulationState,
            savegameObjects.FluidPortReceiverDisabledState,
            savegameObjects.FluidPortSenderBlockedState,
            savegameObjects.FluidPortSenderDiscardState,
            savegameObjects.FluidPortSenderToSpacePipeSimulationState,
            savegameObjects.FluidPortTransferState,
            savegameObjects.FluidStorageSimulationState,
            savegameObjects.FullCutterSimulationState,
            savegameObjects.HalfCutterSimulationState,
            savegameObjects.HalvesSwapperSimulationState,
            savegameObjects.ItemProducerSimulationState,
            savegameObjects.Lift1LayerSimulationState,
            savegameObjects.Lift2LayerSimulationState,
            savegameObjects.LogicGate2In1OutSimulationState,
            savegameObjects.LogicGateCompareSimulationState,
            savegameObjects.LogicGateIfSimulationState,
            savegameObjects.LogicGateNotSimulationState,
            savegameObjects.PainterSimulationState,
            savegameObjects.PinPusherSimulationState,
            savegameObjects.PipeGateSimulationState,
            savegameObjects.RotatorSimulationState,
            savegameObjects.SignalPortSenderBlockedState,
            savegameObjects.SignalPortTransferState,
            savegameObjects.SpaceConveyorSimulationState,
            savegameObjects.SpacePathToBeltPortReceiverSimulationState,
            savegameObjects.SpacePipeToFluidPortReceiverSimulationState,
            savegameObjects.SpaceSplitterSimulationState,
            savegameObjects.StackerSimulationState,
            savegameObjects.Virtual1InSimulationState,
            savegameObjects.Virtual2InSimulationState
        ]:
            if into == cls:
                return self._autoDeserialize(reader,cls)

        if into == savegameObjects.BeltFilterSimulationState:
            base = self.deserialize(reader,savegameObjects.SplitterSimulationState)
            return savegameObjects.BeltFilterSimulationState(
                base.inputLaneState,
                base.outputLaneStates,
                self.deserialize(reader,savegameObjects.SignalConductorInputState)
            )

        if into == savegameObjects.BeltPortSenderTransferSimulationState:
            numItems = reader.readInt1()
            if (numItems != savegameObjects
                .BeltPortSenderTransferSimulationState
                .NUM_JUMP_LANE_ITEMS
            ):
                raise InvalidSerializedData(
                    "Invalid number of items in "
                    + savegameObjects.BeltPortSenderTransferSimulationState.__name__
                    + f" : {numItems}"
                )
            return savegameObjects.BeltPortSenderTransferSimulationState(
                self.deserialize(reader,savegameObjects.FastBeltPathLaneState)
            )

        if into == savegameObjects.ConverterHubProducerSimulationState:
            raise ValueError("unused ?")
            # if it is then also remove serialization
            return savegameObjects.ConverterHubProducerSimulationState(
                self.deserialize(reader,savegameObjects.BeltLaneState),
                reader.readInt()
            )

        if into == savegameObjects.ConverterSimulationState:
            raise InvalidSerializedData(
                f"Can't deserialize {savegameObjects.ConverterSimulationState.__name__} (maybe)"
            )

        if into == savegameObjects.MergerSimulationState:
            return savegameObjects.MergerSimulationState(
                [
                    self.deserialize(reader,savegameObjects.BeltLaneState)
                    for _ in range(reader.readInt1())
                ],
                self.deserialize(reader,savegameObjects.BeltLaneState),
                reader.readShort(),
                reader.readInt1()
            )

        if into == savegameObjects.MixerSimulationState:
            i0 = self.deserialize(reader,savegameObjects.FluidContainerState)
            i1 = self.deserialize(reader,savegameObjects.FluidContainerState)
            c0 = self.deserialize(reader,savegameObjects.FluidContainerState)
            c1 = self.deserialize(reader,savegameObjects.FluidContainerState)
            out = self.deserialize(reader,savegameObjects.FluidContainerState)
            mixState = reader.readInt1()
            if mixState not in savegameObjects.MixerSimulationMixingState:
                raise InvalidSerializedData(
                    "Invalid value for "
                    + savegameObjects.MixerSimulationMixingState.__name__
                    + f" : {mixState}"
                )
            return savegameObjects.MixerSimulationState(
                i0,i1,c0,c1,out,
                savegameObjects.MixerSimulationMixingState(mixState),
                self.deserialize(reader,savegameObjects.SimulationTicks),
                self.deserialize(reader,gameObjects.GenericFluid)
            )

        if into == savegameObjects.PrioritySplitterSimulationState:
            base = self.deserialize(reader,savegameObjects.SplitterSimulationState)
            return savegameObjects.PrioritySplitterSimulationState(
                base.inputLaneState,
                base.outputLaneStates,
                reader.readInt1()
            )

        if into == savegameObjects.SpaceConverterHubSimulationState:
            return savegameObjects.SpaceConverterHubSimulationState([
                self.deserialize(reader,savegameObjects.BundleState[savegameObjects.FastBeltPathLaneState])
                for _ in range(reader.readInt1())
            ])

        if into == savegameObjects.SpaceConverterSimulationState:
            numInputLanes = reader.readInt1()
            numOutputLanes = reader.readInt1()
            return savegameObjects.SpaceConverterSimulationState(
                [
                    self.deserialize(reader,savegameObjects.BundleState[savegameObjects.FastBeltPathLaneState])
                    for _ in range(numInputLanes)
                ],
                self.deserialize(reader,savegameObjects.BundleState[savegameObjects.ConverterSimulationState]),
                [
                    self.deserialize(reader,savegameObjects.BundleState[savegameObjects.FastBeltPathLaneState])
                    for _ in range(numOutputLanes)
                ],
                reader.readInt()
            )

        if into == savegameObjects.SpaceMergerSimulationState:
            return savegameObjects.SpaceMergerSimulationState(
                self.deserialize(reader,savegameObjects.BundleState[savegameObjects.PathMergerSimulationState]),
                [
                    self.deserialize(reader,savegameObjects.BundleState[savegameObjects.FastBeltPathLaneState])
                    for _ in range(reader.readInt1())
                ]
            )

        if into == savegameObjects.SpaceResearchStationSimulationState:
            raise InvalidSerializedData(
                "Can't deserialize "
                + savegameObjects.SpaceResearchStationSimulationState.__name__
                + " (maybe)"
            )

        if into == savegameObjects.SpaceTrashSimulationState:
            raise InvalidSerializedData(
                f"Can't deserialize {savegameObjects.SpaceTrashSimulationState.__name__} (maybe)"
            )

        if into == savegameObjects.SplitterSimulationState:
            numOutputs = reader.readInt1()
            return savegameObjects.SplitterSimulationState(
                self.deserialize(reader,savegameObjects.BeltLaneState),
                [
                    self.deserialize(reader,savegameObjects.BeltLaneState)
                    for _ in range(numOutputs)
                ]
            )

        if into == savegameObjects.TrashSimulationState:
            return savegameObjects.TrashSimulationState([
                self.deserialize(reader,savegameObjects.BeltLaneState)
                for _ in range(savegameObjects.TrashSimulationState.NUM_LANES)
            ])

        raise ValueError(f"Unknown type for deserialization : {into}")

#endregion
#endregion



#region serialization

    def _autoSerialize(self,writer:BinaryStreamWriter,obj:typing.Any) -> None:
        for attrName,attrType in inspect.get_annotations(type(obj)).items():
            kwargs = {}
            if typing.get_origin(attrType) == types.UnionType:
                unionArgs = typing.get_args(attrType)
                if (
                    (len(unionArgs) != 2)
                    or (unionArgs[1] != types.NoneType)
                ):
                    raise ValueError(
                        f"Invalid union type for auto serialization : {attrType}"
                    )
                kwargs["objTypeOverride"] = unionArgs[0]
            elif attrType.__name__.startswith("Generic"):
                kwargs["objTypeOverride"] = attrType
            attrValue = getattr(obj,attrName)
            if attrType == bool:
                writer.writeBool(attrValue)
            else:
                self.serialize(writer,attrValue,**kwargs)

    def serialize(
        self,
        writer:BinaryStreamWriter,
        obj:typing.Any,
        objTypeOverride:type|None=None,
        containedTypeOverride:type|None=None
    ) -> None:
        """Specify a type override if `obj` can be `None`
        or if it's a generic with specific serialization code !"""

        if objTypeOverride is None:
            if obj is None:
                raise ValueError("Specify a type override when 'obj' can be None")
            objType = type(obj)
        else:
            objType = objTypeOverride

        typeOrigin = typing.get_origin(objType)
        if typeOrigin is None:
            containedType = None
        else:
            containedType = typing.get_args(objType)[0]
            objType = typeOrigin

        if containedTypeOverride is not None:
            containedType = containedTypeOverride

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

#region general game objects

        @f
        def _(obj:savegameObjects.GlobalChunkCoordinate):
            writer.writeInt(obj.x)
            writer.writeInt(obj.y)
            writer.writeShort(obj.z)

        @f
        def _(obj:savegameObjects.IslandTileCoordinate):
            writer.writeShort(obj.x)
            writer.writeShort(obj.y)
            writer.writeInt1(obj.z)

        @f
        def _(obj:savegameObjects.GlobalTileCoordinate):
            writer.writeInt(obj.x)
            writer.writeInt(obj.y)
            writer.writeShort(obj.z)

        @f
        def _(obj:utils.Rotation):
            writer.writeInt1(obj.value)

#endregion
#region objects for config

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
            if (
                isinstance(obj,gameObjects.PackageOnTrack)
                and isinstance(obj.container,gameObjects.CargoPackage)
            ):
                if obj.container._itemType == gameObjects.GenericFluid: # FluidId ingame
                    writer.writeInt1(3)
                    self.serialize(writer,obj.container)
                    return
                if obj.container._itemType == gameObjects.ShapeItem: # ShapeId ingame
                    writer.writeInt1(4)
                    self.serialize(writer,obj.container)
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
        def _(obj:gameObjects.CargoPackage):
            # contained type is ignored
            writer.writeShort(obj.amount)
            if obj.amount != 0:
                self.serialize(writer,obj.item,obj._itemType)

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

#endregion
#region misc

        @f
        def _(obj:islands.Island):
            writer.writeString(obj.id)

        @f
        def _(obj:buildings.BuildingInternalVariant):
            writer.writeString(obj.id)

        @f
        def _(obj:savegameObjects.LayeredWagonCargo):
            writer.writeInt1(len(obj.containers))
            for c in obj.containers:
                self.serialize(
                    writer,
                    c,
                    containedType # intentionally None if no containedType specified
                )

        @f
        def _(obj:savegameObjects.CargoContainer):
            # contained type is ignored because CargoPackage ingores it too
            writer.writeShort(len(obj.packages))
            writer.writeShort(obj.maxPackages)
            for p in obj.packages:
                self.serialize(writer,p)

        # to use when ShapeDefinition is used ingame
        @f
        def _(obj:gameObjects.Shape):
            writer.writeString(obj.toShapeCode())

#endregion
#region simulation states

        @f
        def _(obj:savegameObjects.SimulationSteps):
            writer.writeLong(obj.steps)

        @f
        def _(obj:savegameObjects.BeltSlotState):
            if obj.item is None:
                writer.writeBool(False)
            else:
                writer.writeBool(True)
                self.serialize(writer,obj.item,gameObjects.GenericBeltItem)
                self.serialize(writer,obj.progress)

        @f
        def _(obj:savegameObjects.BeltLaneState):
            if obj.item is None:
                writer.writeBool(False)
            else:
                writer.writeBool(True)
                self.serialize(writer,obj.item,gameObjects.GenericBeltItem)
                self.serialize(writer,obj.progress)

        @f
        def _(obj:savegameObjects.FluidContainerState):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:savegameObjects.SimulationTicks):
            writer.writeLong(obj.value)

        @f
        def _(obj:savegameObjects.ShapeCollapseResult):
            if (obj is None) or (len(obj.entries) == 0):
                writer.writeInt1(0)
                return
            # ingame this is '>=', fixed here to not generate errors with valid data
            if len(obj.entries) > 255:
                raise ValueError(
                    f"Too many entries in {savegameObjects.ShapeCollapseResult.__name__}"
                )
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
        def _(obj:savegameObjects.SignalTicks):
            writer.writeLong(obj.value)

        @f
        def _(obj:savegameObjects.SignalBuffer):
            writer.writeInt(savegameObjects.SignalBuffer.ARRAY_SIZE)
            for i in range(savegameObjects.SignalBuffer.ARRAY_SIZE):
                self.serialize(writer,obj.values[i],gameObjects.GenericSignal)
            self.serialize(writer,obj.lastStartTicks)
            self.serialize(writer,obj.lastSignalTick)
            writer.writeBool(obj.wasPushedThisStartTick)

        @f
        def _(obj:savegameObjects.SignalConductorInputState):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:savegameObjects.FastBeltPathLaneState):
            writer.writeCheckpoint(Checkpoint.fastBeltPathStart)
            writer.writeShort(obj.itemCapacity)
            writer.writeShort(obj.compressedItemsAfterFirst)
            @writer.writeBlob
            def _():
                writer.writeInt(len(obj.items))
                self.serialize(writer,obj.firstItemDistance)
                for item in obj.items:
                    self.serialize(writer,item.item,gameObjects.GenericBeltItem)
                    self.serialize(writer,item.nextItemDistance)
            writer.writeCheckpoint(Checkpoint.fastBeltPathEnd)

        @f
        def _(obj:savegameObjects.BundleState):
            if containedType is None:
                needsContainedType(savegameObjects.BundleState)
            if len(obj.entries) != savegameObjects.BundleState.ENTRIES_PER_BUNDLE:
                raise ValueError(
                    "Invalid number of entries for "
                    + savegameObjects.BundleState.__name__
                    + f" ({len(obj.entries)})"
                )
            for e in obj.entries:
                self.serialize(writer,e,containedType)

        @f
        def _(obj:savegameObjects.PathMergerSimulationState):
            writer.writeInt1(len(obj.inputSegmentSlotStates))
            for l in obj.inputSegmentSlotStates:
                for s in l:
                    self.serialize(writer,s)
            writer.writeShort(obj.priorityLaneIndex)
            writer.writeInt1(obj.preferredInputIndex)

        @f
        def _(obj:savegameObjects.BeltPathLaneState):
            writer.writeCheckpoint(Checkpoint.beltPathStateStart)
            writer.writeInt(len(obj.slots))
            for s in obj.slots:
                self.serialize(writer,s)
            writer.writeCheckpoint(Checkpoint.beltPathStateEnd)

        @f
        def _(obj:savegameObjects.PathSplitterSimulationState):
            writer.writeInt1(len(obj.outputLaneStates))
            for o in obj.outputLaneStates:
                self.serialize(writer,o)
            writer.writeInt1(obj.nextPreferredIndex)

        @f
        def _(obj:savegameObjects.SimulationBufferState):
            if containedType is None:
                needsContainedType(savegameObjects.SimulationBufferState)
            writer.writeInt(len(obj.queue))
            @writer.writeBlob
            def _():
                for item in obj.queue:
                    self.serialize(writer,item.item,containedType)
                    self.serialize(writer,item.selfExcess)

        @f
        def _(obj:savegameObjects.BeltItemSimulationBufferState):
            self.serialize(
                writer,
                obj,
                savegameObjects.SimulationBufferState[gameObjects.GenericBeltItem]
            )

        @f
        def _(obj:savegameObjects.FluidPackageData):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:savegameObjects.FluidPackageLaunchData):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:savegameObjects.FluidPackageLaunchState):
            self._autoSerialize(writer,obj)

        @f
        def _(obj:savegameObjects.TrainCargoFillingContainerState):
            # contained type is ignored because CargoPackage ingores it too
            self.serialize(writer,obj.package)

        @f
        def _(obj:savegameObjects.TrainCargoExchangerState):
            # contained type is ignored because TrainCargoFillingContainerState ingores it too

            writer.writeInt1(savegameObjects.TrainCargoExchangerState.NUM_LOADING_PATH_SLOTS)
            @writer.writeBlob
            def _():
                # ingame the serialization code for the BundleState is duplicated here
                self.serialize(
                    writer,
                    obj.loadingPathsStates,
                    containedTypeOverride=savegameObjects.BeltPathLaneState
                )

            for states,text in [
                (obj.trainCargoFillingContainerState,"filling container"),
                (obj.cargoContainerTracksStates,"cargo on track"),
                (obj.cargoOnBridge,"cargo on bridge")
            ]:
                n = len(states)
                if n != savegameObjects.TrainCargoExchangerState.NUM_LAYERS:
                    raise ValueError(
                        f"Invalid number of {text} states for "
                        + savegameObjects.TrainCargoExchangerState.__name__
                        + f" : {n}"
                    )

            for fillingContainer in obj.trainCargoFillingContainerState:
                self.serialize(writer,fillingContainer)

            for cargoOnTrack in obj.cargoContainerTracksStates:
                self.serialize(writer,cargoOnTrack)

            writer.writeBool(True)
            for cargoOnBridge in obj.cargoOnBridge:
                self.serialize(writer,cargoOnBridge)

        @f
        def _(obj:savegameObjects.TrainCargoTransferState):
            # contained type ingored because unused
            for states,text in [
                (obj.cargoContainerTracksStates,"cargo on track"),
                (obj.cargoOnInputBridge,"cargo on input bridge"),
                (obj.cargoOnOutputBridge,"cargo on output bridge")
            ]:
                n = len(states)
                if n != savegameObjects.TrainCargoTransferState.NUM_LAYERS:
                    raise ValueError(
                        f"Invalid number of {text} states for "
                        + savegameObjects.TrainCargoTransferState.__name__
                        + f" : {n}"
                    )
                for cargo in states:
                    self.serialize(writer,cargo)

        @f
        def _(obj:savegameObjects.SignalChannelRingBufferState):

            arrayLen = savegameObjects.SignalChannelRingBuffer.SIGNAL_ARRAY_SIZE

            if len(obj.timedSignals) != arrayLen:
                raise ValueError(
                    "Invalid number of elements in "
                    + savegameObjects.SignalChannelRingBufferState.__name__
                    + f" : {len(obj.timedSignals)}"
                )

            writer.writeInt(arrayLen)
            for timedSignal in obj.timedSignals:
                self._autoSerialize(writer,timedSignal)

#endregion
#region simulation states with polymorphic

        @f
        def _(obj:savegameObjects.GenericSimulationState):
            self.simulationStateSerializer.serialize(writer,obj)

        for cls in [
            savegameObjects.BeltPortReceiverDisabledState,
            savegameObjects.BeltPortSenderBlockedState,
            savegameObjects.BeltPortSenderDiscardState,
            savegameObjects.BeltPortSenderToHubSimulationState,
            savegameObjects.BeltPortSenderToSpacePathSimulationState,
            savegameObjects.BeltReaderSimulationState,
            savegameObjects.ControlledSignalReceiverState,
            savegameObjects.ControlledSignalTransmitterState,
            savegameObjects.ConveyorSimulationState,
            savegameObjects.CrystalGeneratorSimulationState,
            savegameObjects.DisplaySimulationState,
            savegameObjects.ExtractorSimulationState,
            savegameObjects.FluidPortReceiverDisabledState,
            savegameObjects.FluidPortSenderBlockedState,
            savegameObjects.FluidPortSenderDiscardState,
            savegameObjects.FluidPortSenderToSpacePipeSimulationState,
            savegameObjects.FluidPortTransferState,
            savegameObjects.FluidStorageSimulationState,
            savegameObjects.FullCutterSimulationState,
            savegameObjects.HalfCutterSimulationState,
            savegameObjects.HalvesSwapperSimulationState,
            savegameObjects.ItemProducerSimulationState,
            savegameObjects.Lift1LayerSimulationState,
            savegameObjects.Lift2LayerSimulationState,
            savegameObjects.LogicGate2In1OutSimulationState,
            savegameObjects.LogicGateCompareSimulationState,
            savegameObjects.LogicGateIfSimulationState,
            savegameObjects.LogicGateNotSimulationState,
            savegameObjects.PainterSimulationState,
            savegameObjects.PinPusherSimulationState,
            savegameObjects.PipeGateSimulationState,
            savegameObjects.RotatorSimulationState,
            savegameObjects.SignalPortSenderBlockedState,
            savegameObjects.SignalPortTransferState,
            savegameObjects.SpaceConveyorSimulationState,
            savegameObjects.SpacePathToBeltPortReceiverSimulationState,
            savegameObjects.SpacePipeToFluidPortReceiverSimulationState,
            savegameObjects.SpaceSplitterSimulationState,
            savegameObjects.StackerSimulationState,
            savegameObjects.Virtual1InSimulationState,
            savegameObjects.Virtual2InSimulationState
        ]:
            f(lambda obj: self._autoSerialize(writer,obj),cls)

        @f
        def _(obj:savegameObjects.BeltFilterSimulationState):
            self.serialize(writer,savegameObjects.SplitterSimulationState(
                obj.inputLaneState,
                obj.outputLaneStates
            ))
            self.serialize(writer,obj.inputConductorState)

        @f
        def _(obj:savegameObjects.BeltPortSenderTransferSimulationState):
            writer.writeInt1(savegameObjects
                .BeltPortSenderTransferSimulationState
                .NUM_JUMP_LANE_ITEMS
            )
            self.serialize(writer,obj.jumpLaneState)

        @f
        def _(obj:savegameObjects.ConverterHubProducerSimulationState):
            self.serialize(writer,obj.outputLaneState)
            writer.writeInt(obj.numProducedItems)

        @f
        def _(obj:savegameObjects.ConverterSimulationState):
            raise ValueError("unused ?")
            writer.writeInt1(len(obj.processingReceiverStates))
            writer.writeInt1(len(obj.outputLaneStates))
            for lane in (
                obj.inputLaneStates
                + obj.processingReceiverStates
                + obj.processingLaneStates
                + obj.outputLaneStates
            ):
                self.serialize(writer,lane)

        @f
        def _(obj:savegameObjects.MergerSimulationState):
            writer.writeInt1(len(obj.inputLaneStates))
            for lane in obj.inputLaneStates:
                self.serialize(writer,lane)
            self.serialize(writer,obj.outputLaneState)
            writer.writeShort(obj.currentInputIndex)
            writer.writeInt1(obj.preferredInputIndex)

        @f
        def _(obj:savegameObjects.MixerSimulationState):
            self.serialize(writer,obj.input0ContainerState)
            self.serialize(writer,obj.input1ContainerState)
            self.serialize(writer,obj.chamber0ContainerState)
            self.serialize(writer,obj.chamber1ContainerState)
            self.serialize(writer,obj.outputContainerState)
            writer.writeInt1(obj.mixingState.value)
            self.serialize(writer,obj.mixingProgress)
            self.serialize(writer,obj.mixingResult,gameObjects.GenericFluid)

        @f
        def _(obj:savegameObjects.PrioritySplitterSimulationState):
            self.serialize(writer,savegameObjects.SplitterSimulationState(
                obj.inputLaneState,
                obj.outputLaneStates
            ))
            writer.writeInt1(obj.prioritizedIndex)

        @f
        def _(obj:savegameObjects.SpaceConverterHubSimulationState):
            writer.writeInt1(len(obj.outputLaneBundleStates))
            for o in obj.outputLaneBundleStates:
                self.serialize(writer,o,containedTypeOverride=savegameObjects.FastBeltPathLaneState)

        @f
        def _(obj:savegameObjects.SpaceConverterSimulationState):
            writer.writeInt1(len(obj.inputLaneBundleStates))
            writer.writeInt1(len(obj.outputLaneBundleStates))
            for i in obj.inputLaneBundleStates:
                self.serialize(writer,i,containedTypeOverride=savegameObjects.FastBeltPathLaneState)
            self.serialize(
                writer,
                obj.simulationBundleState,
                containedTypeOverride=savegameObjects.ConverterSimulationState
            )
            for o in obj.outputLaneBundleStates:
                self.serialize(writer,o,containedTypeOverride=savegameObjects.FastBeltPathLaneState)
            writer.writeInt(obj.conversionCount)

        @f
        def _(obj:savegameObjects.SpaceMergerSimulationState):
            self.serialize(
                writer,
                obj.mergerSimulationBundleState,
                containedTypeOverride=savegameObjects.PathMergerSimulationState
            )
            writer.writeInt1(len(obj.inputLaneBundleStates))
            for i in obj.inputLaneBundleStates:
                self.serialize(writer,i,containedTypeOverride=savegameObjects.FastBeltPathLaneState)

        @f
        def _(obj:savegameObjects.SpaceResearchStationSimulationState):
            raise ValueError("unused ?")
            self._autoSerialize(writer,obj)

        @f
        def _(obj:savegameObjects.SpaceTrashSimulationState):
            raise ValueError("unused ?")
            self._autoSerialize(writer,obj)

        @f
        def _(obj:savegameObjects.SplitterSimulationState):
            writer.writeInt1(len(obj.outputLaneStates))
            self.serialize(writer,obj.inputLaneState)
            for lane in obj.outputLaneStates:
                self.serialize(writer,lane)

        @f
        def _(obj:savegameObjects.TrashSimulationState):
            if len(obj.laneStates) != savegameObjects.TrashSimulationState.NUM_LANES:
                raise ValueError(
                    "Invalid number of lane states for "
                    + savegameObjects.TrashSimulationState.__name__
                    + f" ({len(obj.laneStates)})"
                )
            for lane in obj.laneStates:
                self.serialize(writer,lane)

        if typeMatch is None:
            raise ValueError(f"Unknown type for serialization : {objType}")

#endregion
#endregion



#region configs

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

#endregion



#endregion



#region json data

type jsonFormat = (
    None
    | type[bool]
    | type[int]
    | type[float]
    | type[str]
    | list[jsonFormat]
    | dict[str,jsonFormat|JSONOptionalValueFormat]
    | JSONNoFormatCheck
)
type jsonObject = None|bool|int|float|str|list[jsonObject]|dict[str,jsonObject]

@dataclass
class JSONOptionalValueFormat:
    valueFormat:jsonFormat
    _default:jsonObject|Callable[[],jsonObject]

    def getDefault(self) -> jsonObject:
        if callable(self._default):
            return self._default()
        return self._default

class JSONNoFormatCheck:
    """Must be instantiated to work"""

class JSONFormatError(Exception): ...

def getJSONObjWithFormat(rawObj:jsonObject,format:jsonFormat,floatCanBeInt:bool=True) -> tuple[jsonObject,list[str]]:

    warningMsgs = []
    defaultObj = object()

    def inner(obj:jsonObject,format:jsonFormat) -> jsonObject:

        objType = type(obj)

        if isinstance(format,dict):

            if objType != dict:
                raise JSONFormatError(f"Incorrect object type, expected 'dict' got '{objType.__name__}'")

            newObj = {}

            for formatKey,formatValue in format.items():

                objValue = obj.get(formatKey,defaultObj)

                if isinstance(formatValue,JSONOptionalValueFormat):
                    if objValue is defaultObj:
                        # decode default value to allow for defaults in defaults
                        objValue = formatValue.getDefault()
                    newObj[formatKey] = inner(objValue,formatValue.valueFormat)
                else:
                    if objValue is defaultObj:
                        raise JSONFormatError(f"Missing dict key : {formatKey}")
                    newObj[formatKey] = inner(objValue,formatValue)

            for key in obj.keys():
                if format.get(key) is None:
                    warningMsgs.append(f"Skipping key : {key}")

            return newObj

        if isinstance(format,list):

            if objType != list:
                raise JSONFormatError(f"Incorrect object type, expected 'list' got '{objType.__name__}'")

            newObj = []
            elemFormat = format[0]

            for objElem in obj:

                newObj.append(inner(objElem,elemFormat))

            return newObj

        if isinstance(format,JSONNoFormatCheck):
            return obj

        if floatCanBeInt and (format == float) and (objType == int):
            return float(obj)

        if objType != format:
            raise JSONFormatError(f"Incorrect object type, expected '{format.__name__}' got '{objType.__name__}'")

        return obj

    return inner(rawObj,format), warningMsgs

def encodeJSONObjWithFormat(obj:jsonObject,format:jsonFormat,includeDefaults:bool=False) -> jsonObject:

    defaultObj = object()
    
    def inner(obj:jsonObject,format:jsonFormat) -> jsonObject:

        if isinstance(format,dict):

            newObj = {}

            for formatKey,formatValue in format.items():

                objValue = obj.get(formatKey,defaultObj)

                if isinstance(formatValue,JSONOptionalValueFormat):
                    if objValue is defaultObj:
                        if includeDefaults:
                            objValue = formatValue.getDefault()
                        else:
                            continue
                    elif objValue == formatValue.getDefault():
                        if not includeDefaults:
                            continue
                    newObj[formatKey] = inner(objValue,formatValue.valueFormat)
                else:
                    newObj[formatKey] = inner(objValue,formatValue)

            return newObj

        if isinstance(format,list):

            newObj = []

            for objElem in obj:

                newObj.append(inner(objElem,format[0]))

            return newObj

        return obj

    return inner(obj,format)

_TSpecialCase = typing.TypeVar("_TSpecialCase")
_TSpecialCaseInnerT = typing.TypeVar("_TSpecialCaseInnerT")
type keyMappingsType = dict[type,dict[str,str|list[str]]]
type jsonObjToCustomObjInnerFunc = Callable[[
    jsonObject,
    type[_TSpecialCaseInnerT]|types.GenericAlias|types.UnionType
],_TSpecialCaseInnerT]

# different from str.capitalize
def _capitalizeAttrName(name:str) -> str:
    return name[0].upper() + name[1:]

def jsonObjToCustomObj[T](
    rawObj:jsonObject,
    customObjClass:type[T],
    keyMappings:keyMappingsType,
    specialCases:Callable[[
        jsonObject,
        type[_TSpecialCase],
        object,
        jsonObjToCustomObjInnerFunc
    ],_TSpecialCase|object]
) -> T:

    notASpecialCase = object()

    def inner[T](rawObj:jsonObject,toClass:type[T]|types.GenericAlias|types.UnionType) -> T:

        specialCase = specialCases(rawObj,toClass,notASpecialCase,inner)
        if specialCase is not notASpecialCase:
            return specialCase

        if keyMappings.get(toClass) is None:

            typeOrigin = typing.get_origin(toClass)
            typeArgs = typing.get_args(toClass)

            if typeOrigin == list:
                newObj = []
                for elem in rawObj:
                    newObj.append(inner(elem,typeArgs[0]))
                return newObj

            if typeOrigin == types.UnionType:
                assert typeArgs[1] == types.NoneType
                if rawObj is None:
                    return None
                return inner(rawObj,typeArgs[0])

            assert isinstance(rawObj,(str,int,float,bool,types.NoneType,list,dict)), type(rawObj)
            return rawObj

        kwargs = {}
        for attrName,attrType in inspect.get_annotations(toClass).items():

            rawObjKey = keyMappings[toClass].get(attrName)

            if rawObjKey is None:
                rawObjKey = _capitalizeAttrName(attrName)

            if rawObjKey == []:
                newElem = inner(rawObj,attrType)
            else:
                if isinstance(rawObjKey,str):
                    rawObjKey = [rawObjKey]
                rawElem = rawObj
                for k in rawObjKey:
                    rawElem = rawElem[k]
                newElem = inner(rawElem,attrType)

            kwargs[attrName] = newElem

        return toClass(**kwargs)

    return inner(rawObj,customObjClass)

@dataclass
class JSONMultiKeyValue:
    value:dict[str,jsonObject]

class HasJSONEncodeOverride:
    def _jsonEncodeOverride(self) -> tuple[list[str],dict[str,jsonObject]]:
        raise NotImplementedError

type customObjToJSONObjInnerFunc = Callable[[
    typing.Any,
    type|types.GenericAlias|types.UnionType
],jsonObject|JSONMultiKeyValue]

def customObjToJSONObj(
    customObj:typing.Any,
    keyMappings:keyMappingsType,
    specialCases:Callable[[
        typing.Any,
        object,
        customObjToJSONObjInnerFunc
    ],jsonObject|JSONMultiKeyValue|object]
) -> jsonObject:

    notASpecialCase = object()

    def inner(
        obj:typing.Any,
        objClass:type|types.GenericAlias|types.UnionType
    ) -> jsonObject|JSONMultiKeyValue:

        if isinstance(objClass,type):
            assert type(obj) == objClass, f"{type(obj)=} != {objClass=}"

        specialCase = specialCases(obj,notASpecialCase,inner)
        if specialCase is not notASpecialCase:
            return specialCase

        if keyMappings.get(objClass) is None:

            typeOrigin = typing.get_origin(objClass)
            typeArgs = typing.get_args(objClass)

            if typeOrigin == list:
                newObj = []
                for elem in obj:
                    newElem = inner(elem,typeArgs[0])
                    assert not isinstance(newElem,JSONMultiKeyValue)
                    newObj.append(newElem)
                return newObj

            if typeOrigin == types.UnionType:
                assert typeArgs[1] == types.NoneType
                if obj is None:
                    return None
                return inner(obj,typeArgs[0])

            assert isinstance(obj,(str,int,float,bool,types.NoneType,list,dict)), type(obj)
            return obj

        if isinstance(obj,HasJSONEncodeOverride):
            skipAttrs, newObj = obj._jsonEncodeOverride()
        else:
            skipAttrs = []
            newObj = {}

        for attrName,attrType in inspect.get_annotations(objClass).items():

            if attrName in skipAttrs:
                continue

            attrValue = getattr(obj,attrName)
            encodeToKey = keyMappings[objClass].get(attrName)

            if encodeToKey is None:
                encodeToKey = _capitalizeAttrName(attrName)

            if encodeToKey == []:
                addValues = inner(attrValue,attrType)
                assert isinstance(addValues,JSONMultiKeyValue)
                newObj.update(addValues.value)

            else:

                if isinstance(encodeToKey,str):
                    encodeToKey = [encodeToKey]
                encodeInObj = newObj
                for k in encodeToKey[:-1]:
                    if encodeInObj.get(k) is None:
                        encodeInObj[k] = {}
                    encodeInObj = encodeInObj[k]
                encodeInKey = encodeToKey[-1]

                newElem = inner(attrValue,attrType)
                assert not isinstance(newElem,JSONMultiKeyValue)

                if encodeInKey in encodeInObj:
                    assert isinstance(encodeInObj[encodeInKey],dict)
                    assert isinstance(newElem,dict)
                    encodeInObj[encodeInKey].update(newElem)
                else:
                    encodeInObj[encodeInKey] = newElem

        return newObj

    result = inner(customObj,type(customObj))
    assert not isinstance(result,JSONMultiKeyValue)
    return result

#endregion