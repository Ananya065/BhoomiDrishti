"""
Confidence policy for classification.
"""
import os
from typing import Tuple, Optional

# Read thresholds from environment variables or use defaults
HIGH_THRESHOLD = float(os.environ.get('CLASSIFICATION_HIGH_THRESHOLD', '0.6'))
MEDIUM_THRESHOLD = float(os.environ.get('CLASSIFICATION_MEDIUM_THRESHOLD', '0.4'))

def determine_confidence(max_score: float) -> Tuple[str, Optional[str]]:
    """
    Returns the confidence level and potentially overridden activity type.
    """
    if max_score >= HIGH_THRESHOLD:
        return 'high', None
    elif max_score >= MEDIUM_THRESHOLD:
        return 'medium', None
    else:
        return 'low', 'unknown'
