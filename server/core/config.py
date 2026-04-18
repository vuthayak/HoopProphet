"""
Centralized configuration for the HoopProphet API server.

All config values in one place — services import from here,
not from pipeline internals.
"""

# Re-export DB path and data directory from pipeline
from server.pipeline import DB_PATH, DATA_DIR

# Model artifact path from training config
from server.pipeline.train_config import MODEL_ARTIFACT_PATH

# API server settings
API_HOST = "0.0.0.0"
API_PORT = 8000

# CORS allowed origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://frontend:3000",
]

# Alias for convenience
DB_FILE = DB_PATH
