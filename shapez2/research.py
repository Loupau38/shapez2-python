from . import(
    ingameData,
    gameObjects,
    translations,
    buildings,
    islands,
    utils,
    shapeCodes
)

import json
import importlib.resources
from dataclasses import dataclass
from enum import Enum
import typing
import inspect
import types

T = typing.TypeVar("T")

SCENARIOS_PATH = "gameFiles/{id}-scenario.json"
SCENARIO_IDS = [
    "default",
    "hard",
    "hexagonal",
    "insane",
    "onboarding"
]



# region formats

@dataclass
class OptionalValueFormat[T1,T2]:
    valueFormat:T1
    default:T2

@dataclass
class RestrictedValuesFormat:
    allowedValues:type[Enum]|list

noFormatCheck = object()
rewardObject = object()
costObject = object()

class RewardType(Enum):
    BuildingReward = "BuildingReward"
    IslandGroupReward = "IslandGroupReward"
    MechanicReward = "MechanicReward"
    WikiEntryReward = "WikiEntryReward"
    BlueprintCurrencyReward = "BlueprintCurrencyReward"
    ChunkLimitReward = "ChunkLimitReward"
    ResearchPointsReward = "ResearchPointsReward"

class CostType(Enum):
    ResearchPointsCost = "ResearchPointsCost"

class TutorialConfig(Enum):
    TCMainTutorial = "TCMainTutorial"
    TCNoTutorial = "TCNoTutorial"

class GameMode(Enum):
    RegularGameMode = "RegularGameMode"

SHAPE_COSTS_FORMAT = [
    {
        "Shape" : str,
        "Amount" : int
    }
]

COST_FORMAT = {
    "$type" : RestrictedValuesFormat(CostType),
    "Amount" : OptionalValueFormat(int,None)
}

REWARD_FORMAT = {
    "$type" : RestrictedValuesFormat(RewardType),
    "BuildingDefinitionGroupId" : OptionalValueFormat(str,None),
    "GroupId" : OptionalValueFormat(str,None),
    "MechanicId" : OptionalValueFormat(str,None),
    "EntryId" : OptionalValueFormat(str,None),
    "Amount" : OptionalValueFormat(int,None)
}

POS_FORMAT = {
    "x" : OptionalValueFormat(int,0),
    "y" : OptionalValueFormat(int,0),
    "z" : OptionalValueFormat(int,0)
}

SCENARIO_FORMAT = {
    "FormatVersion" : RestrictedValuesFormat([2]),
    "GameVersion" : int,
    "UniqueId" : str,
    "IsTutorial" : OptionalValueFormat(bool,False),
    "SupportedGameModes" : [RestrictedValuesFormat(GameMode)],
    "NextScenarios" : [str],
    "ExampleShapes" : [str],
    "Title" : str,
    "Description" : str,
    "PreviewImageId" : str,
    "ResearchConfig" : {
        "BaseChunkLimitMultiplier" : int,
        "BaseBlueprintRewardMultiplier" : int,
        "MaxShapeLayers" : int,
        "InitialResearchPoints" : OptionalValueFormat(int,0),
        "ShapesConfigurationId" : RestrictedValuesFormat([
            ingameData.QUAD_SHAPES_CONFIG.id,
            ingameData.HEX_SHAPES_CONFIG.id
        ]),
        "ColorSchemeConfigurationId" : RestrictedValuesFormat([
            ingameData.DEFAULT_COLOR_SCHEME.id
        ]),
        "ResearchLevelsAreProgressive" : bool,
        "BlueprintCurrencyShapes" : [
            {
                "Shape" : str,
                "RequiredUpgradeIds" : [str],
                "RequiredMechanicIds" : [str],
                "Amount" : int
            }
        ],
        "IntroductionWikiEntryId" : str,
        "InitiallyUnlockedUpgrades" : [str],
        "TutorialConfig" : RestrictedValuesFormat(TutorialConfig)
    },
    "Progression" : {
        "Levels" : {
            "Levels" : [
                {
                    "Definition" : {
                        "Id" : str,
                        "VideoId" : str,
                        "PreviewImageId" : str,
                        "Title" : str,
                        "Description" : str,
                        "WikiEntryId" : OptionalValueFormat(str,None),
                    },
                    "Lines" : {
                        "Lines" : [
                            {
                                "ReusedAtNextMilestone" : OptionalValueFormat(bool,False),
                                "ReusedAtNextMilestoneOffset" : OptionalValueFormat(int,0),
                                "ReusedAtSameMilestone" : OptionalValueFormat(bool,False),
                                "ReusedAtSameMilestoneOffset" : OptionalValueFormat(int,0),
                                "ReusedForPlayerLevel" : OptionalValueFormat(bool,False),
                                "StartingOffset" : OptionalValueFormat(int,0),
                                "Shapes" : SHAPE_COSTS_FORMAT
                            }
                        ]
                    },
                    "Rewards" : {
                        "Rewards" : [rewardObject]
                    }
                }
            ]
        },
        "SideQuestGroups" : {
            "SideQuestGroups" : [
                {
                    "Title" : str,
                    "RequiredUpgradeIds" : [str],
                    "RequiredMechanicIds" : [str],
                    "SideQuests" : [
                        {
                            "Id" : str,
                            "IsFollowupForLevel" : OptionalValueFormat(bool,False),
                            "Rewards" : [rewardObject],
                            "Costs" : SHAPE_COSTS_FORMAT
                        }
                    ]
                }
            ]
        },
        "SideUpgrades" : {
            "UpgradeCategories" : [str],
            "SideUpgrades" : [
                {
                    "Id" : str,
                    "PreviewImageId" : str,
                    "VideoId" : OptionalValueFormat(str,None),
                    "Title" : str,
                    "Description" : str,
                    "Hidden" : OptionalValueFormat(bool,False),
                    "Category" : str,
                    "RequiredUpgradeIds" : [str],
                    "RequiredMechanicIds" : [str],
                    "Rewards" : [rewardObject],
                    "Costs" : [costObject]
                }
            ]
        },
        "LinearUpgrades" : {
            "ConverterHubOutputCountUpgradeId" : OptionalValueFormat(str,None),
            "HubInputSizeUpgradeId" : str,
            "ShapeQuantityUpgradeId" : str,
            "SpeedsToLinearUpgradeMappings" : {
                "BeltSpeed" : str,
                "CutterSpeed" : str,
                "StackerSpeed" : str,
                "PainterSpeed" : str,
                "TrainSpeed" : str,
                "TrainCapacity" : str
            },
            "LinearUpgrades" : [
                {
                    "Id" : str,
                    "Title" : str,
                    "DisplayType" : RestrictedValuesFormat([1,2,3,4]),
                    "Levels" : [
                        {
                            "Value" : int,
                            "Cost" : OptionalValueFormat(costObject,None)
                        }
                    ],
                    "RequiredUpgradeIds" : [str],
                    "RequiredMechanicIds" : [str],
                    "Category" : str
                }
            ]
        },
    },
    "StartingLocation" : {
        "InitialViewport" : {
            "PositionX" : OptionalValueFormat(float,0.0),
            "PositionY" : OptionalValueFormat(float,0.0),
            "Zoom" : OptionalValueFormat(float,0.0),
            "RotationDegrees" : OptionalValueFormat(float,0.0),
            "Angle" : OptionalValueFormat(float,0.0),
            "BuildingLayer" : OptionalValueFormat(int,0),
            "IslandLayer" : OptionalValueFormat(int,0),
            "ShowAllBuildingLayers" : bool,
            "ShowAllIslandLayers" : bool
        },
        "InitialIslands" : {
            "InitialIslands" : [
                {
                    "Position_GC" : POS_FORMAT,
                    "Rotation" : OptionalValueFormat(int,0),
                    "LayoutId" : str
                }
            ]
        },
        "FixedPatches" : {
            "FixedPatches" : [
                {
                    "Shape" : str,
                    "Position_LC" : POS_FORMAT,
                    "LocalTiles" : [POS_FORMAT]
                }
            ]
        },
        "StartingChunks" : {
            "StartingChunks" : [
                {
                    "SuperChunk" : OptionalValueFormat(POS_FORMAT,{"x":0,"y":0,"z":0}),
                    "GuaranteedShapePatches" : [str],
                    "GuaranteedColorPatches" : [str]
                }
            ]
        }
    },
    "PlayerLevelConfig" : {
        "IconicLevelShapes" : {
            "LevelShapes" : [str]
        },
        "IconicLevelShapeInterval" : int,
        "GoalLines" : [
            {
                "Id" : str,
                "Randomized" : OptionalValueFormat(bool,False),
                "RandomizedUseCrystals" : OptionalValueFormat(bool,False),
                "Shape" : OptionalValueFormat(str,None),
                "StartingAmount" : int,
                "ExponentialGrowthPercentPerLevel" : int,
                "RequiredUpgradeIds" : [str],
                "RequiredMechanicIds" : [str]
            }
        ],
        "Rewards" : [
            {
                "MinimumLevel" : OptionalValueFormat(int,0),
                "Rewards" : [rewardObject]
            }
        ]
    },
    "Mechanics" : {
        "Mechanics" : [
            {
                "Id" : str,
                "Title" : str,
                "Description" : str,
                "IconId" : str
            }
        ],
        "BuildingLayerMechanicIds" : [str],
        "IslandLayerMechanicIds" : [str],
        "IslandLayersUnlockOrder" : [int],
        "BlueprintsMechanicId" : str,
        "RailsMechanicId" : str,
        "IslandManagementMechanicId" : str,
        "PlayerLevelMechanicId" : str,
        "TrainHubDeliveryMechanicId" : str
    },
    "ConvertersConfig" : {
        "Configs" : {}
    },
    "ResearchStationConfig" : {
        "Recipes" : {}
    },
    "RailColorsConfig" : {
        "RailColors" : [
            {
                "Id" : {
                    "RailColorId" : str
                },
                "Tint" : str
            }
        ]
    },
    "ToolbarConfig" : noFormatCheck
}

