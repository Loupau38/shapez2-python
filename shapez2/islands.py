from . import utils, translations
from .utils import TileVector, ChunkVector

import json
import importlib.resources
from dataclasses import dataclass
import typing

ISLAND_TITLE_OVERRIDES = {
    k : v for k,v in [
        (f"{i}_{p}",f"@island-layout.Layout_{i}Node.title")
        for i in ["SpaceBelt","SpacePipe","Rail"]
        for p in [
            "Forward",
            "LeftTurn",
            "RightTurn",
            "LeftFwdSplitter",
            "RightFwdSplitter",
            "YSplitter",
            "TripleSplitter",
            "RightFwdMerger",
            "LeftFwdMerger",
            "YMerger",
            "TripleMerger"
        ]
    ]+[
        (f"{i}_{p}",f"@island-layout.Layout_{i}Node.title")
        for i in ["SpaceBelt","SpacePipe"]
        for p in [
            "Lift1UpForward",
            "Lift1UpLeft",
            "Lift1UpRight",
            "Lift1UpBackward",
            "Lift1DownForward",
            "Lift1DownLeft",
            "Lift1DownRight",
            "Lift1DownBackward",
            "Lift2UpForward",
            "Lift2UpLeft",
            "Lift2UpRight",
            "Lift2UpBackward",
            "Lift2DownForward",
            "Lift2DownLeft",
            "Lift2DownRight",
            "Lift2DownBackward"
        ]
    ]+[
        (f"Rail_{p}","@island-layout.Layout_RailNode.title")
        for p in ["YSplitterFlipped","TripleSplitterFlipped"]
    ]+[
        (f"Foundation_{type}{flipID}",f"{type} Foundation{flipText}")
        for type in [
            "1x1",
            "1x2",
            "1x3",
            "1x4",
            "2x2",
            "2x3",
            "2x4",
            "3x3",
            "T4",
            "L3",
            "L4",
            "S4",
            "C5"
        ]
        for flipID,flipText in [
            ("",""),
            ("_Flipped"," (Mirrored)")
        ]
    ]+[
        ("Layout_TrainLoader_Shapes_Flipped","Shape Wagon Loader (Mirrored)"),
        ("Layout_TrainUnloader_Shapes_Flipped","Shape Wagon Unloader (Mirrored)"),
        ("Layout_TrainTransfer_Shape_Flipped","Shape Wagon Transfer (Mirrored)"),
        ("Layout_TrainLoader_Fluids_Flipped","Fluid Wagon Loader (Mirrored)"),
        ("Layout_TrainUnloader_Fluids_Flipped","Fluid Wagon Unloader (Mirrored)"),
        ("Layout_TrainTransfer_Fluid_Flipped","Fluid Wagon Transfer (Mirrored)"),
        ("Layout_TrainRollerCoasterLoop_Flipped","Rail Loop (Mirrored)"),
    ]
}

ISLAND_GROUP_TITLE_OVERRIDES = {
    "FoundationGroup_1x1": "1x1 Foundation",
    "FoundationGroup_1x2": "1x2 Foundation",
    "FoundationGroup_1x3": "1x3 Foundation",
    "FoundationGroup_1x4": "1x4 Foundation",
    "FoundationGroup_2x2": "2x2 Foundation",
    "FoundationGroup_2x3": "2x3 Foundation",
    "FoundationGroup_2x4": "2x4 Foundation",
    "FoundationGroup_3x3": "3x3 Foundation",
    "FoundationGroup_T4": "T4 Foundation",
    "FoundationGroup_L3": "L3 Foundation",
    "FoundationGroup_L4": "L4 Foundation",
    "FoundationGroup_S4": "S4 Foundation",
    "FoundationGroup_C5": "C5 Foundation",
    "RailLiftUp1X1X2Group": "Rail Up 1 Floor",
    "RailLiftDown1X1X2Group": "Rail Down 1 Floor",
    "RailLiftUp1X1X3Group": "Rail Up 2 Floors",
    "RailLiftDown1X1X3Group": "Rail Down 2 Floors",
    "HUB": "Vortex"
}

@dataclass
class IslandChunk:
    buildableTiles:set[TileVector]

