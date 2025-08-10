from . import Surface, _imgToSurf

def smoothscale(surface:Surface,size:tuple[int,int]) -> Surface:
    return _imgToSurf(surface._image.resize(size))

def rotate(surface:Surface,angle:float) -> Surface:
    return _imgToSurf(surface._image.rotate(angle,expand=True))