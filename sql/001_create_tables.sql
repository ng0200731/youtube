CREATE TABLE IF NOT EXISTS videos (
    video_id        TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    channel_title   TEXT,
    channel_id      TEXT,
    description     TEXT,
    tags            TEXT,
    thumbnail_url   TEXT,
    publish_date    TEXT,
    duration        TEXT,
    duration_seconds INTEGER,
    view_count      INTEGER,
    like_count      INTEGER,
    comment_count   INTEGER,
    category_id     TEXT,
    video_url       TEXT,
    fetched_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS searches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    published_after TEXT NOT NULL,
    published_before TEXT NOT NULL,
    max_results     INTEGER,
    pages_fetched   INTEGER,
    total_results   INTEGER,
    quota_used      INTEGER,
    searched_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_results (
    search_id       INTEGER NOT NULL,
    video_id        TEXT NOT NULL,
    rank_position   INTEGER,
    PRIMARY KEY (search_id, video_id),
    FOREIGN KEY (search_id) REFERENCES searches(id),
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

CREATE INDEX IF NOT EXISTS idx_videos_publish_date ON videos(publish_date);
CREATE INDEX IF NOT EXISTS idx_videos_view_count ON videos(view_count DESC);
CREATE INDEX IF NOT EXISTS idx_search_results_search ON search_results(search_id);

CREATE TABLE IF NOT EXISTS comments (
    comment_id    TEXT PRIMARY KEY,
    video_id      TEXT NOT NULL,
    author        TEXT,
    text          TEXT,
    like_count    INTEGER DEFAULT 0,
    reply_count   INTEGER DEFAULT 0,
    published_at  TEXT,
    fetched_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_comments_video ON comments(video_id);
