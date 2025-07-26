from string import digits as DIGITS
import typing
from dataclasses import dataclass

def isNumber(string:str) -> bool:
    if string == "":
        return False
    for char in string:
        if char not in DIGITS:
            return False
    return True

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
class FloatPos:
    x:float
    y:float
    z:float=0.0

@dataclass
class Pos:
    x:int
    y:int
    z:int=0

    def __str__(self) -> str:
        return f"Pos({self.x},{self.y},{self.z})"

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash((self.x,self.y,self.z))

    def __eq__(self,other:typing.Self) -> bool:
        if not isinstance(other,Pos):
            return NotImplemented
        return (self.x == other.x) and (self.y == other.y) and (self.z == other.z)

    def rotateCW(self,numTimes:int|Rotation,aroundCenter:FloatPos=FloatPos(0,0)) -> "Pos":
        if isinstance(numTimes,Rotation):
            numTimes = numTimes.value
        x, y = self.x-aroundCenter.x, self.y-aroundCenter.y
        for _ in range(numTimes):
            x, y = -y, x
        return Pos(round(x+aroundCenter.x),round(y+aroundCenter.y),self.z)

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

def loadPos(raw:dict[str,int]) -> Pos:
    return Pos(
        raw.get("X",0),
        raw.get("Y",0),
        raw.get("Z",0)
    )

class DirectionType(typing.TypedDict):
    pos:Pos
    rot:Rotation
def loadDirection(raw:dict) -> DirectionType:
    return {
        "pos" : loadPos(raw.get("Position_L",{})),
        "rot" : Rotation(raw.get("Direction_L",0))
    }