# The weird part of this library. The code of this library originates from ShapeBot 2,
# which was originally developed with pygame. To convert it to using Pillow,
# I created this interface which copies the pygame functions and classes used in the bot
# to not have to change the code too much, although as a result, some functions might not be
# as efficient as if they were done with Pillow directly

import PIL.Image
import typing
import os

SRCALPHA = 65536
type color = tuple[int,int,int] | tuple[int,int,int,int]
number = int | float

class error(RuntimeError): ...



class Surface:

    def __init__(self,size:tuple[number,number],flags:int=0,*,_fromImage:PIL.Image.Image|None=None) -> None:
        size = (round(size[0]),round(size[1]))
        if flags == 0:
            defaultColor = (0,0,0,255)
        elif flags == SRCALPHA:
            defaultColor = (0,0,0,0)
        else:
            raise NotImplementedError("Surface creation flags not supported")
        if _fromImage is None:
            self._image = PIL.Image.new("RGBA",size,defaultColor)
        else:
            self._image = _fromImage

    def get_width(self) -> int:
        return self._image.width

    def get_height(self) -> int:
        return self._image.height

    def get_size(self) -> tuple[int,int]:
        return self._image.size

    def get_at(self,x_y:tuple[int,int]) -> tuple[int,int,int,int]:
        return self._image.getpixel(x_y)

    def blit(self,source:typing.Self,dest:tuple[number,number]):
        dest = (round(dest[0]),round(dest[1]))
        self._image.alpha_composite(source._image,dest)

    def fill(self,color:color) -> None:
        self._image.paste(color,(0,0)+self._image.size)

    def copy(self) -> "Surface":
        return _imgToSurf(self._image.copy())



class Rect:

    def __init__(self,left:number,top:number,width:number,height:number) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def _toBBox(self) -> tuple[number,number,number,number]:
        return (self.left,self.top,self.left+self.width-1,self.top+self.height-1)



def _imgToSurf(img:PIL.Image.Image) -> Surface:
    return Surface((0,0),_fromImage=img)



from . import ( # circular import workaround
    draw,
    font,
    image,
    mask,
    transform
)



if "SHAPEZ2_USE_PYGAME" in os.environ:
    from pygame import *