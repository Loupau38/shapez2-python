from . import gameObjects, utils, islands, buildings, shapeCodes

import fixedint
import enum
from collections.abc import Callable

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
    BlobStart = checkpointHash("blob:start")
    BlobEnd = checkpointHash("blob:end")
    Island = checkpointHash("island")
    Buildings = checkpointHash("buildings")
    Building = checkpointHash("building")

class EndOfStreamError(Exception): ...
class InvalidSerializedData(Exception): ...

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
            raise InvalidSerializedData(f"Checkpoint mismatch, excpected {checkpoint.value}, got {read}")

    def readBlob(self,callback:Callable[[],None]) -> None:

        self.assertCheckpoint(Checkpoint.BlobStart)
        blobLen = self.readInt()
        startPos = self.pos

        callback()

        if self.pos != startPos+blobLen:
            raise InvalidSerializedData("Blob length mismatch")

        self.assertCheckpoint(Checkpoint.BlobEnd)

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

        self.writeCheckpoint(Checkpoint.BlobStart)
        startPos = self.pos
        self.writeInt(0) # reserve space for the length

        callback()

        endPos = self.pos
        blobLen = endPos - startPos - 4
        self.pos = startPos
        self.writeInt(blobLen)
        self.pos = endPos
        self.writeCheckpoint(Checkpoint.BlobEnd)

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
        self.stringLUT = stringLUT

    def readString(self) -> str|None:
        return self.stringLUT.getString(self.readInt())

class BinaryStreamWriterWithStringLUT(BinaryStreamWriter):

    def __init__(self,checkpoints:bool,stringLUT:StringLUTReadWrite):
        super().__init__(checkpoints)
        self.stringLUT = stringLUT

    def writeString(self,string:str|None) -> None:
        self.writeInt(self.stringLUT.getIndex(string))

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

    def deserialize[T](self,reader:BinaryStreamReader,into:type[T]) -> T:

        # generic game objects

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
                reader.read(1)[0]
            )

        if into == utils.Rotation:
            return utils.Rotation(reader.read(1)[0])

        # game objects for config

        if into == gameObjects.ISignal:
            signalType = reader.read(1)[0]
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
                    self.deserialize(reader,gameObjects.IBeltItem)
                )
            if signalType == 7:
                return gameObjects.FluidSignal.fromFluid(
                    self.deserialize(reader,gameObjects.IFluid)
                )
            raise InvalidSerializedData(f"Unknown signal type : {signalType}")

        if into == gameObjects.IBeltItem:
            itemType = reader.read(1)[0]
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
            shapeCode = reader.readString()
            if shapeCode is None:
                raise InvalidSerializedData("Shape code can't be null")
            valid, error, shapeConfigs, colorSchemes = shapeCodes.isShapeCodeValid(
                shapeCode,self.shapesConfigs,self.colorSchemes,True
            )
            if not valid:
                raise InvalidSerializedData(f"Invalid shape code : {error}")
            self.shapesConfigs = shapeConfigs
            self.colorSchemes = colorSchemes
            return gameObjects.ShapeItem(gameObjects.Shape.fromShapeCode(
                shapeCode,
                self.shapesConfigs[0],
                self.colorSchemes[0]
            ))

        # island config

        if into == gameObjects.RailConfig:
            return gameObjects.RailConfig([
                gameObjects.RailConnectionColorFilter(reader.readInt())
                for _ in range(reader.readInt())
            ])

        if into == gameObjects.DisableableTrainUnloadingLanesConfig:
            return gameObjects.DisableableTrainUnloadingLanesConfig([
                reader.readInt() for _ in range(reader.readInt())
            ])

        # building config

        if into == gameObjects.LabelConfig:
            return gameObjects.LabelConfig(reader.readString())

        if into == gameObjects.SignalProducerConfig:
            return gameObjects.SignalProducerConfig(
                self.deserialize(reader,gameObjects.ISignal)
            )

        # other

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

        raise ValueError(f"Unknown type for deserialization : {into}")