#endregion



#region classes

_keyMappings:dict[type,dict[str,str|list[str]]] = {}
type _jsonObj = str|int|float|bool|None|list[_jsonObj]|dict[str,_jsonObj]
type _encodeOverrideReturn = tuple[list[str],dict[str,_jsonObj]]

@dataclass
class FutureUpgrade:
    id:str

@dataclass
class UnlockRequirements:
    _rawUpgrades:list[str]
    _rawMechanics:list[str]

    def _update(
        self,
        milestones:dict[str,"Milestone"],
        upgrades:dict[str,"SideUpgrade"],
        mechanics:dict[str,"Mechanic"]
    ) -> None:
        self.requiredMilestones:list[Milestone] = []
        self.requiredSideUpgrades:list[SideUpgrade] = []
        self.requiredFutureUpgrades:list[FutureUpgrade] = []
        self.requiredMechanics:list[Mechanic] = []
        for u in self._rawUpgrades:
            if milestones.get(u) is not None:
                self.requiredMilestones.append(milestones[u])
            elif upgrades.get(u) is not None:
                self.requiredSideUpgrades.append(upgrades[u])
            else:
                self.requiredFutureUpgrades.append(FutureUpgrade(u))
        for m in self._rawMechanics:
            if mechanics.get(m) is None:
                raise ScenarioDecodeError(f"Unknown mechanic : {m}")
            self.requiredMechanics.append(mechanics[m])

@dataclass
class BlueprintCurrencyShape:
    shape:gameObjects.Shape
    requirements:UnlockRequirements
    currencyAmount:int
_keyMappings[BlueprintCurrencyShape] = {
    "shape" : "Shape",
    "currencyAmount" : "Amount"
}

@dataclass
class ResearchConfig:
    baseChunkLimitMultiplier:int
    baseBlueprintRewardMultiplier:int
    maxShapeLayers:int
    initialResearchPoints:int
    shapesConfig:gameObjects.ShapesConfiguration
    colorScheme:gameObjects.ColorScheme
    milestonesAreProgressive:bool
    blueprintCurrencyShapes:list[BlueprintCurrencyShape]
    introductionWikiEntry:str
    _rawInitiallyUnlocked:list[str]
    tutorialConfig:TutorialConfig

    def _update(
        self,
        milestones:dict[str,"Milestone"],
        upgrades:dict[str,"SideUpgrade"],
        tasks:dict[str,"SideTask"]
    ) -> None:
        self.initiallyUnlockedMilestones:list[Milestone] = []
        self.initiallyUnlockedSideUpgrades:list[SideUpgrade] = []
        self.initiallyUnlockedSideTasks:list[SideTask] = []
        for elem in self._rawInitiallyUnlocked:
            if milestones.get(elem) is not None:
                self.initiallyUnlockedMilestones.append(milestones[elem])
            elif upgrades.get(elem) is not None:
                self.initiallyUnlockedSideUpgrades.append(upgrades[elem])
            elif tasks.get(elem) is not None:
                self.initiallyUnlockedSideTasks.append(tasks[elem])
            else:
                raise ScenarioDecodeError(f"Unknown milestone/upgrade/task : {elem}")

    def _encode(self) -> _encodeOverrideReturn:
        return (
            ["_rawInitiallyUnlocked"],
            {
                "InitiallyUnlockedUpgrades" : [
                    u.id
                    for u in (
                        self.initiallyUnlockedMilestones
                        + self.initiallyUnlockedSideUpgrades
                        + self.initiallyUnlockedSideTasks
                    )
                ]
            }
        )
