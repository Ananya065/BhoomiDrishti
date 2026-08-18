def analyze_temporal(case_id: str, current_area: float, current_detected_at, db_session) -> dict:
    try:
        from database import ChangeRecord
        from sqlalchemy import select
        import json
        from shapely.geometry import shape, Polygon
        import traceback
        
        current = db_session.execute(select(ChangeRecord).where(ChangeRecord.id == case_id)).scalar_one_or_none()
        if not current:
            return _default_temporal_new()
            
        location_name = current.location_name
        current_geom = None
        try:
            if current.mask_geojson:
                gj = json.loads(current.mask_geojson)
                if 'features' in gj and len(gj['features']) > 0:
                    current_geom = shape(gj['features'][0]['geometry'])
        except Exception:
            pass
            
        # Get historical records for the same location name
        query = select(ChangeRecord).where(
            (ChangeRecord.location_name == location_name) & 
            (ChangeRecord.id != case_id)
        ).order_by(ChangeRecord.detected_at.asc())
        candidate_records = db_session.execute(query).scalars().all()
        
        matched_records = []
        for cand in candidate_records:
            overlap = False
            cand_geom = None
            try:
                if cand.mask_geojson:
                    cand_gj = json.loads(cand.mask_geojson)
                    if 'features' in cand_gj and len(cand_gj['features']) > 0:
                        cand_geom = shape(cand_gj['features'][0]['geometry'])
            except Exception:
                pass
                
            if current_geom and cand_geom:
                try:
                    if current_geom.intersects(cand_geom):
                        overlap = True
                except Exception:
                    pass
            
            # If no geometries or overlap found, we fall back to just same location for very simple cases,
            # but ideally we only match if they intersect.
            if overlap:
                matched_records.append(cand)
                
        if not matched_records:
            return _default_temporal_new()
            
        # Sort matched records by detected_at ascending
        matched_records.sort(key=lambda x: x.detected_at)
        
        # Include current in the timeline
        all_records = matched_records + [current]
            
        first_detected = all_records[0].detected_at
        last_detected = all_records[-1].detected_at
        observation_count = len(all_records)
        
        area_progression = [{'date': d.detected_at.isoformat() if d.detected_at else None, 'area': d.area_sq_m} for d in all_records]
        
        previous_area = matched_records[-1].area_sq_m
        if previous_area and previous_area > 0:
            growth_rate_pct = ((current_area - previous_area) / previous_area) * 100
        else:
            growth_rate_pct = 0.0
            
        if growth_rate_pct > 5.0:
            temporal_status = 'expanding'
        elif growth_rate_pct < -5.0:
            temporal_status = 'reduced'
        else:
            temporal_status = 'stable'
            
        return {
            'temporal_status': temporal_status,
            'first_detected': first_detected,
            'last_detected': last_detected,
            'observation_count': observation_count,
            'area_progression': area_progression,
            'growth_rate_pct': round(growth_rate_pct, 2)
        }
    except Exception as e:
        return _default_temporal_new()
        
def _default_temporal_new() -> dict:
    return {
        'temporal_status': 'new',
        'first_detected': None,
        'last_detected': None,
        'observation_count': 1,
        'area_progression': [],
        'growth_rate_pct': None
    }
