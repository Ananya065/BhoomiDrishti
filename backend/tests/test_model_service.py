import pytest
import os
import torch
from unittest.mock import patch, MagicMock
from ml.services.model_service import ModelService

def test_model_service_sentinel2_success():
    """Test that Sentinel-2 model is selected and fails if checkpoint is missing, but logic flows."""
    with patch('os.path.exists', return_value=True), \
         patch('torch.load', return_value={}), \
         patch('ml.models.model.SiameseUNetAttention.load_state_dict'):
        service = ModelService(sensor='sentinel2', device=torch.device('cpu'))
        assert service.sensor == 'sentinel2'
        assert service.s2_model is not None
        assert service.liss4_model is None
        assert service.s2_model.in_channels == 13

def test_model_service_liss4_missing_checkpoint():
    """Test that LISS-4 honestly fails when checkpoint is missing."""
    with patch.dict(os.environ, {'LISS4_MODEL_CHECKPOINT_PATH': ''}):
        with pytest.raises(FileNotFoundError, match="LISS-4 model checkpoint not configured"):
            ModelService(sensor='liss4', device=torch.device('cpu'))

def test_model_service_liss4_success():
    """Test that LISS-4 model is loaded correctly when configured."""
    with patch.dict(os.environ, {'LISS4_MODEL_CHECKPOINT_PATH': 'dummy_liss4.pth'}), \
         patch('os.path.exists', return_value=True), \
         patch('torch.load', return_value={}), \
         patch('ml.models.model.SiameseUNetAttention.load_state_dict'):
        service = ModelService(sensor='liss4', device=torch.device('cpu'))
        assert service.sensor == 'liss4'
        assert service.liss4_model is not None
        assert service.s2_model is None
        assert service.liss4_model.in_channels == 3

def test_model_service_unsupported_sensor():
    with pytest.raises(ValueError, match="Unsupported sensor"):
        ModelService(sensor='landsat8', device=torch.device('cpu'))