_keyMappings[ResearchConfig] = {
    "baseChunkLimitMultiplier" : "BaseChunkLimitMultiplier",
    "baseBlueprintRewardMultiplier" : "BaseBlueprintRewardMultiplier",
    "maxShapeLayers" : "MaxShapeLayers",
    "initialResearchPoints" : "InitialResearchPoints",
    "shapesConfig" : "ShapesConfigurationId",
    "colorScheme" : "ColorSchemeConfigurationId",
    "milestonesAreProgressive" : "ResearchLevelsAreProgressive",
    "blueprintCurrencyShapes" : "BlueprintCurrencyShapes",
    "introductionWikiEntry" : "IntroductionWikiEntryId",
    "_rawInitiallyUnlocked" : "InitiallyUnlockedUpgrades",
    "tutorialConfig" : "TutorialConfig"
}

class MilestoneShapeLineReuseType(Enum):
    nextMilestone = "nextMilestone"
    sameMilestone = "sameMilestone"
    operatorLevel = "operatorLevel"
    none = "none"

@dataclass
class ShapeCost:
    shape:gameObjects.Shape
    amount:int
_keyMappings[ShapeCost] = {
    "shape" : "Shape",
    "amount" : "Amount"
}

@dataclass
class MilestoneShapeLine:
    reuseType:MilestoneShapeLineReuseType
    reuseOffset:int
    startingOffset:int
    shapes:list[ShapeCost]

@dataclass
class Rewards:
    buildingVariants:list[buildings.BuildingVariant]
    islandGroups:list[islands.IslandGroup]
    _rawMechanics:list[str]
    wikiEntries:list[str]
    blueprintCurrency:int
    chunkLimit:int
    researchPoints:int

    def _update(self,mechanics:dict[str,"Mechanic"]) -> None:
        self.mechanics:list[Mechanic] = []
        for m in self._rawMechanics:
            if mechanics.get(m) is None:
                raise ScenarioDecodeError(f"Unknown mechanic : {m}")
            self.mechanics.append(mechanics[m])
        self.buildingInternalVariants = [
            biv
            for bv in self.buildingVariants
            for biv in bv.internalVariants
        ]
        self.islands = [i for ig in self.islandGroups for i in ig.islands]

@dataclass
class Milestone:
    id:str
    video:str
    previewImage:str
    title:translations.MaybeTranslationString
    description:translations.MaybeTranslationString
    wikiEntry:str|None
    lines:list[MilestoneShapeLine]
    rewards:Rewards
_keyMappings[Milestone] = {
    "id" : ["Definition","Id"],
    "video" : ["Definition","VideoId"],
    "previewImage" : ["Definition","PreviewImageId"],
    "title" : ["Definition","Title"],
    "description" : ["Definition","Description"],
    "wikiEntry" : ["Definition","WikiEntryId"],
    "lines" : ["Lines","Lines"],
    "rewards" : ["Rewards","Rewards"]
}

@dataclass
class SideTask:
    id:str
    isFollowupForMilestone:bool
    costs:list[ShapeCost]
    rewards:Rewards

    def _update(self,taskGroup:"TaskGroup") -> None:
        self.fromTaskGroup = taskGroup
_keyMappings[SideTask] = {
    "id" : "Id",
    "isFollowupForMilestone" : "IsFollowupForLevel",
    "costs" : "Costs",
    "rewards" : "Rewards"
}

@dataclass
class TaskGroup:
    title:translations.MaybeTranslationString
    requirements:UnlockRequirements
    tasks:list[SideTask]
_keyMappings[TaskGroup] = {
    "title" : "Title",
    "tasks" : "SideQuests"
}

@dataclass
class Cost:
    type:CostType
    amount:int
_keyMappings[Cost] = {
    "type" : "$type",
    "amount" : "Amount"
}

@dataclass
class SideUpgrade:
    id:str
    previewImage:str
    video:str|None
    title:translations.MaybeTranslationString
    description:translations.MaybeTranslationString
    hidden:bool
    category:str
    requirements:UnlockRequirements
    costs:list[Cost]
    rewards:Rewards
_keyMappings[SideUpgrade] = {
    "id" : "Id",
    "previewImage" : "PreviewImageId",
    "video" : "VideoId",
    "title" : "Title",
    "description" : "Description",
    "hidden" : "Hidden",
    "category" : "Category",
    "costs" : "Costs",
    "rewards" : "Rewards"
}

@dataclass
class LinearUpgradesMapping:
    _rawIds:list[str|None]

    def _update(self,upgrades:dict[str,"LinearUpgrade"]) -> None:
        def inner(key:int) -> LinearUpgrade:
            upgradeId = self._rawIds[key]
            if upgradeId is None:
                return None
            if upgrades.get(upgradeId) is None:
                raise ScenarioDecodeError(f"Unknown linear upgrade : {upgradeId}")
            return upgrades[upgradeId]
        self.converterHubOutputCount:LinearUpgrade|None = inner(0)
        self.hubInputSize = inner(1)
        self.shapeQuantity = inner(2)
        self.beltSpeed = inner(3)
        self.cutterSpeed = inner(4)
        self.stackerSpeed = inner(5)
        self.painterSpeed = inner(6)
        self.trainsSpeed = inner(7)
        self.trainCapacity = inner(8)

class LinearUpgradeDisplayType(Enum):
    speed = 1
    percentage = 2
    number = 3
    dividedBy100 = 4

@dataclass
class LinearUpgradeLevel:
    value:int
    cost:Cost|None
