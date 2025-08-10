from . import Surface, error, _imgToSurf
import PIL.Image
import io

def load(filename:str|io.BytesIO) -> Surface:
    try:
        image = PIL.Image.open(filename)
    except PIL.UnidentifiedImageError:
        raise error
    return _imgToSurf(image.convert("RGBA"))

def save(surface:Surface,filename:str|io.BytesIO,namehint:str="") -> None:
    surface._image.save(filename,None if namehint == "" else namehint)