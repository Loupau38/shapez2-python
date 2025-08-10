from . import otherClasses, MapShapeGenerator, ConsistentRandom
from .. import gameObjects
from fixedint import Int32

class RandomResearchShapeGenerator:

    MapConfigNormal = otherClasses.MapGenerationParameters.SerializedData(
        ShapePatchShapeColorfulnessPercent = 50,
        ShapePatchRareShapeLikelinessPercent = 30,
        ShapePatchVeryRareShapeLikelinessPercent = 10,
        ShapePatchGenerationLikeliness = [
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.TertiaryColorFullShapePure,40,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.TertiaryColorFullShape,32,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.TertiaryColorAlmostFullShape,28,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.TertiaryColorHalfShape,24,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.SecondaryColorFullShapePure,20,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.SecondaryColorFullShape,16,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.SecondaryColorAlmostFullShape,12,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.SecondaryColorHalfShape,10,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.PrimaryColorFullShapePure,8,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.PrimaryColorFullShape,6,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.PrimaryColorAlmostFullShape,4,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.PrimaryColorHalfShape,3,100),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.UncoloredFullShapePure,2,100),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.UncoloredFullShape,1,300),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.UncoloredAlmostFullShape,1,500),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.UncoloredHalfShape,0,1000)
        ]
    )

    MapConfigCrystals = otherClasses.MapGenerationParameters.SerializedData(
        ShapePatchShapeColorfulnessPercent = 50,
        ShapePatchRareShapeLikelinessPercent = 30,
        ShapePatchVeryRareShapeLikelinessPercent = 10,
        ShapePatchGenerationLikeliness = [
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.TertiaryColorAlmostFullShape,28,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.TertiaryColorHalfShape,24,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.SecondaryColorAlmostFullShape,12,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.SecondaryColorHalfShape,10,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.PrimaryColorAlmostFullShape,4,80),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.PrimaryColorHalfShape,3,100),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.UncoloredAlmostFullShape,1,500),
            otherClasses.MapGenerationShapeLikeliness(MapShapeGenerator.MapShapeGenerationType.UncoloredHalfShape,0,1000)
        ]
    )

    def __init__(
        self,
        mode:otherClasses.GameMode,
        shapes:otherClasses.ShapeRegistry,
        crystals:bool=False
    ) -> None:
        self.Rng = ConsistentRandom.ConsistentRandom(Int32(0))
        self.Crystals = crystals
        self.MapShapeGenerator = MapShapeGenerator.MapShapeGenerator(
            otherClasses.MapGenerationParameters(
                RandomResearchShapeGenerator.MapConfigCrystals
                if crystals else
                RandomResearchShapeGenerator.MapConfigNormal
            ),
            mode.ShapesConfiguration,
            mode.ShapeColorScheme
        )
        self.Shapes = shapes
        self.Mode = mode

    def Generate(self,level:Int32) -> gameObjects.Shape:

        seed = self.Mode.Seed
        self.Rng.SetSeed(seed + Int32(333) * level + (Int32(117) if self.Crystals else Int32(0)))

        additionalLayers = min(max(level//Int32(10),Int32(0)),self.Mode.MaxShapeLayers-Int32(1))

        distanceToOrigin = level

        # Generate base shape
        shape = self.MapShapeGenerator.GenerateClusterShape_withDistance(self.Rng,distanceToOrigin)

        crystalColors = [c for c in self.Mode.ShapeColorScheme.colors if c != self.Mode.ShapeColorScheme.defaultColor]

        # If we allow crystals, crystallize the shape with a given percentage
        # Loupau note : crystallization is guaranteed, not with a percentage
        if self.Crystals:
            colorCrystal1 = self.Rng.Choice(crystalColors)
            shape = self.Shapes.Op_Crystallize(shape,colorCrystal1)

        # Generate N additional layers depending on the level
        for i in range(additionalLayers):

            # Generate the shape to be stacked
            stackedShape = self.MapShapeGenerator.GenerateClusterShape_withDistance(self.Rng,distanceToOrigin)

            # Starting from level N, also use pin pusher operations
            if (level > Int32(50)) and (self.Rng.TestPercentage(Int32(15))):

                stackedShape = self.Shapes.Op_PushPin(stackedShape)
                assert not shape.isEmpty()

            # Stack the newly generated shape on top of the previous one
            shape = self.Shapes.Op_Stack(shape,stackedShape)
            assert not shape.isEmpty()

            # If we allow crystals, crystallize the shape afterwards starting from a given level
            if self.Crystals and (level >= Int32(10)) and self.Rng.TestPercentage(Int32(85)):

                colorCrystal2 = self.Rng.Choice(crystalColors)
                shape = self.Shapes.Op_Crystallize(shape,colorCrystal2)

        return shape