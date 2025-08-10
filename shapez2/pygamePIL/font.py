from . import color, Surface, _imgToSurf
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import typing

def init() -> None:
    pass

class Font:

    def __init__(self,name:typing.Any,size:int) -> None:
        self._font = PIL.ImageFont.truetype(name,size)
        self.underline = False

    def render(self,text:str,antialias:bool|typing.Literal[0,1],color:color,background:color|None=None) -> Surface:

        UNDERLINE_HEIGHT = 2

        if not antialias:
            raise NotImplementedError("Text rendering without antialias not supported")

        bbox = self._font.getbbox(text)

        kwargs = {}
        if background is not None:
            kwargs["color"] = background

        image = PIL.Image.new("RGBA",(bbox[2]+1,bbox[3]+1+(UNDERLINE_HEIGHT if self.underline else 0)),**kwargs)
        imageDraw = PIL.ImageDraw.Draw(image)
        imageDraw.text((0,0),text,color,self._font)

        if self.underline:
            imageDraw.line(((bbox[0],bbox[3]+UNDERLINE_HEIGHT),(bbox[2],bbox[3]+UNDERLINE_HEIGHT)),color)

        return _imgToSurf(image)