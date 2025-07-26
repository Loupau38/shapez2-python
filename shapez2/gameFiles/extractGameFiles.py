import json
import os

GAME_VERSION = 1122
BASE_PATH = os.path.expandvars(f"%LOCALAPPDATA%low\\tobspr Games\\shapez 2\\basedata-v{GAME_VERSION}\\")

BUILDINGS_PATH = BASE_PATH + "buildings.json"
ADDITIONAL_BUILDINGS_PATH = "./shapez2/gameFiles/additionalBuildings.json"
TRANSLATIONS_PATH = BASE_PATH + "translations-en-US.json"
IDENTIFIERS_PATH = BASE_PATH + "identifiers.json"
SCENARIOS_PATH = BASE_PATH + "scenarios\\"

EXTRACTED_BUILDINGS_PATH = "./shapez2/gameFiles/buildings.json"
EXTRACTED_ISLANDS_PATH = "./shapez2/gameFiles/islands.json"
EXTRACTED_TRANSLATIONS_PATH = "./shapez2/gameFiles/translations-en-US.json"
EXTRACTED_ICONS_PATH = "./shapez2/gameFiles/icons.json"
EXTRACTED_SCENARIOS_PATH = "./shapez2/gameFiles/"

def extractKeys(fromDict:dict,toDict:dict,keys:list[str]) -> dict:
    for key in keys:
        toDict[key] = fromDict[key]
    return toDict

def main() -> None:

    if os.getcwd().split("\\")[-1] != "s2 py package":
        print("Must be executed from 's2 py package' directory")
        input()
        exit()

    # research

    scenariosRaw = []
    for dirEntry in os.scandir(SCENARIOS_PATH):
        if dirEntry.is_file():
            with open(dirEntry.path,encoding="utf-8") as f:
                scenariosRaw.append((dirEntry.name,json.load(f)))

    for name,scenario in scenariosRaw:
        with open(EXTRACTED_SCENARIOS_PATH+name,"w",encoding="utf-8") as f:
            json.dump(scenario,f,indent=4,ensure_ascii=True)



    # buildings

    with open(BUILDINGS_PATH,encoding="utf-8") as f:
        buildingsRaw = json.load(f)
    with open(ADDITIONAL_BUILDINGS_PATH,encoding="utf-8") as f:
        additionalBuildings = json.load(f)

    toRemoveBuildings = []
    for ab in additionalBuildings:
        if ab["Id"] in (b["Id"] for b in buildingsRaw):
            toRemoveBuildings.append(ab["Id"])
        else:
            print(f"Additonal building {ab['Id']} not in base buildings")

    buildingsRaw = [b for b in buildingsRaw if b["Id"] not in toRemoveBuildings]
    extractedBuildings:dict[str,str|list] = {"GameVersion":GAME_VERSION,"Buildings":[]}
    for internalVariantListRaw in additionalBuildings+buildingsRaw:
        curInternalVariantListKeys = ["Id"]
        if internalVariantListRaw.get("Title") is not None:
            curInternalVariantListKeys.append("Title")
        extractedInternalVariantList = extractKeys(internalVariantListRaw,{},curInternalVariantListKeys)
        extractedInternalVariantList["InternalVariants"] = []
        for buildingRaw in internalVariantListRaw["InternalVariants"]:
            extractedBuilding = extractKeys(buildingRaw,{},["Id","Tiles"])
            extractedInternalVariantList["InternalVariants"].append(extractedBuilding)
        extractedBuildings["Buildings"].append(extractedInternalVariantList)
    extractedBuildings["Buildings"] = sorted(extractedBuildings["Buildings"],key=lambda b: b["Id"])

    with open(EXTRACTED_BUILDINGS_PATH,"w",encoding="utf-8") as f:
        json.dump(extractedBuildings,f,indent=4,ensure_ascii=True)



    # islands
    with open(EXTRACTED_ISLANDS_PATH,encoding="utf-8") as f:
        islandsRaw = json.load(f)
    islandsRaw["GameVersion"] = GAME_VERSION
    print("Check if islands have changed and remember to use /blueprint-creator all-buildings and all-islands")
    with open(EXTRACTED_ISLANDS_PATH,"w",encoding="utf-8") as f:
        json.dump(islandsRaw,f,indent=4,ensure_ascii=True)



    # translations
    with open(TRANSLATIONS_PATH,encoding="utf-8") as f:
        translationsRaw = json.load(f)
    with open(EXTRACTED_TRANSLATIONS_PATH,"w",encoding="utf-8") as f:
        json.dump({
            "GameVersion" : GAME_VERSION,
            "Translations" : translationsRaw["Entries"]
        },f,ensure_ascii=False,indent=4)



    # icons
    with open(IDENTIFIERS_PATH,encoding="utf-8") as f:
        identifiersRaw = json.load(f)
    with open(EXTRACTED_ICONS_PATH,"w",encoding="utf-8") as f:
        json.dump({
            "GameVersion" : GAME_VERSION,
            "Icons":sorted(identifiersRaw["IconIds"])
        },f,ensure_ascii=False,indent=4)



if __name__ == "__main__":
    main()