from dataclasses import dataclass

GAME_VERSIONS = {
    1005 : [
        "0.0.0-alpha1",
        "0.0.0-alpha2",
        "0.0.0-alpha3"
    ],
    1008 : [
        "0.0.0-alpha4"
    ],
    1009 : [
        "0.0.0-alpha5"
    ],
    1013 : [
        "0.0.0-alpha6"
    ],
    1015 : [
        "0.0.0-alpha6.1",
        "0.0.0-alpha6.2"
    ],
    1018 : [
        "0.0.0-alpha7"
    ],
    1019 : [
        "0.0.0-alpha7.1",
        "0.0.0-alpha7.2",
        "0.0.0-alpha7.3"
    ],
    1022 : [
        "0.0.0-alpha7.4"
    ],
    1024 : [
        "0.0.0-alpha8"
    ],
    1027 : [
        "0.0.0-alpha9",
        "0.0.0-alpha10",
        "0.0.0-alpha10.1",
        "0.0.0-alpha10.2"
    ],
    1029 : [
        "0.0.0-alpha11"
    ],
    1030 : [
        "0.0.0-alpha12-demo",
        "0.0.0-alpha12"
    ],
    1031 : [
        "0.0.0-alpha13-demo",
        "0.0.0-alpha13",
        "0.0.0-alpha13.5-demo",
        "0.0.0-alpha13.6-demo",
        "0.0.0-alpha13.7-demo",
        "0.0.0-alpha14-demo",
        "0.0.0-alpha14.1-demo"
    ],
    1032 : [
        "0.0.0-alpha14.2-demo",
        "0.0.0-alpha14.3-demo",
        "0.0.0-alpha15-demo",
        "0.0.0-alpha15.1-demo",
        "0.0.0-alpha15.2-demo",
        "0.0.0-alpha15.3-demo"
    ],
    1033 : [
        "0.0.0-alpha15.2",
        "0.0.0-alpha15.3-demo"
    ],
    1036 : [
        "0.0.0-alpha16"
    ],
    1038 : [
        "0.0.0-alpha16",
        "0.0.0-alpha16.1"
    ],
    1040 : [
        "0.0.0-alpha17"
    ],
    1042 : [
        "0.0.0-alpha18"
    ],
    1045 : [
        "0.0.0-alpha19"
    ],
    1057 : [
        "0.0.0-alpha20"
    ],
    1064 : [
        "0.0.0-alpha21",
        "0.0.0-alpha21.1"
    ],
    1067 : [
        "0.0.0-alpha22.2"
    ],
    1071 : [
        "0.0.0-alpha22.3",
        "0.0.0-alpha22.4"
    ],
    99999 : [
        "0.0.0-alpha22.4"
    ],
    1082 : [
        "0.0.0-alpha23",
        "0.0.0-alpha23.1"
    ],
    1088 : [
        "0.0.0-alpha23.2"
    ],
    1089 : [
        "0.0.1"
    ],
    1091 : [
        "0.0.2"
    ],
    1094 : [
        "0.0.3",
        "0.0.4",
        "0.0.5"
    ],
    1095 : [
        "0.0.6",
        "0.0.7",
        "0.0.8",
        "0.0.8-rc2",
        "0.0.8-rc3"
    ],
    1103 : [
        "0.0.9-rc1"
    ],
    1105 : [
        "0.0.9-rc2",
        "0.0.9-rc3",
        "0.0.9-rc4",
        "0.0.9-rc5",
        "0.0.9-rc6",
        "0.0.9-rc7"
    ],
    1118 : [
        "0.1.0-pre1-rc3"
    ],
    1119 : [
        "0.1.0-pre2-rc1",
        "0.1.0-pre2-rc2"
    ],
    1121 : [
        "0.1.0-pre3-rc1",
        "0.1.0-pre4-rc1"
    ],
    1122 : [
        "0.1.0-pre5-rc1",
        "0.1.0-pre6-rc1",
        "0.1.0-pre7-rc1",
        "0.1.0-pre8-rc1",
        "0.1.1"
    ]
}
LATEST_GAME_VERSION = list(GAME_VERSIONS.keys())[-1]
LATEST_MAJOR_VERSION = 3

@dataclass
class AlphaSuffix:
    version:str
    subVersion:str|None

@dataclass
class ReleaseCandidateSuffix:
    number:str

@dataclass
class PreviewSuffix:
    number:str

class DemoSuffix:...

@dataclass
class VersionName:
    major:str
    minor:str
    patch:str
    suffixes:list[AlphaSuffix|ReleaseCandidateSuffix|PreviewSuffix|DemoSuffix]

def getVersionNameFromId(versionId:str) -> VersionName:

    mainNumber, *suffixes = versionId.split("-")

    output = VersionName(*mainNumber.split("."),[])

    for suffix in suffixes:

        if suffix.startswith("alpha"):
            suffixNumSplit = suffix.removeprefix("alpha").split(".")
            output.suffixes.append(AlphaSuffix(
                suffixNumSplit[0],
                suffixNumSplit[1] if len(suffixNumSplit) > 1 else None
            ))

        elif suffix.startswith("rc"):
            output.suffixes.append(ReleaseCandidateSuffix(suffix.removeprefix("rc")))

        elif suffix.startswith("pre"):
            output.suffixes.append(PreviewSuffix(suffix.removeprefix("pre")))

        elif suffix == "demo":
            output.suffixes.append(DemoSuffix())

    return output

def versionNameToString(versionName:VersionName) -> str:

    output = f"{versionName.major}.{versionName.minor}.{versionName.patch}"

    for suffix in versionName.suffixes:

        if isinstance(suffix,AlphaSuffix):
            output += f" Alpha {suffix.version}"
            if suffix.subVersion is not None:
                output += f".{suffix.subVersion}"

        elif isinstance(suffix,ReleaseCandidateSuffix):
            output += f" RC {suffix.number}"

        elif isinstance(suffix,PreviewSuffix):
            output += f" Preview {suffix.number}"

        elif isinstance(suffix,DemoSuffix):
            output += " Demo"

    return output