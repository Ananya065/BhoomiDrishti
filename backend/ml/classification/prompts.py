"""
Prompts for CLIP-based zero-shot classification.
"""

ACTIVITY_CLASSES = [
    'construction',
    'deforestation',
    'mining',
    'encroachment',
    'other'
]

PROMPTS = {
    'construction': 'satellite image showing new buildings, roads, structures, or construction activity',
    'deforestation': 'satellite image showing removal or clearing of vegetation or forest',
    'mining': 'satellite image showing mining pits, exposed earth, excavation, or quarry activity',
    'encroachment': 'satellite image showing development or land-use intrusion into previously undeveloped or restricted land',
    'other': 'satellite image showing a land-use change that does not clearly match construction, deforestation, mining, or encroachment'
}
