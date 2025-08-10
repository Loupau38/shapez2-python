from . import MapShapeGenerator
from .. import shapeOperations, gameObjects
from fixedint import Int32
from dataclasses import dataclass

@dataclass
class MapGenerationShapeLikeliness:
    GenerationType:MapShapeGenerator.MapShapeGenerationType
    MinimumDistanceToOrigin:Int32
    LikelinessPerMille:Int32

class MapGenerationParameters:

    @dataclass
    class SerializedData:
        FluidsSpawnPrimaryColors:bool = True
        FluidsSpawnSecondaryColors:bool = False
        FluidsSpawnTertiaryColors:bool = False
        FluidPatchLikelinessPercent:Int32 = Int32(15)
        FluidPatchBaseSize:Int32 = Int32(2)
        FluidPatchSizeGrowPercentPerChunk:Int32 = Int32(70)
        FluidPatchMaxSize:Int32 = Int32(4)
        ShapePatchLikelinessPercent:Int32 = Int32(30)
        ShapePatchBaseSize:Int32 = Int32(2)
        ShapePatchSizeGrowPercentPerChunk:Int32 = Int32(70)
        ShapePatchMaxSize:Int32 = Int32(5)
        ShapePatchShapeColorfulnessPercent:Int32 = Int32(50)
        ShapePatchRareShapeLikelinessPercent:Int32 = Int32(30)
        ShapePatchVeryRareShapeLikelinessPercent:Int32 = Int32(10)
        ShapePatchGenerationLikeliness:list[MapGenerationShapeLikeliness] = None

    def __init__(self,data:SerializedData) -> None:
        self.FluidsSpawnPrimaryColors = data.FluidsSpawnPrimaryColors
        self.FluidsSpawnSecondaryColors = data.FluidsSpawnSecondaryColors
        self.FluidsSpawnTertiaryColors = data.FluidsSpawnTertiaryColors
        self.FluidPatchLikelinessPercent = data.FluidPatchLikelinessPercent
        self.FluidPatchBaseSize = data.FluidPatchBaseSize
        self.FluidPatchSizeGrowPercentPerChunk = data.FluidPatchSizeGrowPercentPerChunk
        self.FluidPatchMaxSize = data.FluidPatchMaxSize
        self.ShapePatchLikelinessPercent = data.ShapePatchLikelinessPercent
        self.ShapePatchBaseSize = data.ShapePatchBaseSize
        self.ShapePatchSizeGrowPercentPerChunk = data.ShapePatchSizeGrowPercentPerChunk
        self.ShapePatchMaxSize = data.ShapePatchMaxSize
        self.ShapePatchRareShapeLikelinessPercent = data.ShapePatchRareShapeLikelinessPercent
        self.ShapePatchVeryRareShapeLikelinessPercent = data.ShapePatchVeryRareShapeLikelinessPercent
        self.ShapePatchShapeColorfulnessPercent = data.ShapePatchShapeColorfulnessPercent
        self.ShapePatchGenerationLikeliness = data.ShapePatchGenerationLikeliness.copy()

@dataclass
class GameMode:
    ShapesConfiguration:gameObjects.ShapesConfiguration
    ShapeColorScheme:gameObjects.ColorScheme
    Seed:Int32
    MaxShapeLayers:Int32

class ShapeRegistry:

    def __init__(self,shapesConfiguration:gameObjects.ShapesConfiguration,maxShapeLayers:Int32) -> None:
        self._pyOperationsConfig = shapeOperations.ShapeOperationConfig(int(maxShapeLayers),shapesConfiguration)

    def Op_Stack(self,bottomShape:gameObjects.Shape,topShape:gameObjects.Shape) -> gameObjects.Shape:
        return shapeOperations.stack(bottomShape,topShape,config=self._pyOperationsConfig)[0]

    def Op_PushPin(self,shape:gameObjects.Shape) -> gameObjects.Shape:
        return shapeOperations.pushPin(shape,config=self._pyOperationsConfig)[0]

    def Op_Crystallize(self,shape:gameObjects.Shape,color:gameObjects.Color) -> gameObjects.Shape:
        return shapeOperations.genCrystal(shape,color,config=self._pyOperationsConfig)[0]