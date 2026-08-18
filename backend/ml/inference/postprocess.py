import numpy as np
import cv2

def postprocess_mask(prob_map, threshold=0.5, min_area=10):
    """
    prob_map: numpy array (H, W) or (1, H, W) of probabilities
    Returns:
    - binary_mask: numpy array (H, W) 
    - components: list of dicts with region stats
    """
    if prob_map.ndim == 3:
        prob_map = prob_map[0]
        
    binary_mask = (prob_map > threshold).astype(np.uint8)
    
    # Connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    
    components = []
    # label 0 is background
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            # Create a component dict
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            
            # Confidence can be the mean probability in this component
            component_mask = (labels == i)
            mean_conf = float(prob_map[component_mask].mean())
            
            components.append({
                "region_id": i,
                "pixel_count": int(area),
                "bbox": [int(x), int(y), int(w), int(h)],
                "centroid": [float(centroids[i][0]), float(centroids[i][1])],
                "confidence": mean_conf,
                "mask": component_mask # binary mask of just this component
            })
            
    # Rebuild mask removing small components
    clean_mask = np.zeros_like(binary_mask)
    for comp in components:
        clean_mask[comp["mask"]] = 1
        
    return clean_mask, components