_keyMappings[LinearUpgradeLevel] = {
    "value" : "Value",
    "cost" : "Cost"
}

@dataclass
class LinearUpgrade:
    id:str
    title:translations.MaybeTranslationString
    displayType:LinearUpgradeDisplayType
    requirements:UnlockRequirements
    category:str
    levels:list[LinearUpgradeLevel]
_keyMappings[LinearUpgrade] = {
    "id" : "Id",
    "title" : "Title",
    "displayType" : "DisplayType",
    "category" : "Category",
    "levels" : "Levels"
}

@dataclass
class InitialViewportConfig:
    pos:utils.FloatPos
    zoom:float
    rotation:float
    angle:float
    buildingLayer:int
    islandLayer:int
    showAllBuildingLayers:bool
    showAllIslandLayers:bool
_keyMappings [InitialViewportConfig] = {
    "zoom" : "Zoom",
    "rotation" : "RotationDegrees",
    "angle" : "Angle",
    "buildingLayer" : "BuildingLayer",
    "islandLayer" : "IslandLayer",
    "showAllBuildingLayers" : "ShowAllBuildingLayers",
    "showAllIslandLayers" : "ShowAllIslandLayers"
}

_keyMappings[utils.Pos] = {
    "x" : "x",
    "y" : "y",
    "z" : "z"
}

@dataclass
class InitialIsland:
    pos:utils.Pos
    rotation:int
    type:islands.Island
_keyMappings[InitialIsland] = {
    "pos" : "Position_GC",
    "rotation" : "Rotation",
    "type" : "LayoutId"
}

@dataclass
class FixedPatch:
    shape:gameObjects.Shape
    pos:utils.Pos
    tiles:list[utils.Pos]
_keyMappings[FixedPatch] = {
    "shape" : "Shape",
    "pos" : "Position_LC",
    "tiles" : "LocalTiles"
}

@dataclass
class StartingChunk:
    superChunk:utils.Pos
    guaranteedShapePatches:list[gameObjects.Shape]
    guaranteedFluidPatches:list[gameObjects.Color]
_keyMappings[StartingChunk] = {
    "superChunk" : "SuperChunk",
    "guaranteedShapePatches" : "GuaranteedShapePatches",
    "guaranteedFluidPatches" : "GuaranteedColorPatches"
}

@dataclass
class StartingLocationConfig:
    initialViewport:InitialViewportConfig
    initialIslands:list[InitialIsland]
    fixedPatches:list[FixedPatch]
    startingChunks:list[StartingChunk]
_keyMappings[StartingLocationConfig] = {
    "initialViewport" : "InitialViewport",
    "initialIslands" : ["InitialIslands","InitialIslands"],
    "fixedPatches" : ["FixedPatches","FixedPatches"],
    "startingChunks" : ["StartingChunks","StartingChunks"],
}

class OperatorLevelGoalLineType(Enum):
    shape = "shape"
    randomNoCrystals = "randomNoCrystals"
    randomCrystals = "randomCrystals"

@dataclass
class OperatorLevelGoalLine:
    id:str
    type:OperatorLevelGoalLineType
    shape:gameObjects.Shape|None
    startingAmount:int
    growth:int
    requirements:UnlockRequirements
_keyMappings[OperatorLevelGoalLine] = {
    "id" : "Id",
    "shape" : "Shape",
    "startingAmount" : "StartingAmount",
    "growth" : "ExponentialGrowthPercentPerLevel"
}

@dataclass
class OperatorLevelReward:
    minLevel:int
    rewards:Rewards
_keyMappings[OperatorLevelReward] = {
    "minLevel" : "MinimumLevel",
    "rewards" : "Rewards"
}

@dataclass
class OperatorLevelConfig:
    badgeShapes:list[gameObjects.Shape]
    badgeShapeInterval:int
    goalLines:list[OperatorLevelGoalLine]
    rewards:list[OperatorLevelReward]

    def _update(self) -> None:
        self.goalLinesById = {g.id:g for g in self.goalLines}
_keyMappings[OperatorLevelConfig] = {
    "badgeShapes" : ["IconicLevelShapes","LevelShapes"],
    "badgeShapeInterval" : "IconicLevelShapeInterval",
    "goalLines" : "GoalLines",
    "rewards" : "Rewards"
}

@dataclass
class Mechanic:
    id:str
    title:translations.MaybeTranslationString
    description:translations.MaybeTranslationString
    icon:str

    def _update(self,unlockedBy:list[
        Milestone
        | SideTask
        | SideUpgrade
        | OperatorLevelReward
    ]) -> None:
        self.unlockedBy = unlockedBy
_keyMappings[Mechanic] = {
    "id" : "Id",
    "title" : "Title",
    "description" : "Description",
    "icon" : "IconId"
}

@dataclass
class MechanicsConfig:
    islandLayersUnlockOrder:list[int]
    _rawIds1:list[list[str]]
    _rawIds2:list[str]

    def _update(self,mechanics:dict[str,Mechanic]) -> None:
        def inner0(m:str) -> Mechanic:
            if mechanics.get(m) is None:
                raise ScenarioDecodeError(f"Unknown mechanic : {m}")
            return mechanics[m]
        def inner1(key:int) -> list[Mechanic]:
            return [inner0(m) for m in self._rawIds1[key]]
        def inner2(key:int) -> Mechanic:
           return inner0(self._rawIds2[key])
        self.buildingLayers = inner1(0)
        self.islandLayers = inner1(1)
        self.blueprints = inner2(0)
        self.trains = inner2(1)
        self.islandBuilding = inner2(2)
        self.operatorLevel = inner2(3)
        self.trainHubDelivery = inner2(4)

