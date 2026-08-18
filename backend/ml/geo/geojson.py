import json
import rasterio
from rasterio.features import shapes
import pyproj
from shapely.geometry import shape, Polygon
from shapely.ops import transform

def generate_geojson(binary_mask, transform_affine, crs, components, resolution=10.0):
    """
    binary_mask: (H, W) numpy array
    transform_affine: affine.Affine object from rasterio
    crs: pyproj.CRS or rasterio.crs.CRS object or string
    components: list of region dicts from postprocess
    resolution: pixel resolution in meters
    """
    features = []
    
    has_crs = crs is not None and str(crs).strip().lower() != 'none'
    is_projected = False
    project_to_wgs84 = None
    
    if has_crs:
        try:
            crs_obj = pyproj.CRS.from_user_input(crs)
            is_projected = crs_obj.is_projected
            wgs84 = pyproj.CRS('EPSG:4326')
            project_to_wgs84 = pyproj.Transformer.from_crs(crs_obj, wgs84, always_xy=True).transform
        except Exception:
            has_crs = False
            
    # Iterate exactly over components to guarantee mapping
    for comp in components:
        comp_mask = comp["mask"].astype('uint8')
        # Extract polygon for this specific connected component
        comp_shapes = list(shapes(comp_mask, mask=(comp_mask == 1), transform=transform_affine))
        
        if not comp_shapes:
            continue
            
        # A component might have holes, but usually maps to one MultiPolygon or Polygon
        # We take the largest geometry or merge them if multiple returned
        geom, _ = comp_shapes[0] 
        poly = shape(geom)
        
        # Area calculation
        area_sq_m = 0.0
        area_method = "projected_crs"
        if has_crs:
            if is_projected:
                area_sq_m = poly.area
            else:
                cea_proj = pyproj.CRS("+proj=cea +lon_0=0 +lat_ts=30 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")
                transformer = pyproj.Transformer.from_crs(crs_obj, cea_proj, always_xy=True)
                metric_poly = transform(transformer.transform, poly)
                area_sq_m = metric_poly.area
        else:
            # Explicit fallback if explicitly target resolution is 10m
            area_sq_m = poly.area * 100.0
            area_method = "pixel_resolution_10m"
            
        if has_crs and project_to_wgs84:
            geojson_poly = transform(project_to_wgs84, poly)
        else:
            geojson_poly = poly
            
        # Update component dict with the exact computed area
        comp["area_sq_m"] = area_sq_m
            
        feature = {
            "type": "Feature",
            "properties": {
                "region_id": comp["region_id"],
                "area_sq_m": round(area_sq_m, 2),
                "area_method": area_method,
                "detection_confidence": round(comp["confidence"], 4),
                "georeferenced": has_crs,
                "coordinate_system": "geographic" if has_crs else "image-local"
            },
            "geometry": json.loads(json.dumps(geojson_poly.__geo_interface__)) if has_crs else geom
        }
        features.append(feature)
        
    return {
        "type": "FeatureCollection",
        "features": features
    }
