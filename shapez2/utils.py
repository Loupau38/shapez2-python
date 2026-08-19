from string import digits as DIGITS
import typing
from dataclasses import dataclass
import math

def isNumber(string:str) -> bool:
    if string == "":
        return False
    for char in string:
        if char not in DIGITS:
            return False
    return True

# todo : remove
def decodeStringWithLen(string:bytes,numBytesForLen:int=2,emptyIsLengthNegative1:bool=True) -> bytes:

    stringLen = len(string)
    if stringLen < numBytesForLen:
        raise ValueError(f"String must be at least {numBytesForLen} characters long but is {stringLen}")

    encodedLength, string = string[:numBytesForLen], string[numBytesForLen:]
    decodedLength = int.from_bytes(encodedLength,"little",signed=True)

    if (emptyIsLengthNegative1) and (decodedLength == -1):
        decodedLength = 0

    if decodedLength < 0:
        raise ValueError(f"String length can't be negative : {decodedLength}")

    return string[:decodedLength]

# todo : remove
def encodeStringWithLen(string:bytes,numBytesForLen:int=2,emptyIsLengthNegative1:bool=True) -> bytes:
    stringLen = len(string)
    if emptyIsLengthNegative1 and (stringLen == 0):
        stringLen = -1
    return stringLen.to_bytes(numBytesForLen,"little",signed=True) + string

@dataclass
class Rotation:
    value:int

    def rotateCW(self,numTimes:int|typing.Self) -> "Rotation":
        if isinstance(numTimes,Rotation):
            numTimes = numTimes.value
        return Rotation((self.value+numTimes)%4)

@dataclass
class _Float3:
    x:float
    y:float
    z:float=0.0

class FloatPos(_Float3): ...
class FloatVector(_Float3): ...

@dataclass
class _Int3:
    x:int
    y:int
    z:int=0

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.x},{self.y},{self.z})"

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash((self.x,self.y,self.z))

    def __eq__(self,other:typing.Any) -> bool:
        if not isinstance(other,_Int3):
            return NotImplemented
        return (self.x == other.x) and (self.y == other.y) and (self.z == other.z)

    def __add__(self,other:"_Int3") -> "_Int3":
        if not isinstance(other,_Int3):
            return NotImplemented
        return _Int3(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z
        )

class Vector(_Int3):

    @typing.overload
    def __add__(self,other:"Vector") -> "Vector": ...

    @typing.overload
    def __add__(self,other:"Pos") -> "Pos": ...

    def __add__(self,other):
        result = super().__add__(other)
        if isinstance(other,Vector):
            return Vector(result.x,result.y,result.z)
        if isinstance(other,Pos):
            return Pos(result.x,result.y,result.z)
        return NotImplemented

    def rotateCW(
        self,
        numTimes:int|Rotation,
        aroundCenter:FloatVector=FloatVector(0,0)
    ) -> typing.Self:
        """`aroundCenter` and `self` must have the same origin"""
        if isinstance(numTimes,Rotation):
            numTimes = numTimes.value
        x, y = self.x-aroundCenter.x, self.y-aroundCenter.y
        for _ in range(numTimes):
            x, y = -y, x
        return type(self)(round(x+aroundCenter.x),round(y+aroundCenter.y),self.z)

class Pos(_Int3):

    def __add__(self,other:Vector) -> "Pos":
        if isinstance(other,Vector):
            result = super().__add__(other)
            return Pos(result.x,result.y,result.z)
        return NotImplemented

    def rotateCW(
        self,
        numTimes:int|Rotation,
        aroundCenter:FloatPos=FloatPos(0,0)
    ) -> typing.Self:
        if isinstance(numTimes,Rotation):
            numTimes = numTimes.value
        x, y = self.x-aroundCenter.x, self.y-aroundCenter.y
        for _ in range(numTimes):
            x, y = -y, x
        return type(self)(round(x+aroundCenter.x),round(y+aroundCenter.y),self.z)

TILES_PER_CHUNK = 20
CHUNKS_PER_SUPER_CHUNK = 64

class TileVector(Vector):

    @typing.overload
    def __add__(self,other:"TileVector") -> "TileVector": ...

    @typing.overload
    def __add__(self,other:"GlobalTileCoordinate") -> "GlobalTileCoordinate": ...

    def __add__(self,other:"TileVector"|"GlobalTileCoordinate") -> "TileVector"|"GlobalTileCoordinate":
        if isinstance(other,TileVector):
            result = super().__add__(other)
            return TileVector(result.x,result.y,result.z)
        if isinstance(other,GlobalTileCoordinate):
            result = super().__add__(other)
            return GlobalTileCoordinate(result.x,result.y,result.z)
        return NotImplemented

    def toGlobalTile(self,islandPos:"GlobalChunkCoordinate") -> "GlobalTileCoordinate":
        return islandPos.tileOrigin() + self

