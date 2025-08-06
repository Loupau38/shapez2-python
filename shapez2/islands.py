from . import utils, translations
from .utils import Rotation, Pos, Size, Rect

import json
import importlib.resources
from dataclasses import dataclass
import typing

ISLAND_SIZE = 20
DEFAULT_REMOVED_ISLAND_SIZE = 3
REDUCED_REMOVED_ISLAND_SIZE = DEFAULT_REMOVED_ISLAND_SIZE + 1
NOTCH_SIZE = 4

@dataclass
class IslandTile:
    pos:Pos
    buildArea:list[Rect]

class Island:

    def __init__(
        self,
        id:str,
        title:translations.MaybeTranslationString,
        tiles:list[IslandTile],
        islandUnitCost:int|float,
        group:"IslandGroup"
    ) -> None:
        self.id = id
        self.title = title
        self.tiles = tiles
        self.islandUnitCost = islandUnitCost
        self.group = group
        self.totalBuildArea:list[Rect] = []
        for tile in tiles:
            for area in tile.buildArea:
                self.totalBuildArea.append(Rect(
                    Pos((tile.pos.x*ISLAND_SIZE)+area.topLeft.x,(tile.pos.y*ISLAND_SIZE)+area.topLeft.y),
                    area.size
                ))

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,Island):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

@dataclass
class IslandGroup:
    id:str
    title:translations.MaybeTranslationString
    islands:list[Island]

    def __eq__(self,other:object) -> bool:
        if not isinstance(other,IslandGroup):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

