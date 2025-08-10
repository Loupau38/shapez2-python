from . import ConsistentRandom
from .. import gameObjects
from fixedint import Int32
import enum

class MapShapeGenerationType(enum.Enum):
    UncoloredHalfShape = 0
    UncoloredAlmostFullShape = 1
    UncoloredFullShape = 2
    UncoloredFullShapePure = 3
    PrimaryColorHalfShape = 4
    PrimaryColorAlmostFullShape = 5
    PrimaryColorFullShape = 6
    PrimaryColorFullShapePure = 7
    SecondaryColorHalfShape = 8
    SecondaryColorAlmostFullShape = 9
    SecondaryColorFullShape = 10
    SecondaryColorFullShapePure = 11
    TertiaryColorHalfShape = 12
    TertiaryColorAlmostFullShape = 13
    TertiaryColorFullShape = 14
    TertiaryColorFullShapePure = 15

from . import otherClasses # circular import workaround

class MapShapeGenerator:

    def __init__(
        self,
        mapGenerationParameters:otherClasses.MapGenerationParameters,
        shapesConfiguration:gameObjects.ShapesConfiguration,
        colorScheme:gameObjects.ColorScheme
    ) -> None:
        self.MapGenerationParameters = mapGenerationParameters
        self.ShapesConfiguration = shapesConfiguration
        self.ColorScheme = colorScheme

    def GenerateClusterShape_withType(
        self,
        rng:ConsistentRandom.ConsistentRandom,
        type:"MapShapeGenerationType"
    ) -> gameObjects.Shape:

        match type:
            case MapShapeGenerationType.UncoloredHalfShape:
                accentColor = self.ColorScheme.defaultColor
            case MapShapeGenerationType.UncoloredAlmostFullShape:
                accentColor = self.ColorScheme.defaultColor
            case MapShapeGenerationType.UncoloredFullShape:
                accentColor = self.ColorScheme.defaultColor
            case MapShapeGenerationType.UncoloredFullShapePure:
                accentColor = self.ColorScheme.defaultColor
            case MapShapeGenerationType.PrimaryColorHalfShape:
                accentColor = rng.Choice(self.ColorScheme.primaryColors)
            case MapShapeGenerationType.PrimaryColorAlmostFullShape:
                accentColor = rng.Choice(self.ColorScheme.primaryColors)
            case MapShapeGenerationType.PrimaryColorFullShape:
                accentColor = rng.Choice(self.ColorScheme.primaryColors)
            case MapShapeGenerationType.PrimaryColorFullShapePure:
                accentColor = rng.Choice(self.ColorScheme.primaryColors)
            case MapShapeGenerationType.SecondaryColorHalfShape:
                accentColor = rng.Choice(self.ColorScheme.secondaryColors)
            case MapShapeGenerationType.SecondaryColorAlmostFullShape:
                accentColor = rng.Choice(self.ColorScheme.secondaryColors)
            case MapShapeGenerationType.SecondaryColorFullShape:
                accentColor = rng.Choice(self.ColorScheme.secondaryColors)
            case MapShapeGenerationType.SecondaryColorFullShapePure:
                accentColor = rng.Choice(self.ColorScheme.secondaryColors)
            case MapShapeGenerationType.TertiaryColorHalfShape:
                accentColor = rng.Choice(self.ColorScheme.tertiaryColors)
            case MapShapeGenerationType.TertiaryColorAlmostFullShape:
                accentColor = rng.Choice(self.ColorScheme.tertiaryColors)
            case MapShapeGenerationType.TertiaryColorFullShape:
                accentColor = rng.Choice(self.ColorScheme.tertiaryColors)
            case MapShapeGenerationType.TertiaryColorFullShapePure:
                accentColor = rng.Choice(self.ColorScheme.tertiaryColors)
            case _:
                raise ValueError

        partCount = Int32(self.ShapesConfiguration.numPartsPerLayer)

        oneQuad = Int32(1)
        halfShapeQuadCount = partCount // Int32(2)
        pureShapePartCount = partCount

        match type:
            case MapShapeGenerationType.UncoloredHalfShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.UncoloredAlmostFullShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.UncoloredFullShape:
                type1ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.UncoloredFullShapePure:
                type1ShapeCount = pureShapePartCount
            case MapShapeGenerationType.PrimaryColorHalfShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.PrimaryColorAlmostFullShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.PrimaryColorFullShape:
                type1ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.PrimaryColorFullShapePure:
                type1ShapeCount = pureShapePartCount
            case MapShapeGenerationType.SecondaryColorHalfShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.SecondaryColorAlmostFullShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.SecondaryColorFullShape:
                type1ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.SecondaryColorFullShapePure:
                type1ShapeCount = pureShapePartCount
            case MapShapeGenerationType.TertiaryColorHalfShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.TertiaryColorAlmostFullShape:
                type1ShapeCount = oneQuad
            case MapShapeGenerationType.TertiaryColorFullShape:
                type1ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.TertiaryColorFullShapePure:
                type1ShapeCount = pureShapePartCount
            case _:
                raise ValueError

        match type:
            case MapShapeGenerationType.UncoloredHalfShape:
                type2ShapeCount = oneQuad
            case MapShapeGenerationType.UncoloredAlmostFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.UncoloredFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.UncoloredFullShapePure:
                type2ShapeCount = Int32(0)
            case MapShapeGenerationType.PrimaryColorHalfShape:
                type2ShapeCount = oneQuad
            case MapShapeGenerationType.PrimaryColorAlmostFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.PrimaryColorFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.PrimaryColorFullShapePure:
                type2ShapeCount = Int32(0)
            case MapShapeGenerationType.SecondaryColorHalfShape:
                type2ShapeCount = oneQuad
            case MapShapeGenerationType.SecondaryColorAlmostFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.SecondaryColorFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.SecondaryColorFullShapePure:
                type2ShapeCount = Int32(0)
            case MapShapeGenerationType.TertiaryColorHalfShape:
                type2ShapeCount = oneQuad
            case MapShapeGenerationType.TertiaryColorAlmostFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.TertiaryColorFullShape:
                type2ShapeCount = halfShapeQuadCount
            case MapShapeGenerationType.TertiaryColorFullShapePure:
                type2ShapeCount = Int32(0)
            case _:
                raise ValueError

        shapeParts:list[gameObjects.ShapePart] = []

        # Part 1 is shared, part 2 not
        part1 = self.PickRandomShape(rng)
        for i in range(type1ShapeCount):
            color = (
                accentColor
                if rng.TestPercentage(self.MapGenerationParameters.ShapePatchShapeColorfulnessPercent) else
                self.ColorScheme.defaultColor
            )
            shapeParts.append(gameObjects.ShapePart(part1,color))

        for i in range(type2ShapeCount):
            part2 = self.PickRandomShape(rng)
            color = (
                accentColor
                if rng.TestPercentage(self.MapGenerationParameters.ShapePatchShapeColorfulnessPercent) else
                self.ColorScheme.defaultColor
            )
            shapeParts.append(gameObjects.ShapePart(part2,color))

        assert len(shapeParts) > 0
        assert len(shapeParts) <= partCount

        for i in range(len(shapeParts),partCount):
            shapeParts.append(gameObjects.ShapePart(None,None))

        rng.Shuffle(shapeParts)

        return gameObjects.Shape([shapeParts])

    def GenerateClusterShape_withDistance(
        self,
        rng:ConsistentRandom.ConsistentRandom,
        distanceToOrigin:Int32
    ) -> gameObjects.Shape:

        type = MapShapeGenerationType.UncoloredHalfShape

        for shape in self.MapGenerationParameters.ShapePatchGenerationLikeliness:

            if (distanceToOrigin < shape.MinimumDistanceToOrigin) or (not rng.TestPerMille(shape.LikelinessPerMille)):
                continue

            # Found it!
            type = shape.GenerationType
            break

        return self.GenerateClusterShape_withType(rng,type)

    def PickRandomShape(self,rng:ConsistentRandom.ConsistentRandom) -> gameObjects.ShapePartType:

        if (
            (len(self.ShapesConfiguration.mapGenerationVeryRareParts) > 0)
            and (rng.TestPercentage(self.MapGenerationParameters.ShapePatchVeryRareShapeLikelinessPercent))
        ):
            return rng.Choice(self.ShapesConfiguration.mapGenerationVeryRareParts)

        if (
            (len(self.ShapesConfiguration.mapGenerationRareParts) > 0)
            and (rng.TestPercentage(self.MapGenerationParameters.ShapePatchRareShapeLikelinessPercent))
        ):
            return rng.Choice(self.ShapesConfiguration.mapGenerationRareParts)

        return rng.Choice(self.ShapesConfiguration.mapGenerationCommonParts)