class Island(utils.HasUniqueID):

    def __init__(
        self,
        id:str,
        title:translations.MaybeTranslationString,
        chunks:dict[ChunkVector,IslandChunk],
        islandUnitCost:int,
        group:"IslandGroup"
    ) -> None:
        self.id = id
        self.title = title
        self.chunks = chunks
        self.islandUnitCost = islandUnitCost
        self.group = group
        self.totalBuildableTiles = set[TileVector]()
        for pos,chunk in chunks.items():
            self.totalBuildableTiles.update(pos.toTileVector()+t for t in chunk.buildableTiles)

@dataclass(eq=False)
class IslandGroup(utils.HasUniqueID):
    id:str
    title:translations.MaybeTranslationString
    islands:list[Island]

def _loadIslands() -> tuple[dict[str,Island],dict[str,IslandGroup]]:

    class PosFormat(typing.TypedDict):
        x:int
        y:int
        z:int

    class ChunkFormat(typing.TypedDict):
        Pos:PosFormat
        BuildableTiles:list[list[int]]

    class IslandFormat(typing.TypedDict):
        Id:str
        Title:str
        Cost:int
        GroupId:str
        Chunks:list[ChunkFormat]

    class IslandGroupFormat(typing.TypedDict):
        Id:str
        Title:str

    class FileFormat(typing.TypedDict):
        Islands:list[IslandFormat]
        Groups:list[IslandGroupFormat]

    with importlib.resources.files(__package__).joinpath("gameFiles/islands.json").open(encoding="utf-8") as f:
        islandsRaw:FileFormat = json.load(f)

    allIslands:dict[str,Island] = {}
    allIslandGroups:dict[str,IslandGroup] = {}

    for group in islandsRaw["Groups"]:
        groupId = group["Id"]
        if groupId in ISLAND_GROUP_TITLE_OVERRIDES:
            islandGroupTitle = ISLAND_GROUP_TITLE_OVERRIDES[groupId]
        else:
            islandGroupTitle = "@" + group["Title"]
        allIslandGroups[groupId] = IslandGroup(
            groupId,
            translations.MaybeTranslationString(islandGroupTitle),
            []
        )

    for islandRaw in islandsRaw["Islands"]:

        islandId = islandRaw["Id"]
        if islandId in ISLAND_TITLE_OVERRIDES:
            islandTitle = ISLAND_TITLE_OVERRIDES[islandId]
        else:
            islandTitle = "@" + islandRaw["Title"]

        curIslandGroup = allIslandGroups[islandRaw["Group"]]

        curChunks:dict[ChunkVector,IslandChunk] = {}
        for chunkRaw in islandRaw["Chunks"]:
            chunkPos = ChunkVector(
                chunkRaw["Pos"]["x"],
                chunkRaw["Pos"]["y"],
                chunkRaw["Pos"]["z"]
            )
            rawTiles:list[int] = []
            for tileRange in chunkRaw["BuildableTiles"]:
                rawTiles.extend(range(tileRange[0],tileRange[1]+1,tileRange[2]))
            chunkTiles = set[TileVector]()
            for rawTile in rawTiles:
                y, x = divmod(rawTile,utils.TILES_PER_CHUNK)
                chunkTiles.add(TileVector(x,y,0))
            curChunks[chunkPos] = IslandChunk(chunkTiles)

        curIsland = Island(
            islandId,
            translations.MaybeTranslationString(islandTitle),
            curChunks,
            islandRaw["Cost"],
            curIslandGroup
        )
        allIslands[islandId] = curIsland
        curIslandGroup.islands.append(curIsland)

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

_RAIL_PATH_TYPES = [
    "Forward",
    "LeftTurn",
    "RightTurn",
    "LeftFwdSplitter",
    "RightFwdSplitter",
    "YSplitter",
    "YSplitterFlipped",
    "TripleSplitter",
    "TripleSplitterFlipped",
    "RightFwdMerger",
    "LeftFwdMerger",
    "YMerger",
    "TripleMerger"
]

ISLAND_IDS = {
    "rails" : [
        allIslands[f"Rail_{path}"].id
        for path in _RAIL_PATH_TYPES
    ],
    "disableableTrainUnloadingLanes" : [
        allIslands[f"Layout_Train{pt}_{ct}{s}{f}"].id
        for ct in ("Shape","Fluid")
        for pt,s in (("Unloader","s"),("Transfer",""))
        for f in ("","_Flipped")
    ]
}