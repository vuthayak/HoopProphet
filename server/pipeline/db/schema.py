import sqlite3


def init_db(conn: sqlite3.Connection):
    """Create all tables and indexes for the HoopProphet database."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            position TEXT,
            team_id INTEGER,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY,
            abbreviation TEXT NOT NULL,
            full_name TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS player_game_logs (
            player_id INTEGER NOT NULL,
            game_id TEXT NOT NULL,
            season TEXT NOT NULL,
            game_date TEXT NOT NULL,
            matchup TEXT NOT NULL,
            wl TEXT,
            min REAL DEFAULT 0,
            pts REAL DEFAULT 0,
            reb REAL DEFAULT 0,
            ast REAL DEFAULT 0,
            stl REAL DEFAULT 0,
            blk REAL DEFAULT 0,
            fg3m REAL DEFAULT 0,
            fgm REAL DEFAULT 0,
            fga REAL DEFAULT 0,
            ftm REAL DEFAULT 0,
            fta REAL DEFAULT 0,
            oreb REAL DEFAULT 0,
            dreb REAL DEFAULT 0,
            tov REAL DEFAULT 0,
            pf REAL DEFAULT 0,
            plus_minus REAL DEFAULT 0,
            is_dnp INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, game_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        );

        CREATE TABLE IF NOT EXISTS team_stats (
            team_id INTEGER NOT NULL,
            season TEXT NOT NULL,
            def_rating REAL,
            off_rating REAL,
            net_rating REAL,
            pace REAL,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (team_id, season),
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        );

        CREATE TABLE IF NOT EXISTS team_rosters (
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            season TEXT NOT NULL,
            PRIMARY KEY (team_id, player_id, season)
        );

        CREATE TABLE IF NOT EXISTS team_schedules (
            team_id INTEGER NOT NULL,
            game_id TEXT NOT NULL,
            season TEXT NOT NULL,
            game_date TEXT NOT NULL,
            matchup TEXT NOT NULL,
            wl TEXT,
            PRIMARY KEY (team_id, game_id)
        );

        CREATE TABLE IF NOT EXISTS collection_progress (
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            season TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (entity_type, entity_id, season)
        );

        CREATE INDEX IF NOT EXISTS idx_gamelogs_season ON player_game_logs(season);
        CREATE INDEX IF NOT EXISTS idx_gamelogs_date ON player_game_logs(game_date);
        CREATE INDEX IF NOT EXISTS idx_gamelogs_player_season ON player_game_logs(player_id, season);

        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_url TEXT,
            headline TEXT NOT NULL,
            raw_content TEXT,
            published_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
            player_id INTEGER,
            player_name TEXT,
            alert_keywords TEXT,
            UNIQUE(source, source_url, published_at)
        );

        CREATE TABLE IF NOT EXISTS player_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            subcategory TEXT,
            severity TEXT NOT NULL DEFAULT 'warning',
            source TEXT NOT NULL,
            source_url TEXT,
            headline TEXT,
            first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            UNIQUE(player_id, alert_type, source)
        );

        CREATE INDEX IF NOT EXISTS idx_news_items_player ON news_items(player_id);
        CREATE INDEX IF NOT EXISTS idx_news_items_source ON news_items(source, fetched_at);
        CREATE INDEX IF NOT EXISTS idx_player_alerts_player ON player_alerts(player_id);
        CREATE INDEX IF NOT EXISTS idx_player_alerts_type ON player_alerts(alert_type);
    """)
