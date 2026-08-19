from . import utils, translations

import json
import importlib.resources
import enum

class BuildingVariant(utils.HasUniqueID):

    def __init__(self,id:str,title:translations.MaybeTranslationString) -> None:
        self.id = id
        self.title = title
        self.internalVariants:list[BuildingInternalVariant] = []

class BuildingInternalVariant(utils.HasUniqueID):

    def __init__(self,id:str,tiles:list[utils.TileVector],fromBuildingVariant:BuildingVariant) -> None:
        self.id = id
        self.tiles = tiles
        self.fromBuildingVariant = fromBuildingVariant

def _loadBuildings() -> tuple[dict[str,BuildingVariant],dict[str,BuildingInternalVariant]]:

    with importlib.resources.files(__package__).joinpath("gameFiles/buildings.json").open(encoding="utf-8") as f:
        buildingsRaw = json.load(f)

    allVariants = {}
    allInternalVariants = {}

    for variantRaw in buildingsRaw["Buildings"]:
        curVariantTitle = f"@building-variant.{variantRaw["Id"]}.title"
        curVariant = BuildingVariant(
            variantRaw["Id"],
            translations.MaybeTranslationString(curVariantTitle)
        )
        allVariants[curVariant.id] = curVariant
        for InternalVariantRaw in variantRaw["InternalVariants"]:
            curInternalVariant = BuildingInternalVariant(
                InternalVariantRaw["Id"],
                [
                    utils.TileVector(tile["X"],tile["Y"],tile["Z"])
                    for tile in InternalVariantRaw["Tiles"]
                ],
                curVariant
            )
            allInternalVariants[curInternalVariant.id] = curInternalVariant
            curVariant.internalVariants.append(curInternalVariant)

    return allVariants, allInternalVariants

allBuildingVariants, allBuildingInternalVariants = _loadBuildings()

def getCategorizedBuildingCounts(
    counts:dict[BuildingInternalVariant,int]
) -> dict[BuildingVariant,dict[BuildingInternalVariant,int]]:

    variants = {}
    for biv,c in counts.items():
        curVariant = biv.fromBuildingVariant
        if variants.get(curVariant) is None:
            variants[curVariant] = {}
        variants[curVariant][biv] = c

    return variants

# use variables instead of string literals and make potential ID changes not go unnoticed at the same time
# note : when changing an ID, make sure the migration functions still work as intended
_b = allBuildingInternalVariants
class BuildingIds(enum.StrEnum):
    label = _b["LabelDefaultInternalVariant"].id
    signalProducer = _b["ConstantSignalDefaultInternalVariant"].id
    itemProducer = _b["SandboxItemProducerDefaultInternalVariant"].id
    fluidProducer = _b["SandboxFluidProducerDefaultInternalVariant"].id
    button = _b["ButtonDefaultInternalVariant"].id
    compareGate = _b["LogicGateCompareInternalVariant"].id
    compareGateMirrored = _b["LogicGateCompareInternalVariantMirrored"].id
    globalSignalSender = _b["ControlledSignalTransmitterInternalVariant"].id
    globalSignalReceiver = _b["ControlledSignalReceiverInternalVariant"].id
    globalSignalReceiverMirrored = _b["ControlledSignalReceiverInternalVariantMirrored"].id
    operatorSignalRceiver = _b["WireGlobalTransmitterReceiverInternalVariant"].id
    beltTMerger = _b["MergerTShapeInternalVariant"].id
    painter = _b["PainterDefaultInternalVariant"].id
    painterMirrored = _b["PainterDefaultInternalVariantMirrored"].id
    crystalGenerator = _b["CrystalGeneratorDefaultInternalVariant"].id
    crystalGeneratorMirrored = _b["CrystalGeneratorDefaultInternalVariantMirrored"].id
del _b