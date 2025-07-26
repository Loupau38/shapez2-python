from . import pygamePIL

import json
import typing
import importlib.resources
import enum
from dataclasses import dataclass

_T = typing.TypeVar("_T")

TAG_GL_COLOR = (216,121,62)
TAG_GL_BG_COLOR = (0,0,0,85)
TAG_LINK_COLOR = (28,194,255)

class TagType(enum.Enum):
    single = "single"
    start = "start"
    end = "end"

class ValueSep(enum.Enum):
    colon = ":"
    equals = "="

@dataclass
class FeatureTag:
    type:TagType
    feature:str
    value:str|None=None
    valueSep:ValueSep|None=None

    def toString(self) -> str:
        returnString = "<"
        if self.type == TagType.end:
            returnString += "/"
        returnString += self.feature
        if self.value is not None:
            if self.valueSep == ValueSep.colon:
                returnString += ":"
            else:
                returnString += '="'
            returnString += self.value
            if self.valueSep == ValueSep.equals:
                returnString += '"'
        if self.type == TagType.single:
            returnString += "/"
        returnString += ">"
        return returnString

def _sanitizeComponents(components:list[str|FeatureTag]) -> list[str|FeatureTag]:
    components = [c for c in components if c != ""]
    new = []
    for c in components:
        if (new != []) and isinstance(c,str) and isinstance(new[-1],str):
            new[-1] += c
        else:
            new.append(c)
    return new

class FeatureString:

    def __init__(self,components:list[str|FeatureTag]) -> None:
        self.components = _sanitizeComponents(components)

    def replaceParams(self,params:dict[str,str],default:str|None=None) -> "FeatureString":
        newComponents:list[str|FeatureTag] = []
        for comp in self.components:
            if isinstance(comp,str) or (comp.type != TagType.single):
                newComponents.append(comp)
                continue
            if params.get(comp.feature) is None:
                if default is None:
                    raise ValueError(f"Parameter '{comp.feature}' doesn't have a value assigned")
                newValue = default
            else:
                newValue = params[comp.feature]
            newComponents.append(newValue)
        return FeatureString(newComponents)

    def renderToRawString(self) -> str:
        return "".join(c.toString() if isinstance(c,FeatureTag) else c for c in self.components)

    def renderToStringNoFeatures(self) -> str:
        return "".join(c for c in self.components if isinstance(c,str))

    def renderToSurface(self,font:pygamePIL.font_Font,boldFont:pygamePIL.font_Font) -> pygamePIL.Surface:

        TEXT_COLOR = (255,255,255)

        def removeFromEnd(list:list[_T],value:_T) -> None:
            for i in reversed(range(len(list))):
                if list[i] == value:
                    list.pop(i)
                    return

        def colorHexToRGB(color:str) -> tuple[int,int,int]|None:
            if not color.startswith("#"):
                return None
            color = color.removeprefix("#")
            if len(color) != 6:
                return None
            for c in color:
                if c not in "0123456789abcdefABCDEF":
                    return None
            return tuple(int(color[i*2:(i+1)*2],16) for i in range(3))

        rawFeaturesStack:list[tuple[str,str|None]] = []
        renderedText:list[list[pygamePIL.Surface]] = [[]]

        for component in self.components:

            if isinstance(component,FeatureTag):
                if component.type in (TagType.start,TagType.end):
                    if component.type == TagType.start:
                        func = rawFeaturesStack.append
                    else:
                        func = lambda v: removeFromEnd(rawFeaturesStack,v)
                    if component.feature == "b":
                        func(("bold",None))
                    elif component.feature == "u":
                        func(("underline",None))
                    elif component.feature == "gl":
                        func(("glow",None))
                    elif component.feature == "link":
                        func(("link",None))
                    elif (
                        (component.feature == "color")
                        and (component.value is not None)
                        and (component.valueSep == ValueSep.equals)
                    ):
                        func(("color",component.value))
                continue

            calculatedFeatures = {
                "bold" : False,
                "underline" : False,
                "color" : TEXT_COLOR,
                "background" : None
            }

            for rawFeature in rawFeaturesStack:
                if rawFeature[0] == "bold":
                    calculatedFeatures["bold"] = True
                elif rawFeature[0] == "underline":
                    calculatedFeatures["underline"] = True
                elif rawFeature[0] == "glow":
                    calculatedFeatures["color"] = TAG_GL_COLOR
                    calculatedFeatures["background"] = TAG_GL_BG_COLOR
                    calculatedFeatures["bold"] = True
                elif rawFeature[0] == "link":
                    calculatedFeatures["color"] = TAG_LINK_COLOR
                    calculatedFeatures["underline"] = True
                elif rawFeature[0] == "color":
                    color = colorHexToRGB(rawFeature[1])
                    if color is not None:
                        calculatedFeatures["color"] = color

            firstLine, *otherLines = component.split("\n")

            def renderText(text:str) -> pygamePIL.Surface:
                usedFont = boldFont if calculatedFeatures["bold"] else font
                usedFont.underline = calculatedFeatures["underline"]
                return usedFont.render(
                    text,
                    1,
                    calculatedFeatures["color"],
                    calculatedFeatures["background"]
                )

            renderedText[-1].append(renderText(firstLine))
            for l in otherLines:
                renderedText.append([renderText(l)])

        renderedLines:list[pygamePIL.Surface] = []
        for line in renderedText:
            lineWidth = sum(t.get_width() for t in line)
            lineHeight = max(t.get_height() for t in line)
            lineSurf = pygamePIL.Surface((lineWidth,lineHeight),pygamePIL.SRCALPHA)
            curX = 0
            for text in line:
                lineSurf.blit(text,(curX,0))
                curX += text.get_width()
            renderedLines.append(lineSurf)

        finalWidth = max(l.get_width() for l in renderedLines)
        finalHeight = sum(l.get_height() for l in renderedLines)
        finalSurf = pygamePIL.Surface((finalWidth,finalHeight),pygamePIL.SRCALPHA)
        curY = 0
        for line in renderedLines:
            finalSurf.blit(line,(0,curY))
            curY += line.get_height()

        return finalSurf