@dataclass
class Scenario:
    gameVersion:int
    id:str
    isTutorial:bool
    supportedGameModes:list[GameMode]
    nextScenarios:list[str]
    exampleShapes:list[gameObjects.Shape]
    title:translations.MaybeTranslationString
    description:translations.MaybeTranslationString
    previewImage:str
    researchConfig:ResearchConfig
    milestones:list[Milestone]
    taskGroups:list[TaskGroup]
    upgradeCategories:list[str]
    sideUpgrades:list[SideUpgrade]
    linearUpgradesMapping:LinearUpgradesMapping
    linearUpgrades:list[LinearUpgrade]
    startingLocationConfig:StartingLocationConfig
    operatorLevelConfig:OperatorLevelConfig
    mechanics:list[Mechanic]
    mechanicsConfig:MechanicsConfig
    _rawRailColorsConfig:list[dict[str,str|dict[str,str]]]

    def _update(self) -> None:
        self.railColorsConfig:dict[str,str] = {v["Id"]["RailColorId"]:v["Tint"] for v in self._rawRailColorsConfig}
        self.milestonesById = {m.id:m for m in self.milestones}
        self.sideTasksById = {t.id:t for tg in self.taskGroups for t in tg.tasks}
        self.sideUpgradesById = {u.id:u for u in self.sideUpgrades}
        self.linearUpgradesById = {u.id:u for u in self.linearUpgrades}
        self.mechanicsById = {m.id:m for m in self.mechanics}
        self.upgradesByCategory:dict[str,list[SideUpgrade|LinearUpgrade]] = {c:[] for c in self.upgradeCategories}
        for u in self.sideUpgrades+self.linearUpgrades:
            if self.upgradesByCategory.get(u.category) is not None:
                self.upgradesByCategory[u.category].append(u)

    def _encode(self) -> _encodeOverrideReturn:
        return (
            ["_rawRailColorsConfig"],
            {
                "FormatVersion" : 2,
                "ConvertersConfig" : {
                    "Configs" : {}
                },
                "ResearchStationConfig" : {
                    "Recipes" : {}
                },
                "RailColorsConfig" : {
                    "RailColors" : [
                        {
                            "Id" : {
                                "RailColorId" : id
                            },
                            "Tint" : t
                        }
                        for id,t in self.railColorsConfig.items()
                    ]
                },
                "ToolbarConfig" : "#include_raw:Scenarios/Shared/Toolbar/ToolbarConfig"
            }
        )
_keyMappings[Scenario] = {
    "gameVersion" : "GameVersion",
    "id" : "UniqueId",
    "isTutorial" : "IsTutorial",
    "supportedGameModes" : "SupportedGameModes",
    "nextScenarios" : "NextScenarios",
    "exampleShapes" : "ExampleShapes",
    "title" : "Title",
    "description" : "Description",
    "previewImage" : "PreviewImageId",
    "researchConfig" : "ResearchConfig",
    "milestones" : ["Progression","Levels","Levels"],
    "taskGroups" : ["Progression","SideQuestGroups","SideQuestGroups"],
    "upgradeCategories" : ["Progression","SideUpgrades","UpgradeCategories"],
    "sideUpgrades" : ["Progression","SideUpgrades","SideUpgrades"],
    "linearUpgradesMapping" : ["Progression","LinearUpgrades"],
    "linearUpgrades" : ["Progression","LinearUpgrades","LinearUpgrades"],
    "startingLocationConfig" : "StartingLocation",
    "operatorLevelConfig" : "PlayerLevelConfig",
    "mechanics" : ["Mechanics","Mechanics"],
    "mechanicsConfig" : "Mechanics",
    "_rawRailColorsConfig" : ["RailColorsConfig","RailColors"]
}

def _genericEq(self,other:object) -> bool:
    if not isinstance(other,type(self)):
        return NotImplemented
    return self.id == other.id
def _genericHash(self) -> int:
    return hash(self.id)
for _cls in (
    FutureUpgrade,
    Milestone,
    SideTask,
    SideUpgrade,
    LinearUpgrade,
    OperatorLevelGoalLine,
    Mechanic,
    Scenario
):
    _cls.__eq__ = _genericEq
    _cls.__hash__ = _genericHash

class ScenarioDecodeError(Exception): ...

#endregion



#region decoding

