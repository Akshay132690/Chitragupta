import numpy as np
import geopandas as gpd
from skimage.morphology import skeletonize
from rasterio.features import shapes
from shapely.geometry import shape


def mask_to_geojson(mask, out_path, threshold=0.3):
    """
    mask: float numpy array (H, W) with values in [0,1]
    out_path: path to save GeoJSON
    threshold: probability threshold for road pixels
    """

    # 1. Binarize
    binary = (mask > threshold)

    # 2. Skeletonize (returns boolean)
    skeleton = skeletonize(binary)

    # 3. Convert bool -> uint8 for rasterio
    skeleton_u8 = (skeleton.astype(np.uint8)) * 255

    geometries = []

    for geom, value in shapes(skeleton_u8, mask=skeleton_u8):
        if value == 255:
            try:
                geometries.append(shape(geom))
            except Exception:
                pass

    # 4. Create GeoDataFrame
    if geometries:
        gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
    else:
        gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # 5. Save GeoJSON
    gdf.to_file(out_path, driver="GeoJSON")

    return gdf