class Language(enum.Enum):
    en_US = "en-US"
FALLBACK_LANGUAGE = Language.en_US

@dataclass
class TranslationString:
    key:str

    def translate(self,language:Language=FALLBACK_LANGUAGE) -> FeatureString:
        if _translations[language].get(self.key) is not None:
            return _translations[language][self.key]
        if _translations[FALLBACK_LANGUAGE].get(self.key) is not None:
            return _translations[FALLBACK_LANGUAGE][self.key]
        return FeatureString([self.key])

class MaybeTranslationString(TranslationString):

    def __init__(self,key:str) -> None:
        self.key:str|None
        if key.startswith("@"):
            super().__init__(key.removeprefix("@"))
            self.rawString = None
        else:
            self.key = None
            self.rawString = key

    def translate(self,language:Language=FALLBACK_LANGUAGE) -> FeatureString:
        if self.rawString is None:
            return super().translate(language)
        return featureStringFromRaw(self.rawString)

    def getRaw(self) -> str:
        if self.key is None:
            return self.rawString
        return f"@{self.key}"

def _loadRawTranslations() -> dict[Language,dict[str,str]]:
    raw = {}
    for l in Language:
        with (
            importlib.resources.files(__package__)
            .joinpath(f"gameFiles/translations-{l.value}.json")
            .open(encoding="utf-8")
        ) as f:
            raw[l] = json.load(f)["Translations"]
    return raw
_rawTranslations = _loadRawTranslations()

def getRawTranslation(key:str,language:Language=FALLBACK_LANGUAGE) -> str:
    if _rawTranslations[language].get(key) is not None:
        return _rawTranslations[language][key]
    if _rawTranslations[FALLBACK_LANGUAGE].get(key) is not None:
        return _rawTranslations[FALLBACK_LANGUAGE][key]
    return key

_translations:dict[Language,dict[str,FeatureString]] = {}

def _decodeRawString(raw:str,language:Language|None) -> FeatureString:

    components:list[str|FeatureTag] = []
    openingSplits = raw.split("<")
    components.append(openingSplits[0])

    for split in openingSplits[1:]:

        if split.count(">") == 0:
            components.append("<"+split)
            continue

        tag, *leftover = split.split(">")
        text = ">".join(leftover)

        if tag == "":
            components.append("<>"+text)
            continue

        if tag.startswith("/"):
            tagType = TagType.end
            tag = tag.removeprefix("/")
        elif tag.endswith("/"):
            tagType = TagType.single
            tag = tag.removesuffix("/")
        else:
            tagType = TagType.start

        if tag.count(":") == 1:
            valueSep = ValueSep.colon
            feature, value = tag.split(":")
        elif tag.count("=") == 1:
            feature, value = tag.split("=")
            if value.startswith('"') and value.endswith('"'):
                value = value.removeprefix('"').removesuffix('"')
                valueSep = ValueSep.equals
            else:
                feature = tag
                value = None
                valueSep = None
        else:
            feature = tag
            value = None
            valueSep = None

        components.append(FeatureTag(tagType,feature,value,valueSep))
        components.append(text)

    newComponents = []
    for comp in components:
        if (
            (language is not None)
            and isinstance(comp,FeatureTag)
            and (comp.type == TagType.single)
            and (comp.valueSep == ValueSep.colon)
            and (comp.feature == "copy-from")
        ):
            key:str = comp.value
            if _translations[language].get(key) is not None:
                newValue = _translations[language][key].components
            elif _rawTranslations[language].get(key) is not None:
                newValue = _decodeRawString(_rawTranslations[language][key],language).components
            else:
                newValue = [key]
            newComponents.extend(newValue)
        else:
            newComponents.append(comp)

    return FeatureString(newComponents)

def _loadTranslations() -> None:
    for lang,translations in _rawTranslations.items():
        _translations[lang] = {}
        for key,value in translations.items():
            _translations[lang][key] = _decodeRawString(value,lang)
_loadTranslations()

def featureStringFromRaw(rawString:str) -> FeatureString:
    return _decodeRawString(rawString,None)