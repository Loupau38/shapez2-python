from . import gameObjects

def _createDefaultColorScheme() -> gameObjects.ColorScheme:

    baseColors:dict[str,tuple[int,int,int]] = {
        "u" : (164,158,165),
        "r" : (255,0,0),
        "g" : (0,255,0),
        "b" : (0,0,255),
        "c" : (0,255,255),
        "m" : (255,0,255),
        "y" : (255,255,0),
        "w" : (255,255,255),
        "k" : (86,77,78),
        "p" : (167,41,207),
        "o" : (213,133,13)
    }

    defaultColors = {c:gameObjects.Color(c) for c in "urgbcmyw"}

    rawColorSkins = {
        "RGB" : {
            "u" : baseColors["u"],
            "r" : baseColors["r"],
            "g" : baseColors["g"],
            "b" : baseColors["b"],
            "c" : baseColors["c"],
            "m" : baseColors["m"],
            "y" : baseColors["y"],
            "w" : baseColors["w"]
        },
        "RYB" : {
            "u" : baseColors["u"],
            "r" : baseColors["r"],
            "g" : baseColors["y"],
            "b" : baseColors["b"],
            "c" : baseColors["g"],
            "m" : baseColors["p"],
            "y" : baseColors["o"],
            "w" : baseColors["k"]
        },
        "CMYK" : {
            "u" : baseColors["u"],
            "r" : baseColors["c"],
            "g" : baseColors["m"],
            "b" : baseColors["y"],
            "c" : baseColors["r"],
            "m" : baseColors["g"],
            "y" : baseColors["b"],
            "w" : baseColors["k"]
        }
    }

    colorSkins = {
        name : gameObjects.ColorSkin(name,{
            defaultColors[cn] : cv
            for cn,cv in values.items()
        })
        for name,values in rawColorSkins.items()
    }

    secondaryColorRecipes = {
        defaultColors["c"] : (defaultColors["g"],defaultColors["b"]),
        defaultColors["m"] : (defaultColors["r"],defaultColors["b"]),
        defaultColors["y"] : (defaultColors["r"],defaultColors["g"])
    }
    primaries = [defaultColors[c] for c in "rgb"]

    mixingRecipes = {}

    for r,(i1,i2) in secondaryColorRecipes.items():
        mixingRecipes[frozenset((i1,i2))] = r
        notI = [p for p in primaries if p not in (i1,i2)][0]
        mixingRecipes[frozenset((r,notI))] = defaultColors["w"]
        mixingRecipes[frozenset((r,i1))] = i1
        mixingRecipes[frozenset((r,i2))] = i2

    for p in primaries:
        sec = [r for r,i in secondaryColorRecipes.items() if p in i]
        mixingRecipes[frozenset(sec)] = p

    for c in defaultColors.values():
        mixingRecipes[frozenset((c,c))] = c
        mixingRecipes[frozenset((defaultColors["w"],c))] = c
        mixingRecipes[frozenset((defaultColors["u"],c))] = c

    return gameObjects.ColorScheme(
        "DefaultColorSchemeRGBFlex",
        [
            defaultColors["r"],
            defaultColors["g"],
            defaultColors["b"]
        ],
        [
            defaultColors["c"],
            defaultColors["m"],
            defaultColors["y"]
        ],
        [
            defaultColors["w"]
        ],
        defaultColors["u"],
        [
            gameObjects.ColorMode("RGB",colorSkins["RGB"],False),
            gameObjects.ColorMode("RYB",colorSkins["RYB"],False),
            gameObjects.ColorMode("CMYK",colorSkins["CMYK"],False),
            gameObjects.ColorMode("RGB-cb",colorSkins["RGB"],True),
        ],
        mixingRecipes
    )

DEFAULT_COLOR_SCHEME = _createDefaultColorScheme()

_PIN_PART = gameObjects.ShapePartType("P",False,False,False,replacedByCrystal=True)
_CRYSTAL_PART = gameObjects.ShapePartType("c",canChangeColor=False,crystalBehavior=True)

QUAD_SHAPES_CONFIG = gameObjects.ShapesConfiguration(
    "DefaultShapesQuadConfiguration",
    4,
    _PIN_PART,
    _CRYSTAL_PART,
    [
        (gameObjects.ShapePartType("C"),0),
        (gameObjects.ShapePartType("R"),0),
        (gameObjects.ShapePartType("S"),1),
        (gameObjects.ShapePartType("W"),2),
        (_PIN_PART,3),
        (_CRYSTAL_PART,3)
    ]
)
HEX_SHAPES_CONFIG = gameObjects.ShapesConfiguration(
    "DefaultShapesHexagonalConfiguration",
    6,
    _PIN_PART,
    _CRYSTAL_PART,
    [
        (gameObjects.ShapePartType("H"),0),
        (gameObjects.ShapePartType("G"),1),
        (gameObjects.ShapePartType("F"),2),
        (_PIN_PART,3),
        (_CRYSTAL_PART,3)
    ]
)