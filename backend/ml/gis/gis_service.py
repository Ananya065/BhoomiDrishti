import logging
from shapely.geometry import shape
import geopandas as gpd
from backend.ml.gis.layers import get_available_layers

logger = logging.getLogger(__name__)

def analyze_region_gis(region_geometry_geojson: dict) -> dict:
    """Analyze a region geometry against available GIS layers."""
    default_result = {
        'sensitive_zone': None,
        'sensitive_zone_type': None,
        'overlap_area_sq_m': None,
        'overlap_percentage': None,
        'gis_status': 'unavailable',
        'intersecting_layers': []
    }
    
    try:
        try:
            region_shape = shape(region_geometry_geojson)
        except Exception as e:
            logger.error(f"Error parsing geometry: {e}")
            default_result['gis_status'] = 'error'
            return default_result
            
        bounds = region_shape.bounds
        if not bounds:
            default_result['gis_status'] = 'error'
            return default_result
            
        # Check if coordinates look like pixel coordinates or missing CRS
        # Usually lat/lon is bounded by [-180, -90, 180, 90]
        # Pixel coordinates are typically > 0 and could be larger
        if bounds[0] >= 0 and bounds[1] >= 0 and bounds[2] > 180 and bounds[3] > 90:
            default_result['gis_status'] = 'non_georeferenced'
            return default_result
            
        available_layers = get_available_layers()
        if not available_layers:
            return default_result
        
        region_gdf = gpd.GeoDataFrame(geometry=[region_shape], crs="EPSG:4326")
        
        sensitive_zone = False
        sensitive_types = []
        total_overlap_area = 0.0
        
        for name, filepath in available_layers.items():
            try:
                layer_gdf = gpd.read_file(filepath)
                if layer_gdf.crs and layer_gdf.crs != region_gdf.crs:
                    region_gdf_proj = region_gdf.to_crs(layer_gdf.crs)
                else:
                    region_gdf_proj = region_gdf
                    
                intersection = gpd.overlay(region_gdf_proj, layer_gdf, how='intersection')
                if not intersection.empty:
                    sensitive_zone = True
                    sensitive_types.append(name)
                    if region_gdf_proj.crs and region_gdf_proj.crs.is_geographic:
                        intersection_area_gdf = intersection.to_crs("EPSG:3857")
                        total_overlap_area += float(intersection_area_gdf.geometry.area.sum())
                    else:
                        total_overlap_area += float(intersection.geometry.area.sum())
            except Exception as e:
                logger.error(f"Error processing layer {name}: {e}")
                
        region_area = 0.0
        if region_gdf.crs and region_gdf.crs.is_geographic:
            region_area = float(region_gdf.to_crs("EPSG:3857").geometry.area.sum())
        else:
            region_area = float(region_gdf.geometry.area.sum())
            
        overlap_pct = (total_overlap_area / region_area * 100) if region_area > 0 else 0.0
        
        return {
            'sensitive_zone': sensitive_zone,
            'sensitive_zone_type': ', '.join(sensitive_types) if sensitive_types else None,
            'overlap_area_sq_m': round(total_overlap_area, 2),
            'overlap_percentage': round(min(overlap_pct, 100.0), 2),
            'gis_status': 'verified' if sensitive_zone else 'no_intersection',
            'intersecting_layers': sensitive_types
        }
    except Exception as e:
        logger.error(f"Error in GIS analysis: {e}")
        default_result['gis_status'] = 'error'
        return default_result
