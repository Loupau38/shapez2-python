from . import number, Surface, color, Rect
import PIL.ImageDraw
import math

def _invalidBBoxCheck(bbox:tuple[number,number,number,number]) -> bool:
    return (bbox[2] < bbox[0]) or (bbox[3] < bbox[1])

def rect(surface:Surface,color:color,rect:Rect,width:int=0,border_radius:int=-1) -> None:
    curBBox = rect._toBBox()
    if _invalidBBoxCheck(curBBox):
        return
    fillColor = color if width == 0 else None
    outlineColor = None if width == 0 else color
    draw = PIL.ImageDraw.Draw(surface._image)
    if border_radius < 0:
        draw.rectangle(curBBox,fillColor,outlineColor,width)
    else:
        draw.rounded_rectangle(curBBox,border_radius,fillColor,outlineColor,width)

def line(surface:Surface,color:color,start_pos:tuple[number,number],end_pos:tuple[number,number],width:int=1) -> None:
    PIL.ImageDraw.Draw(surface._image).line([start_pos,end_pos],color,width)

def circle(
    surface:Surface,color:color,center:tuple[number,number],radius:float,width:int=0,
    draw_top_right:bool=False,draw_top_left:bool=False,draw_bottom_left:bool=False,draw_bottom_right:bool=False
) -> None:

    bbox = (center[0]-radius,center[1]-radius,center[0]+radius-1,center[1]+radius-1)
    if _invalidBBoxCheck(bbox):
        return
    draw = PIL.ImageDraw.Draw(surface._image)

    if draw_top_right or draw_top_left or draw_bottom_left or draw_bottom_right:

        for quadrant,startAngle,stopAngle in [
            (draw_bottom_right,0,90),
            (draw_bottom_left,90,180),
            (draw_top_left,180,270),
            (draw_top_right,270,360)
        ]:
            if quadrant:
                draw.arc(bbox,startAngle,stopAngle,color,round(radius) if width == 0 else width)

    else:

        fillColor = color if width == 0 else None
        outlineColor = None if width == 0 else color
        draw.ellipse(bbox,fillColor,outlineColor,width)

def arc(surface:Surface,color:color,rect:Rect,start_angle:float,stop_angle:float,width:int=1) -> None:
    curBBox = rect._toBBox()
    if _invalidBBoxCheck(curBBox):
        return
    PIL.ImageDraw.Draw(surface._image).arc(
        curBBox,
        360 - math.degrees(stop_angle),
        360 - math.degrees(start_angle),
        color,
        width
    )

def polygon(surface:Surface,color:color,points:list[tuple[number,number]],width:int=0):
    draw = PIL.ImageDraw.Draw(surface._image)
    if width == 0:
        draw.polygon(points,color)
    else:
        for i,point in enumerate(points):
            draw.line([point,points[(i+1)%len(points)]],color,width)