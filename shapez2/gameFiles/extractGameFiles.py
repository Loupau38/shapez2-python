import json
import os
import sys
import shutil

GAME_VERSION = 1138
BASE_PATH = os.environ["shapez2_assets_path"] + "/"
EXTRACTED_BASE_PATH = "./shapez2/gameFiles/"

BUILDINGS_PATH = BASE_PATH + "misc/buildings.json"
ISLANDS_PATH = BASE_PATH + "misc/islands.json"
TRANSLATIONS_PATH = BASE_PATH + "misc/translations-en-US.json"
IDENTIFIERS_PATH = BASE_PATH + "misc/identifiers.json"
SCENARIOS_PATH = BASE_PATH + "scenarios/"

EXTRACTED_BUILDINGS_PATH = EXTRACTED_BASE_PATH + "buildings.json"
EXTRACTED_ISLANDS_PATH = EXTRACTED_BASE_PATH + "islands.json"
EXTRACTED_TRANSLATIONS_PATH = EXTRACTED_BASE_PATH + "translations-en-US.json"
EXTRACTED_ICONS_PATH = EXTRACTED_BASE_PATH + "icons.json"
EXTRACTED_SCENARIOS_PATH = EXTRACTED_BASE_PATH + "scenarios/"

def extractKeys(fromDict:dict,toDict:dict,keys:list[str]) -> dict:
    for key in keys:
        toDict[key] = fromDict[key]
    return toDict

def main() -> None:

    if os.getcwd().split("\\")[-1] != "s2 py package":
        print("Must be executed from 's2 py package' directory")
        input()
        sys.exit()

    # scenarios

    for dirEntry in os.scandir(SCENARIOS_PATH):
        if dirEntry.is_file():
            shutil.copy(dirEntry.path,EXTRACTED_SCENARIOS_PATH)



    # buildings

    with open(BUILDINGS_PATH,encoding="utf-8") as f:
        buildingsRaw = json.load(f)

    extractedBuildings:dict[str,list] = {"Buildings":[]}
    for internalVariantListRaw in buildingsRaw:
        extractedInternalVariantList = extractKeys(internalVariantListRaw,{},["Id"])
        extractedInternalVariantList["InternalVariants"] = []
        for buildingRaw in internalVariantListRaw["InternalVariants"]:
            extractedBuilding = extractKeys(buildingRaw,{},["Id","Tiles"])
            extractedInternalVariantList["InternalVariants"].append(extractedBuilding)
        extractedBuildings["Buildings"].append(extractedInternalVariantList)

    with open(EXTRACTED_BUILDINGS_PATH,"w",encoding="utf-8") as f:
        json.dump(extractedBuildings,f,indent=4,ensure_ascii=True)



    # islands
    shutil.copy(ISLANDS_PATH,EXTRACTED_ISLANDS_PATH)



    # translations
    with open(TRANSLATIONS_PATH,encoding="utf-8") as f:
        translationsRaw = json.load(f)
    with open(EXTRACTED_TRANSLATIONS_PATH,"w",encoding="utf-8") as f:
        json.dump({
            "Translations" : translationsRaw["Entries"]
        },f,ensure_ascii=False,indent=4)



    # icons
    with open(IDENTIFIERS_PATH,encoding="utf-8") as f:
        identifiersRaw = json.load(f)
    with open(EXTRACTED_ICONS_PATH,"w",encoding="utf-8") as f:
        json.dump({
            "Icons" : identifiersRaw["IconIds"]
        },f,ensure_ascii=False,indent=4)



if __name__ == "__main__":
    main()