class GlobalTileCoordinate(Pos):

    def __add__(self,other:TileVector) -> "GlobalTileCoordinate":
        if isinstance(other,TileVector):
            return other + self
        return NotImplemented

    def toIslandTile(self,islandPos:"GlobalChunkCoordinate") -> TileVector:
        islandOrigin = islandPos.tileOrigin()
        return TileVector(
            self.x - islandOrigin.x,
            self.y - islandOrigin.y,
            self.z - islandOrigin.z
        )

    def containedInGlobalChunk(self) -> "GlobalChunkCoordinate":
        return GlobalChunkCoordinate(
            self.x // TILES_PER_CHUNK,
            self.y // TILES_PER_CHUNK,
            self.z // TILES_PER_CHUNK
        )

class ChunkVector(Vector):

    @typing.overload
    def __add__(self,other:"ChunkVector") -> "ChunkVector": ...

    @typing.overload
    def __add__(self,other:"GlobalChunkCoordinate") -> "GlobalChunkCoordinate": ...

    def __add__(self,other:"ChunkVector"|"GlobalChunkCoordinate") -> "ChunkVector"|"GlobalChunkCoordinate":
        if isinstance(other,ChunkVector):
            result = super().__add__(other)
            return ChunkVector(result.x,result.y,result.z)
        if isinstance(other,GlobalChunkCoordinate):
            result = super().__add__(other)
            return GlobalChunkCoordinate(result.x,result.y,result.z)
        return NotImplemented

    def toTileVector(self) -> TileVector:
        return TileVector(
            self.x * TILES_PER_CHUNK,
            self.y * TILES_PER_CHUNK,
            self.z * TILES_PER_CHUNK
        )

class GlobalChunkCoordinate(Pos):

    def __add__(self,other:ChunkVector) -> "GlobalChunkCoordinate":
        if isinstance(other,ChunkVector):
            return other + self
        return NotImplemented

    def tileOrigin(self) -> GlobalTileCoordinate:
        return GlobalTileCoordinate(
            self.x * TILES_PER_CHUNK,
            self.y * TILES_PER_CHUNK,
            self.z * TILES_PER_CHUNK
        )

    def containedInSuperChunk(self) -> "SuperChunkCoordinate":
        return SuperChunkCoordinate(
            math.floor((self.x+(CHUNKS_PER_SUPER_CHUNK/2))/CHUNKS_PER_SUPER_CHUNK),
            math.floor((self.y+(CHUNKS_PER_SUPER_CHUNK/2))/CHUNKS_PER_SUPER_CHUNK)
        )

class SuperChunkVector(Vector):
    """z attribute shouldn't be used"""

    @typing.overload
    def __add__(self,other:"SuperChunkVector") -> "SuperChunkVector": ...

    @typing.overload
    def __add__(self,other:"SuperChunkCoordinate") -> "SuperChunkCoordinate": ...

    def __add__(self,other:"ChunkVector"|"SuperChunkCoordinate") -> "SuperChunkVector"|"SuperChunkCoordinate":
        if isinstance(other,SuperChunkVector):
            result = super().__add__(other)
            return SuperChunkVector(result.x,result.y)
        if isinstance(other,SuperChunkCoordinate):
            result = super().__add__(other)
            return SuperChunkCoordinate(result.x,result.y)
        return NotImplemented

class SuperChunkCoordinate(Pos):
    """z attribute shouldn't be used"""

    def __add__(self,other:SuperChunkVector) -> "SuperChunkCoordinate":
        if isinstance(other,SuperChunkVector):
            return other + self
        return NotImplemented

    def globalChunkOrigin(self) -> GlobalChunkCoordinate:
        return GlobalChunkCoordinate(
            (self.x*CHUNKS_PER_SUPER_CHUNK) - (CHUNKS_PER_SUPER_CHUNK//2),
            (self.y*CHUNKS_PER_SUPER_CHUNK) - (CHUNKS_PER_SUPER_CHUNK//2),
            0
        )

@dataclass
class Size:
    width:int
    height:int
    depth:int=0

    def rotateCW(self,numTimes:int|Rotation) -> "Size":
        if isinstance(numTimes,Rotation):
            numTimes = numTimes.value
        width, height = self.width, self.height
        for _ in range(numTimes):
            width, height = height, width
        return Size(width,height,self.depth)

@dataclass
class Rect:
    topLeft:Pos
    size:Size

    def rotateCW(self,numTimes:int|Rotation,aroundCenter:FloatPos=FloatPos(0,0)) -> "Rect":
        if isinstance(numTimes,Rotation):
            numTimes = numTimes.value
        left, top = self.topLeft.x-aroundCenter.x, self.topLeft.y-aroundCenter.y
        width, height = self.size.width, self.size.height
        for _ in range(numTimes):
            left, top = -top-height+1, left
            width, height = height, width
        return Rect(
            Pos(round(left+aroundCenter.x),round(top+aroundCenter.y)),
            Size(width,height)
        )

    def containsPos(self,pos:Pos) -> bool:
        if pos.x < self.topLeft.x:
            return False
        if pos.y < self.topLeft.y:
            return False
        if pos.x >= self.topLeft.x+self.size.width:
            return False
        if pos.y >= self.topLeft.y+self.size.height:
            return False
        return True

class HasUniqueID:
    """If using this on a dataclass, don't forget to set `eq=False` !"""

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,type(self)):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)