from . import Surface
import PIL.Image

class Mask:

    def __init__(self,_image:PIL.Image.Image) -> None:
        self._image = _image

    def to_surface(self,surface:Surface,setsurface:Surface,unsetcolor:None) -> None:
        surface._image.paste(setsurface._image,(0,0),self._image)

def from_surface(surface:Surface,treshold:int=127) -> Mask:
    return Mask(surface._image.getchannel("A").point(lambda x: 1 if x > treshold else 0,"1"))