def decodeScenario(rawScenario:str) -> tuple[Scenario,list[str]]:

    warningMsgs = []
    defaultObj = object()

    def getValidObjWithFormat(obj:typing.Any,format:typing.Any) -> typing.Any:

        objType = type(obj)

        if isinstance(format,dict):

            if objType != dict:
                raise ScenarioDecodeError(f"Incorrect object type (expected 'dict' got '{objType.__name__}')")

            newObj = {}

            for formatKey,formatValue in format.items():

                objValue = obj.get(formatKey,defaultObj)

                if isinstance(formatValue,OptionalValueFormat):
                    if objValue is defaultObj:
                        newObj[formatKey] = formatValue.default
                    elif objValue == formatValue.default:
                        newObj[formatKey] = objValue
                    else:
                        newObj[formatKey] = getValidObjWithFormat(objValue,formatValue.valueFormat)
                else:
                    if objValue is defaultObj:
                        raise ScenarioDecodeError(f"Missing dict key ('{formatKey}')")
                    newObj[formatKey] = getValidObjWithFormat(objValue,formatValue)

            for key in obj.keys():
                if format.get(key) is None:
                    warningMsgs.append(f"Skipping key '{key}'")

            return newObj

        if isinstance(format,list):

            if objType != list:
                raise ScenarioDecodeError(f"Incorrect object type (expected 'list' got '{objType.__name__}')")

            newObj = []
            elemFormat = format[0]

            for objElem in obj:

                newObj.append(getValidObjWithFormat(objElem,elemFormat))

            return newObj

        if isinstance(format,RestrictedValuesFormat):

            if obj not in format.allowedValues:
                raise ScenarioDecodeError(f"'{obj}' is not part of {(
                    format.allowedValues
                    if isinstance(format.allowedValues,list) else
                    [v.value for v in format.allowedValues]
                )}")

            return obj

        if format is rewardObject:

            newObj = getValidObjWithFormat(obj,REWARD_FORMAT)

            for rewardType,rewardKey in [
                ("BuildingReward","BuildingDefinitionGroupId"),
                ("IslandGroupReward","GroupId"),
                ("MechanicReward","MechanicId"),
                ("WikiEntryReward","EntryId"),
                ("BlueprintCurrencyReward","Amount"),
                ("ChunkLimitReward","Amount"),
                ("ResearchPointsReward","Amount")
            ]:
                if (newObj["$type"] == rewardType) and (newObj[rewardKey] is None):
                    raise ScenarioDecodeError(f"Missing '{rewardKey}' key in '{rewardType}'")

            return newObj

        if format is costObject:

            newObj = getValidObjWithFormat(obj,COST_FORMAT)

            for costType,costKey in [
                ("ResearchPointsCost","Amount")
            ]:
                if (newObj["$type"] == costType) and (newObj[costKey] is None):
                    raise ScenarioDecodeError(f"Missing '{costKey}' key in '{costType}'")

            return newObj

        if format is noFormatCheck:
            return obj

        if objType != format:
            raise ScenarioDecodeError(f"Incorrect object type (expected '{format.__name__}' got '{objType.__name__}')")

        return obj

    try:
        scenarioObj = json.loads(rawScenario)
    except Exception:
        raise ScenarioDecodeError("Invalid json format")

    validScenario = getValidObjWithFormat(scenarioObj,SCENARIO_FORMAT)

    def shapesConfigFromId(id:str) -> gameObjects.ShapesConfiguration:
        return (
            ingameData.QUAD_SHAPES_CONFIG
            if id == ingameData.QUAD_SHAPES_CONFIG.id else
            ingameData.HEX_SHAPES_CONFIG
        )

    curShapesConfig = shapesConfigFromId(validScenario["ResearchConfig"]["ShapesConfigurationId"])
    toUpdateRequirements:list[UnlockRequirements] = []
    toUpdateRewards:list[Rewards] = []

    def decodeObj(rawObj:typing.Any,toClass:type[T]|types.GenericAlias|types.UnionType) -> T:

        if toClass == gameObjects.Shape:
            shapeCodeValid, errorMsg, _ = shapeCodes.isShapeCodeValid(rawObj,curShapesConfig)
            if not shapeCodeValid:
                raise ScenarioDecodeError(f"Invalid shape code : {errorMsg}")
            return gameObjects.Shape.fromShapeCode(rawObj,curShapesConfig)

        elif toClass == UnlockRequirements:
            newObj = UnlockRequirements(rawObj["RequiredUpgradeIds"],rawObj["RequiredMechanicIds"])
            toUpdateRequirements.append(newObj)
            return newObj

        elif toClass == gameObjects.ShapesConfiguration:
            return shapesConfigFromId(rawObj)

        elif toClass == gameObjects.ColorScheme:
            assert rawObj == ingameData.DEFAULT_COLOR_SCHEME.id
            return ingameData.DEFAULT_COLOR_SCHEME

        elif toClass == TutorialConfig:
            return TutorialConfig(rawObj)

        elif toClass == MilestoneShapeLine:
            if rawObj["ReusedAtNextMilestone"]:
                reuseType = MilestoneShapeLineReuseType.nextMilestone
                reuseOffset = rawObj["ReusedAtNextMilestoneOffset"]
            elif rawObj["ReusedAtSameMilestone"]:
                reuseType = MilestoneShapeLineReuseType.sameMilestone
                reuseOffset = rawObj["ReusedAtSameMilestoneOffset"]
            elif rawObj["ReusedForPlayerLevel"]:
                reuseType = MilestoneShapeLineReuseType.operatorLevel
                reuseOffset = 0
            else:
                reuseType = MilestoneShapeLineReuseType.none
                reuseOffset = 0
            return MilestoneShapeLine(
                reuseType,
                reuseOffset,
                decodeObj(rawObj["StartingOffset"],int),
                decodeObj(rawObj["Shapes"],list[ShapeCost])
            )

        elif toClass == Rewards:
            buildings_ = []
            islandGroups = []
            mechanics = []
            wikiEntries = []
            blueprintCurrency = 0
            chunkLimit = 0
            researchPoints = 0
            for r in rawObj:
                rtype = RewardType(r["$type"])
                if rtype == RewardType.BuildingReward:
                    buildingId = r["BuildingDefinitionGroupId"]
                    building = buildings.allBuildingVariants.get(buildingId)
                    if building is None:
                        raise ScenarioDecodeError(f"Unknown building : {buildingId}")
                    buildings_.append(building)
                elif rtype == RewardType.IslandGroupReward:
                    islandGroupId = r["GroupId"]
                    islandGroup = islands.allIslandGroups.get(islandGroupId)
                    if islandGroup is None:
                        raise ScenarioDecodeError(f"Unknown island group : {islandGroupId}")
                    islandGroups.append(islandGroup)
                elif rtype == RewardType.MechanicReward:
                    mechanics.append(r["MechanicId"])
                elif rtype == RewardType.WikiEntryReward:
                    wikiEntries.append(r["EntryId"])
                elif rtype == RewardType.BlueprintCurrencyReward:
                    blueprintCurrency += r["Amount"]
                elif rtype == RewardType.ChunkLimitReward:
                    chunkLimit += r["Amount"]
                elif rtype == RewardType.ResearchPointsReward:
                    researchPoints += r["Amount"]
                else:
                    assert False
            newObj = Rewards(
                buildings_,
                islandGroups,
                mechanics,
                wikiEntries,
                blueprintCurrency,
                chunkLimit,
                researchPoints
            )
            toUpdateRewards.append(newObj)
            return newObj

        elif toClass == translations.MaybeTranslationString:
            return translations.MaybeTranslationString(rawObj)

        elif toClass == CostType:
            return CostType(rawObj)

        elif toClass == LinearUpgradesMapping:
            return LinearUpgradesMapping([
                rawObj["ConverterHubOutputCountUpgradeId"],
                rawObj["HubInputSizeUpgradeId"],
                rawObj["ShapeQuantityUpgradeId"],
                rawObj["SpeedsToLinearUpgradeMappings"]["BeltSpeed"],
                rawObj["SpeedsToLinearUpgradeMappings"]["CutterSpeed"],
                rawObj["SpeedsToLinearUpgradeMappings"]["StackerSpeed"],
                rawObj["SpeedsToLinearUpgradeMappings"]["PainterSpeed"],
                rawObj["SpeedsToLinearUpgradeMappings"]["TrainSpeed"],
                rawObj["SpeedsToLinearUpgradeMappings"]["TrainCapacity"]
            ])

        elif toClass == LinearUpgradeDisplayType:
            return LinearUpgradeDisplayType(rawObj)

        elif toClass == utils.FloatPos:
            return utils.FloatPos(rawObj["PositionX"],rawObj["PositionY"])

        elif toClass == islands.Island:
            if islands.allIslands.get(rawObj) is None:
                raise ScenarioDecodeError(f"Unknown island layout : {rawObj}")
            return islands.allIslands[rawObj]

        elif toClass == gameObjects.Color:
            newObj = ingameData.DEFAULT_COLOR_SCHEME.colorsByCode.get(rawObj)
            if newObj is None:
                raise ScenarioDecodeError(f"Unknown color : {rawObj}")
            return newObj

        elif toClass == OperatorLevelGoalLineType:
            if rawObj["Randomized"]:
                if rawObj["RandomizedUseCrystals"]:
                    return OperatorLevelGoalLineType.randomCrystals
                return OperatorLevelGoalLineType.randomNoCrystals
            return OperatorLevelGoalLineType.shape

        elif toClass == MechanicsConfig:
            return MechanicsConfig(
                decodeObj(rawObj["IslandLayersUnlockOrder"],list[int]),
                [
                    rawObj["BuildingLayerMechanicIds"],
                    rawObj["IslandLayerMechanicIds"]
                ],
                [
                    rawObj["BlueprintsMechanicId"],
                    rawObj["RailsMechanicId"],
                    rawObj["IslandManagementMechanicId"],
                    rawObj["PlayerLevelMechanicId"],
                    rawObj["TrainHubDeliveryMechanicId"]
                ]
            )

        elif toClass == GameMode:
            return GameMode(rawObj)

        elif _keyMappings.get(toClass) is None:

            if isinstance(toClass,types.GenericAlias) and (toClass.__origin__ == list):
                elemType = toClass.__args__[0]
                newObj = []
                for elem in rawObj:
                    newObj.append(decodeObj(elem,elemType))
                return newObj

            elif isinstance(toClass,types.UnionType):
                assert toClass.__args__[1] == types.NoneType
                if rawObj is None:
                    return None
                return decodeObj(rawObj,toClass.__args__[0])

            assert isinstance(rawObj,(str,int,float,bool,types.NoneType,list,dict)), type(rawObj)
            return rawObj

        kwargs = {}
        for attrName,attrType in inspect.get_annotations(toClass).items():
            rawObjKey = _keyMappings[toClass].get(attrName)
            if rawObjKey is None:
                newElem = decodeObj(rawObj,attrType)
            else:
                if isinstance(rawObjKey,str):
                    rawObjKey = [rawObjKey]
                rawElem = rawObj
                for k in rawObjKey:
                    rawElem = rawElem[k]
                newElem = decodeObj(rawElem,attrType)
            kwargs[attrName] = newElem
        return toClass(**kwargs)

    decodedScenario = decodeObj(validScenario,Scenario)

    decodedScenario.operatorLevelConfig._update()
    decodedScenario._update()
    for tg in decodedScenario.taskGroups:
        for st in tg.tasks:
            st._update(tg)

    for r in toUpdateRequirements:
        r._update(
            decodedScenario.milestonesById,
            decodedScenario.sideUpgradesById,
            decodedScenario.mechanicsById
        )
    decodedScenario.researchConfig._update(
        decodedScenario.milestonesById,
        decodedScenario.sideUpgradesById,
        decodedScenario.sideTasksById
    )
    for r in toUpdateRewards:
        r._update(decodedScenario.mechanicsById)
    decodedScenario.linearUpgradesMapping._update(decodedScenario.linearUpgradesById)
    decodedScenario.mechanicsConfig._update(decodedScenario.mechanicsById)

    for m in decodedScenario.mechanics:
        m._update([
            obj
            for obj in (
                decodedScenario.milestones
                + [st for tg in decodedScenario.taskGroups for st in tg.tasks]
                + decodedScenario.sideUpgrades
                + decodedScenario.operatorLevelConfig.rewards
            )
            if m in obj.rewards.mechanics
        ])

    return decodedScenario, warningMsgs

