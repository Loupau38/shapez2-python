import json
import os
import sys
import shutil

GAME_VERSION = 1138
BASE_PATH = os.environ["shapez2_assets_path"] + "/"
EXTRACTED_BASE_PATH = "./shapez2/gameFiles/"

BUILDINGS_PATH = BASE_PATH + "misc/buildings.json"
ISLANDS_PATH = BASE_PATH + "misc/islands.json"
NON_BUILDABLE_ISLANDS_PATH = EXTRACTED_BASE_PATH + "nonBuildableIslands.json"
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
    with open(ISLANDS_PATH,encoding="utf-8") as f:
        islandsRaw = json.load(f)
    with open(NON_BUILDABLE_ISLANDS_PATH,encoding="utf-8") as f:
        nonBuildableIslands = json.load(f)

    for island in islandsRaw["Islands"]:
        for chunk in island["Chunks"]:
            if island["Id"] in nonBuildableIslands:
                chunk["BuildableTiles"] = []
                continue
            curRanges = []
            curRangeStart = None
            prevTile = None
            curStep = None
            rawTiles = chunk["BuildableTiles"]
            for tile in rawTiles:
                if prevTile is None:
                    curRangeStart = tile
                    prevTile = tile
                    continue
                if curStep is None:
                    curStep = tile - prevTile
                    prevTile = tile
                    continue
                if tile-prevTile == curStep:
                    prevTile = tile
                    continue
                curRanges.append((curRangeStart,prevTile,curStep))
                curRangeStart = tile
                prevTile = tile
                curStep = None
            if curStep is not None:
                curRanges.append((curRangeStart,tile,curStep))
            elif prevTile is not None:
                assert curRangeStart == tile
                curRanges.append((curRangeStart,tile,1))
            if sum((list(range(r[0],r[1]+1,r[2])) for r in curRanges),start=[]) != rawTiles:
                print("Generated buildable tiles don't match raw :")
                print(f"Raw : {",".join(str(t) for t in rawTiles)}")
                print(f"Generated : {curRanges}")
                raise Exception
            chunk["BuildableTiles"] = [list(r) for r in curRanges]

    with open(EXTRACTED_ISLANDS_PATH,"w",encoding="utf-8") as f:
        json.dump(islandsRaw,f,ensure_ascii=False,indent=4)



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