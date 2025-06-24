# Extremely outdated (but planned to be updated),
# kept to not have to remove the /research-viewer command from ShapeBot 2

import json
import importlib.resources

class Node:
    def __init__(self,id:str,title:str,desc:str,goalShape:str,goalAmount:int,unlocks:list[str]) -> None:
        self.id = id
        self.title = title
        self.desc = desc
        self.goalShape = goalShape
        self.goalAmount = goalAmount
        self.unlocks = unlocks

class Level:
    def __init__(self,milestone:Node,sideGoals:list[Node]) -> None:
        self.milestone = milestone
        self.sideGoals = sideGoals

def _loadResearchTree() -> tuple[list[Level],str]:

    with importlib.resources.files(__package__).joinpath("gameFiles/research.json").open(encoding="utf-8") as f:
        researchRaw = json.load(f)

    treeVersion = researchRaw["GameVersion"]

    reserachTree = []

    for levelRaw in researchRaw["Levels"]:
        reserachTree.append(Level(
            Node(*levelRaw["Node"].values()),
            [Node(*sg.values()) for sg in levelRaw["SideGoals"]]
        ))

    return reserachTree, treeVersion

reserachTree, treeVersion = _loadResearchTree()