#endregion



#region encoding

def encodeScenario(scenario:Scenario) -> str:

    @dataclass
    class MultiKeyValue:
        value:dict[str,_jsonObj]

    def customObjToJSON(obj:typing.Any,objClass:type|types.GenericAlias|types.UnionType) -> _jsonObj|MultiKeyValue:

        if isinstance(objClass,type):
            assert type(obj) == objClass, f"{type(obj)=} != {objClass=}"

        if isinstance(obj,UnlockRequirements):
            return MultiKeyValue({
                "RequiredUpgradeIds" : [r.id for r in (obj.requiredMilestones+obj.requiredSideUpgrades+obj.requiredFutureUpgrades)],
                "RequiredMechanicIds" : [m.id for m in obj.requiredMechanics]
            })

        elif isinstance(obj,gameObjects.Shape):
            return obj.toShapeCode()

        elif isinstance(obj,gameObjects.ShapesConfiguration):
            return obj.id

        elif isinstance(obj,gameObjects.ColorScheme):
            return obj.id

        elif isinstance(obj,TutorialConfig):
            return obj.value

        elif isinstance(obj,MilestoneShapeLine):
            newObj = {}
            if obj.reuseType == MilestoneShapeLineReuseType.nextMilestone:
                newObj["ReusedAtNextMilestone"] = True
                newObj["ReusedAtNextMilestoneOffset"] = obj.reuseOffset
            elif obj.reuseType == MilestoneShapeLineReuseType.sameMilestone:
                newObj["ReusedAtSameMilestone"] = True
                newObj["ReusedAtSameMilestoneOffset"] = obj.reuseOffset
            elif obj.reuseType == MilestoneShapeLineReuseType.operatorLevel:
                newObj["ReusedForPlayerLevel"] = True
            newObj["StartingOffset"] = customObjToJSON(obj.startingOffset,int)
            newObj["Shapes"] = customObjToJSON(obj.shapes,list[ShapeCost])
            return newObj

        elif isinstance(obj,Rewards):
            newObj = []
            for bv in obj.buildingVariants:
                newObj.append({
                    "$type" : RewardType.BuildingReward.value,
                    "BuildingDefinitionGroupId" : bv.id
                })
            for ig in obj.islandGroups:
                newObj.append({
                    "$type" : RewardType.IslandGroupReward.value,
                    "GroupId" : ig.id
                })
            for m in obj.mechanics:
                newObj.append({
                    "$type" : RewardType.MechanicReward.value,
                    "MechanicId" : m.id
                })
            for we in obj.wikiEntries:
                newObj.append({
                    "$type" : RewardType.WikiEntryReward.value,
                    "EntryId" : we
                })
            for val,valType in [
                (obj.blueprintCurrency,RewardType.BlueprintCurrencyReward),
                (obj.chunkLimit,RewardType.ChunkLimitReward),
                (obj.researchPoints,RewardType.ResearchPointsReward)
            ]:
                if val != 0:
                    newObj.append({
                        "$type" : valType.value,
                        "Amount" : val
                    })
            return newObj

        elif isinstance(obj,translations.MaybeTranslationString):
            return obj.getRaw()

        elif isinstance(obj,CostType):
            return obj.value

        elif isinstance(obj,LinearUpgradesMapping):
            return {
                "ConverterHubOutputCountUpgradeId" : (
                    None
                    if obj.converterHubOutputCount is None else
                    obj.converterHubOutputCount.id
                ),
                "HubInputSizeUpgradeId" : obj.hubInputSize.id,
                "ShapeQuantityUpgradeId" : obj.shapeQuantity.id,
                "SpeedsToLinearUpgradeMappings" : {
                    "BeltSpeed" : obj.beltSpeed.id,
                    "CutterSpeed" : obj.cutterSpeed.id,
                    "StackerSpeed" : obj.stackerSpeed.id,
                    "PainterSpeed" : obj.painterSpeed.id,
                    "TrainSpeed" : obj.trainsSpeed.id,
                    "TrainCapacity" : obj.trainCapacity.id
                }
            }

        elif isinstance(obj,LinearUpgradeDisplayType):
            return obj.value

        elif isinstance(obj,utils.FloatPos):
            return MultiKeyValue({
                "PositionX" : obj.x,
                "PositionY" : obj.y
            })

        elif isinstance(obj,islands.Island):
            return obj.id

        elif isinstance(obj,gameObjects.Color):
            return obj.code

        elif isinstance(obj,OperatorLevelGoalLineType):
            if obj == OperatorLevelGoalLineType.randomCrystals:
                return MultiKeyValue({
                    "Randomized" : True,
                    "RandomizedUseCrystals" : True
                })
            if obj == OperatorLevelGoalLineType.randomNoCrystals:
                return MultiKeyValue({
                    "Randomized" : True
                })
            return MultiKeyValue({})

        elif isinstance(obj,MechanicsConfig):
            return {
                "BuildingLayerMechanicIds" : [m.id for m in obj.buildingLayers],
                "IslandLayerMechanicIds" : [m.id for m in obj.islandLayers],
                "IslandLayersUnlockOrder" : obj.islandLayersUnlockOrder,
                "BlueprintsMechanicId" : obj.blueprints.id,
                "RailsMechanicId" : obj.trains.id,
                "IslandManagementMechanicId" : obj.islandBuilding.id,
                "PlayerLevelMechanicId" : obj.operatorLevel.id,
                "TrainHubDeliveryMechanicId" : obj.trainHubDelivery.id
            }

        elif isinstance(obj,GameMode):
            return obj.value

        elif _keyMappings.get(objClass) is None:

            if isinstance(objClass,types.GenericAlias) and (objClass.__origin__ == list):
                elemType = objClass.__args__[0]
                newObj = []
                for elem in obj:
                    newElem = customObjToJSON(elem,elemType)
                    assert not isinstance(newElem,MultiKeyValue)
                    newObj.append(newElem)
                return newObj

            elif isinstance(objClass,types.UnionType):
                assert objClass.__args__[1] == types.NoneType
                if obj is None:
                    return None
                return customObjToJSON(obj,objClass.__args__[0])

            assert isinstance(obj,(str,int,float,bool,types.NoneType,list,dict)), type(obj)
            return obj

        if hasattr(obj,"_encode"):
            encodeBase:_encodeOverrideReturn = obj._encode()
            skipAttrs, newObj = encodeBase
        else:
            skipAttrs = []
            newObj = {}

        for attrName,attrType in inspect.get_annotations(objClass).items():
            if attrName in skipAttrs:
                continue
            attrValue = getattr(obj,attrName)
            encodeToKey = _keyMappings[objClass].get(attrName)
            if encodeToKey is None:
                addValues = customObjToJSON(attrValue,attrType)
                assert isinstance(addValues,MultiKeyValue)
                newObj.update(addValues.value)
            else:
                if isinstance(encodeToKey,str):
                    encodeToKey = [encodeToKey]
                encodeInObj = newObj
                for k in encodeToKey[:-1]:
                    if encodeInObj.get(k) is None:
                        encodeInObj[k] = {}
                    encodeInObj = encodeInObj[k]
                encodeInKey = encodeToKey[-1]
                newElem = customObjToJSON(attrValue,attrType)
                assert not isinstance(newElem,MultiKeyValue)
                if encodeInObj.get(encodeInKey) is None:
                    encodeInObj[encodeInKey] = newElem
                else:
                    assert isinstance(encodeInObj[encodeInKey],dict)
                    assert isinstance(newElem,dict)
                    encodeInObj[encodeInKey].update(newElem)

        return newObj

    encodedScenario = customObjToJSON(scenario,Scenario)

    defaultObj = object()

    def encodeObjWithFormat(obj:typing.Any,format:typing.Any) -> typing.Any:

        if isinstance(format,dict):

            newObj = {}

            for formatKey,formatValue in format.items():

                objValue = obj.get(formatKey,defaultObj)

                if isinstance(formatValue,OptionalValueFormat):
                    if (objValue == formatValue.default) or (objValue is defaultObj):
                        continue
                    newObj[formatKey] = encodeObjWithFormat(objValue,formatValue.valueFormat)
                else:
                    newObj[formatKey] = encodeObjWithFormat(objValue,formatValue)

            return newObj

        if isinstance(format,list):

            newObj = []

            for objElem in obj:

                newObj.append(encodeObjWithFormat(objElem,format[0]))

            return newObj

        if format is rewardObject:
            return encodeObjWithFormat(obj,REWARD_FORMAT)

        if format is costObject:
            return encodeObjWithFormat(obj,COST_FORMAT)

        return obj

    formattedScenario = encodeObjWithFormat(encodedScenario,SCENARIO_FORMAT)

    return json.dumps(
        formattedScenario,
        ensure_ascii=True,
        indent=4
    )

#endregion



def _loadGameScenarios() -> dict[str,Scenario]:
    scenarios = {}
    for id in SCENARIO_IDS:
        with (
            importlib.resources.files(__package__)
            .joinpath(SCENARIOS_PATH.format(id=id))
            .open(encoding="utf-8")
        ) as f:
            s,w = decodeScenario(f.read())
        if len(w) > 0:
            print(f"Scenario load warning : {s.id} : {w}")
        scenarios[s.id] = s
    return scenarios

ingameScenarios = _loadGameScenarios()