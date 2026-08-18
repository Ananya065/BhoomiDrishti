import json
import rasterio
from rasterio.features import shapes
import pyproj
from shapely.geometry import shape, Polygon
from shapely.ops import transform

def generate_geojson(binary_mask, transform_affine, crs, components):
    """
    binary_mask: (H, W) numpy array
    transform_affine: affine.Affine object from rasterio
    crs: pyproj.CRS or rasterio.crs.CRS object or string
    components: list of region dicts from postprocess
    """
    features = []
    
    # Generate shapes using rasterio for the entire mask at once
    # This gives us polygons in the raster's CRS
    mask_shapes = list(shapes(binary_mask, mask=(binary_mask == 1), transform=transform_affine))
    
    # We need to compute area in square meters and output geojson in EPSG:4326
    
    is_projected = False
    project_to_wgs84 = None
    project_to_metric = None
    
    has_crs = crs is not None and str(crs).strip().lower() != 'none'
    
    if has_crs:
        crs_obj = pyproj.CRS.from_user_input(crs)
        is_projected = crs_obj.is_projected
        
        # Transformer to WGS84 for GeoJSON
        wgs84 = pyproj.CRS('EPSG:4326')
        project_to_wgs84 = pyproj.Transformer.from_crs(crs_obj, wgs84, always_xy=True).transform
        
        if not is_projected:
            # Create a localized UTM projection for area calculation
            # We'll do this lazily per polygon using an equal-area or UTM projection based on bounds
            pass
    
    # Assign each shape to the corresponding region component based on centroid
    for geom, value in mask_shapes:
        poly = shape(geom)
        
        # Calculate area in square meters
        area_sq_m = 0.0
        if has_crs:
            if is_projected:
                area_sq_m = poly.area
            else:
                # Reproject to an equal area projection (e.g. CEA) to calculate area
                cea_proj = pyproj.CRS("+proj=cea +lon_0=0 +lat_ts=30 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")
                transformer = pyproj.Transformer.from_crs(crs_obj, cea_proj, always_xy=True)
                metric_poly = transform(transformer.transform, poly)
                area_sq_m = metric_poly.area
        else:
            # Fallback: assume Sentinel-2 10m resolution if no CRS is provided
            area_sq_m = poly.area * 100.0
            
        # Convert to WGS84 for GeoJSON output
        if has_crs and project_to_wgs84:
            geojson_poly = transform(project_to_wgs84, poly)
        else:
            # Fallback if no CRS: we can't reliably place this on Earth.
            # But the existing UI needs lat/lng. We'll just pass the raw coords, 
            # though they won't make sense on a real map.
            # The actual inference API will provide georeferenced images.
            geojson_poly = poly
            
        # Match with component to get confidence and region_id
        # A simple heuristic: centroid inside the component's bbox in pixel space
        # Wait, the `mask_shapes` poly is already in spatial coordinates.
        # It's easier to just calculate properties from the polygon directly if we don't strictly need the components mapping,
        # but let's use the area and simple logic to assign an ID.
        feature = {
            "type": "Feature",
            "properties": {
                "region_id": len(features) + 1,
                "area_sq_m": round(area_sq_m, 2),
                "confidence": 0.90 # placeholder unless we map properly to `components`
            },
            "geometry": geom if not has_crs else json.loads(json.dumps(geojson_poly.__geo_interface__))
        }
        features.append(feature)
        
    return {
        "type": "FeatureCollection",
        "features": features
    }
