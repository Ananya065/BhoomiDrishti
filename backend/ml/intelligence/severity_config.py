# Weights must sum to 1.0
WEIGHTS = {
    'area': 0.25,           # Larger area = higher severity
    'detection_confidence': 0.20,  # Model confidence in change
    'activity_type': 0.20,  # Some activities are inherently more severe
    'gis_overlap': 0.20,    # Overlap with sensitive zones
    'classification_confidence': 0.15  # How sure we are of the activity type
}

# Activity type severity multipliers
ACTIVITY_SEVERITY = {
    'mining': 1.0,
    'deforestation': 0.9,
    'encroachment': 0.8,
    'construction': 0.6,
    'other': 0.3,
    'unknown': 0.2,
    'pending': 0.1
}

# Area thresholds (sq meters)
AREA_THRESHOLDS = {
    'small': 1000,
    'medium': 10000,
    'large': 100000,
    'massive': 1000000
}

# Severity levels
SEVERITY_LEVELS = {
    'CRITICAL': 75,
    'HIGH': 50,
    'MEDIUM': 25,
    'LOW': 0
}
