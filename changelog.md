## 2.0.1
- Fix feature tag decoding not accepting `=` separator if the value doesn't have surrounding `"`

## 2.0.0
- Add gameCode module
  - Add shape part map generation rareness info to `gameObjects.ShapesConfiguration`
- Add ability to replace pygamePIL with pygame
  - Make pygamePIL use submodules like pygame
- Add support for named colors in feature string rendering
- Rename `costs` attribute of `research.LinearUpgradeLevel` to `cost`
- Fix `</color>` having no effect in feature string rendering

## 1.2.0
- Raw islands json file changes :
  - Rename `IslandGroups` to `SimilarIslands`
  - Use translation key for space belts, space pipes, and rails title
  - Remove the space between the letter and the digit in the irregular foundations titles
  - Change `Cross 5 Foundation` to `C5 Foundation`
  - Remove the vortex platform title override
  - Fix the mirrored rail loop inconsistently being called `Flipped`
- Add island group title overrides
  - Change island group `title` property to be a `MaybeTranslationString`

## 1.1.0
- Add `__eq__` method to most classes in game objects

## 1.0.1
- Fix standard migration features not applied when using advanced migration in blueprint decoding

## 1.0.0
- Overhaul basically everything, so no detailed changelog this time

## 0.0.1
- Add initial files