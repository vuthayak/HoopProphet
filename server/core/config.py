"""
Centralized configuration for the HoopProphet API server.

All config values in one place — services import from here,
not from pipeline internals.
"""

# Re-export DB path and data directory from pipeline
from server.pipeline import DB_PATH, DATA_DIR, CACHE_PATH

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

# News & Injury Flags configuration (Phase 6)
ESPN_RSS_URL = "https://www.espn.com/espn/rss/nba/news"
NBA_RSS_URL = "https://www.nba.com/rss/nba_rss.xml"
NBA_INJURY_REPORT_URL = "https://official.nba.com/nba-injury-report/"
NEWS_TTL_HOURS = 6
NEWS_STALE_WARNING_HOURS = 24
NEWS_CLEANUP_DAYS = 30

# Alert keyword mappings per D-11
ALERT_CATEGORIES = {
    "INJURY": {
        "keywords": ["injury", "injured", "hurt", "sprain", "strain", "fracture", "sore", "knee", "ankle", "shoulder", "back", "hamstring", "concussion"],
        "severity": "warning",
        "subcategory_map": {
            "questionable": "QUESTIONABLE",
            "probable": "PROBABLE",
            "doubtful": "DOUBTFUL",
        }
    },
    "OUT": {
        "keywords": ["out", "ruled out", "not playing", "dnp", "did not play", "sidelined"],
        "severity": "critical",
    },
    "QUESTIONABLE": {
        "keywords": ["questionable", "gtc", "game-time decision"],
        "severity": "warning",
    },
    "TRADE": {
        "keywords": ["traded", "trade", "acquired", "signs with", "waived", "claimed off waivers"],
        "severity": "warning",
    },
    "SUSPENSION": {
        "keywords": ["suspended", "suspension", "banned", "indefinitely"],
        "severity": "critical",
    },
    "G_LEAGUE": {
        "keywords": ["g league", "g-league", "assigned to", "recalled from", "two-way"],
        "severity": "info",
    },
    "REST": {
        "keywords": ["rest", "load management", "rest day", "sitting out"],
        "severity": "info",
    },
}