def _loadIslands() -> tuple[dict[str,Island],dict[str,IslandGroup]]:

    class TileFormat(typing.TypedDict):
        x:typing.NotRequired[int]
        y:typing.NotRequired[int]
        z:typing.NotRequired[int]

    class BAOFormat(typing.TypedDict):
        Tile:TileFormat
        Rects:list[list[int]]

    class IslandFormat(typing.TypedDict):
        Id:str
        Title:typing.NotRequired[str]
        Tiles:list[TileFormat]
        ReducedSides:typing.NotRequired[list[dict]]
        BuildAreaOverride:typing.NotRequired[list[BAOFormat]]
        NoBuildArea:typing.NotRequired[bool]
        IslandUnitCost:typing.NotRequired[int]
        Group:str

    class IslandGroupFormat(typing.TypedDict):
        Common:IslandFormat
        Islands:list[IslandFormat]

    class FileFormat(typing.TypedDict):
        SimilarIslands:list[IslandGroupFormat]
        Islands:list[IslandFormat]
        ExtraGroups:list[str]
        GroupTitleOverrides:dict[str,str]

    with importlib.resources.files(__package__).joinpath("gameFiles/islands.json").open(encoding="utf-8") as f:
        islandsRaw:FileFormat = json.load(f)

    for islandGroup in islandsRaw["SimilarIslands"]:
        for island in islandGroup["Islands"]:
            newIsland = islandGroup["Common"].copy()
            newIsland.update(island)
            islandsRaw["Islands"].append(newIsland)

    allIslands:dict[str,Island] = {}
    allIslandGroups:dict[str,IslandGroup] = {}

    def createIslandGroup(id:str) -> None:
        if islandsRaw["GroupTitleOverrides"].get(id) is None:
            islandGroupTitle = f"@island-group.{id}.title"
        else:
            islandGroupTitle = islandsRaw["GroupTitleOverrides"][id]
        allIslandGroups[id] = IslandGroup(
            id,
            translations.MaybeTranslationString(islandGroupTitle),
            []
        )

    for islandRaw in islandsRaw["Islands"]:

        curRemovedNotches:list[tuple[Pos,Rotation]] = [
            ((rn:=utils.loadDirection(rnr))["pos"],rn["rot"]) for rnr in islandRaw.get("RemovedNotches",[])
        ]
        curReducedSides:list[tuple[Pos,Rotation]] = [
            ((rs:=utils.loadDirection(rsr))["pos"],rs["rot"]) for rsr in islandRaw.get("ReducedSides",[])
        ]
        curBuildAreaOverrides:dict[Pos,list[Rect]] = {}
        for baor in islandRaw.get("BuildAreaOverride",[]):
            curBAORects = []
            for baorr in baor["Rects"]:
                curBAORects.append(Rect(
                    Pos(baorr[0],baorr[1]),
                    Size(baorr[2],baorr[3])
                ))
            curBuildAreaOverrides[utils.loadPos(baor["Tile"])] = curBAORects

        curTiles = [utils.loadPos(tr) for tr in islandRaw["Tiles"]]

        generatedIslandTiles = []

        for tile in curTiles:

            if islandRaw.get("NoBuildArea",False):
                generatedIslandTiles.append(IslandTile(tile,[]))
                continue

            if curBuildAreaOverrides.get(tile) is not None:
                generatedIslandTiles.append(IslandTile(tile,curBuildAreaOverrides[tile]))
                continue

            curCurReducedSides:dict[int,bool] = {
                r1 : any(((p == tile) and (r2.value == r1)) for p,r2 in curReducedSides) for r1 in range(4)
            }
            curCurRemovedNotches:dict[int,bool] = {
                r1 : any(((p == tile) and (r2.value == r1)) for p,r2 in curRemovedNotches) for r1 in range(4)
            }

            neighboringTiles:dict[Pos,bool] = {}
            for x in range(-1,2):
                for y in range(-1,2):
                    neighboringTiles[Pos(x,y)] = Pos(tile.x+x,tile.y+y) in curTiles

            buildAreas = []

            eastUnconnected = ISLAND_SIZE - (REDUCED_REMOVED_ISLAND_SIZE if curCurReducedSides[0] else DEFAULT_REMOVED_ISLAND_SIZE) - 1
            southUnconnected = ISLAND_SIZE - (REDUCED_REMOVED_ISLAND_SIZE if curCurReducedSides[1] else DEFAULT_REMOVED_ISLAND_SIZE) - 1
            westUnconnected = REDUCED_REMOVED_ISLAND_SIZE if curCurReducedSides[2] else DEFAULT_REMOVED_ISLAND_SIZE
            northUnconnected = REDUCED_REMOVED_ISLAND_SIZE if curCurReducedSides[3] else DEFAULT_REMOVED_ISLAND_SIZE

            buildAreas.append(Rect(
                Pos(westUnconnected,northUnconnected),
                Size(eastUnconnected-westUnconnected+1,southUnconnected-northUnconnected+1)
            ))

            if ( # east side
                (not curCurReducedSides[0]) and
                (neighboringTiles[Pos(1,0)])
            ):
                buildAreas.append(Rect(
                    Pos(ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE,northUnconnected),
                    Size(DEFAULT_REMOVED_ISLAND_SIZE,southUnconnected-northUnconnected+1)
                ))

            if ( # south side
                (not curCurReducedSides[1]) and
                (neighboringTiles[Pos(0,1)])
            ):
                buildAreas.append(Rect(
                    Pos(westUnconnected,ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE),
                    Size(eastUnconnected-westUnconnected+1,DEFAULT_REMOVED_ISLAND_SIZE)
                ))

            if ( # west side
                (not curCurReducedSides[2]) and
                (neighboringTiles[Pos(-1,0)])
            ):
                buildAreas.append(Rect(
                    Pos(0,northUnconnected),
                    Size(DEFAULT_REMOVED_ISLAND_SIZE,southUnconnected-northUnconnected+1)
                ))

            if ( # north side
                (not curCurReducedSides[3]) and
                (neighboringTiles[Pos(0,-1)])
            ):
                buildAreas.append(Rect(
                    Pos(westUnconnected,0),
                    Size(eastUnconnected-westUnconnected+1,DEFAULT_REMOVED_ISLAND_SIZE)
                ))

            if ( # north east corner
                (not curCurReducedSides[0]) and
                (not curCurReducedSides[3]) and
                (neighboringTiles[Pos(0,-1)]) and
                (neighboringTiles[Pos(1,0)]) and
                (neighboringTiles[Pos(1,-1)])
            ):
                buildAreas.append(Rect(
                    Pos(ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE,0),
                    Size(DEFAULT_REMOVED_ISLAND_SIZE,DEFAULT_REMOVED_ISLAND_SIZE)
                ))

            if ( # south east corner
                (not curCurReducedSides[0]) and
                (not curCurReducedSides[1]) and
                (neighboringTiles[Pos(1,0)]) and
                (neighboringTiles[Pos(1,1)]) and
                (neighboringTiles[Pos(0,1)])
            ):
                buildAreas.append(Rect(
                    Pos(ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE,ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE),
                    Size(DEFAULT_REMOVED_ISLAND_SIZE,DEFAULT_REMOVED_ISLAND_SIZE)
                ))

            if ( # south west corner
                (not curCurReducedSides[2]) and
                (not curCurReducedSides[1]) and
                (neighboringTiles[Pos(0,1)]) and
                (neighboringTiles[Pos(-1,1)]) and
                (neighboringTiles[Pos(-1,0)])
            ):
                buildAreas.append(Rect(
                    Pos(0,ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE),
                    Size(DEFAULT_REMOVED_ISLAND_SIZE,DEFAULT_REMOVED_ISLAND_SIZE)
                ))

            if ( # north west corner
                (not curCurReducedSides[2]) and
                (not curCurReducedSides[3]) and
                (neighboringTiles[Pos(-1,0)]) and
                (neighboringTiles[Pos(-1,-1)]) and
                (neighboringTiles[Pos(0,-1)])
            ):
                buildAreas.append(Rect(
                    Pos(0,0),
                    Size(DEFAULT_REMOVED_ISLAND_SIZE,DEFAULT_REMOVED_ISLAND_SIZE)
                ))

            if ( # east notch
                (not neighboringTiles[Pos(1,0)]) and
                (not curCurReducedSides[0]) and
                (not curCurRemovedNotches[0])
            ):
                buildAreas.append(Rect(
                    Pos(ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE,int((ISLAND_SIZE/2)-(NOTCH_SIZE/2))),
                    Size(1,NOTCH_SIZE)
                ))

            if ( # south notch
                (not neighboringTiles[Pos(0,1)]) and
                (not curCurReducedSides[1]) and
                (not curCurRemovedNotches[1])
            ):
                buildAreas.append(Rect(
                    Pos(int((ISLAND_SIZE/2)-(NOTCH_SIZE/2)),ISLAND_SIZE-DEFAULT_REMOVED_ISLAND_SIZE),
                    Size(NOTCH_SIZE,1)
                ))

            if ( # west notch
                (not neighboringTiles[Pos(-1,0)]) and
                (not curCurReducedSides[2]) and
                (not curCurRemovedNotches[2])
            ):
                buildAreas.append(Rect(
                    Pos(DEFAULT_REMOVED_ISLAND_SIZE-1,int((ISLAND_SIZE/2)-(NOTCH_SIZE/2))),
                    Size(1,NOTCH_SIZE)
                ))

            if ( # north notch
                (not neighboringTiles[Pos(0,-1)]) and
                (not curCurReducedSides[3]) and
                (not curCurRemovedNotches[3])
            ):
                buildAreas.append(Rect(
                    Pos(int((ISLAND_SIZE/2)-(NOTCH_SIZE/2)),DEFAULT_REMOVED_ISLAND_SIZE-1),
                    Size(NOTCH_SIZE,1)
                ))

            generatedIslandTiles.append(IslandTile(tile,buildAreas))

        if islandRaw.get("Title") is None:
            islandTitle = f"@island-layout.{islandRaw['Id']}.title"
        else:
            islandTitle = islandRaw["Title"]

        curGroupId = islandRaw["Group"]
        if allIslandGroups.get(curGroupId) is None:
            createIslandGroup(curGroupId)
        curIslandGroup = allIslandGroups[curGroupId]

        curIsland = Island(
            islandRaw["Id"],
            translations.MaybeTranslationString(islandTitle),
            generatedIslandTiles,
            islandRaw.get("IslandUnitCost",len(generatedIslandTiles)),
            curIslandGroup
        )
        allIslands[islandRaw["Id"]] = curIsland
        curIslandGroup.islands.append(curIsland)

    for groupId in islandsRaw["ExtraGroups"]:
        createIslandGroup(groupId)

    return allIslands, allIslandGroups

allIslands, allIslandGroups = _loadIslands()

def getCategorizedIslandCounts(counts:dict[Island,int]) -> dict[IslandGroup,dict[Island,int]]:

    groups = {}
    for i,c in counts.items():
        curGroup = i.group
        if groups.get(curGroup) is None:
            groups[curGroup] = {}
        groups[curGroup][i] = c

    return groups