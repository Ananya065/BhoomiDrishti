"""
Core classifier module using CLIP for zero-shot classification.
"""
import os
import torch
from PIL import Image
from typing import Dict, Any

from .prompts import ACTIVITY_CLASSES, PROMPTS
from .confidence import determine_confidence

_model = None
_processor = None

def _load_model():
    """
    Lazy loads the CLIP model and processor.
    """
    global _model, _processor
    if _model is None:
        from transformers import CLIPModel, CLIPProcessor
        model_name = os.environ.get('CLIP_MODEL_NAME', 'openai/clip-vit-base-patch32')
        _model = CLIPModel.from_pretrained(model_name)
        _processor = CLIPProcessor.from_pretrained(model_name)
        _model.eval()

def classify_image(image: Image.Image) -> Dict[str, Any]:
    """
    Classify a cropped PIL Image using CLIP zero-shot classification.
    """
    try:
        _load_model()
    except Exception as e:
        return {
            'activity_type': 'unknown',
            'classification_confidence': 'low',
            'classification_method': 'clip_zero_shot',
            'classification_status': 'error',
            'top_scores': {}
        }
    
    try:
        prompts = [PROMPTS[c] for c in ACTIVITY_CLASSES]
        inputs = _processor(text=prompts, images=image, return_tensors="pt", padding=True)
        
        with torch.no_grad():
            outputs = _model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1).squeeze().tolist()
        
        scores = {cls: prob for cls, prob in zip(ACTIVITY_CLASSES, probs)}
        max_score = max(probs)
        best_class = ACTIVITY_CLASSES[probs.index(max_score)]
        
        confidence_level, overridden_class = determine_confidence(max_score)
        
        final_class = overridden_class if overridden_class else best_class
        status = 'classified' if confidence_level in ['high', 'medium'] else 'low_confidence'
        
        return {
            'activity_type': final_class,
            'classification_confidence': confidence_level,
            'classification_method': 'clip_zero_shot',
            'classification_status': status,
            'top_scores': scores
        }
    except Exception as e:
        return {
            'activity_type': 'unknown',
            'classification_confidence': 'low',
            'classification_method': 'clip_zero_shot',
            'classification_status': 'error',
            'top_scores': {}
        }
