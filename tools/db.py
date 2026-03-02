import sqlite3
import os
import json

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.tmp')
DB_PATH = os.path.join(DB_DIR, 'yt_cache.db')
SQL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sql')


def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    schema_path = os.path.join(SQL_DIR, '001_create_tables.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    conn = get_connection()
    conn.executescript(schema)
    conn.close()


def get_cached_video_ids(video_ids):
    if not video_ids:
        return set()
    conn = get_connection()
    placeholders = ','.join('?' for _ in video_ids)
    rows = conn.execute(
        f"SELECT video_id FROM videos WHERE video_id IN ({placeholders})",
        list(video_ids)
    ).fetchall()
    conn.close()
    return {row['video_id'] for row in rows}


def insert_videos(videos):
    if not videos:
        return
    conn = get_connection()
    for v in videos:
        tags_json = json.dumps(v.get('tags', []))
        conn.execute("""
            INSERT OR REPLACE INTO videos
            (video_id, title, channel_title, channel_id, description, tags,
             thumbnail_url, publish_date, duration, duration_seconds,
             view_count, like_count, comment_count, category_id, video_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v['video_id'], v['title'], v.get('channel_title'), v.get('channel_id'),
            v.get('description'), tags_json, v.get('thumbnail_url'),
            v.get('publish_date'), v.get('duration'), v.get('duration_seconds'),
            v.get('view_count'), v.get('like_count'), v.get('comment_count'),
            v.get('category_id'), v.get('video_url')
        ))
    conn.commit()
    conn.close()


def log_search(published_after, published_before, pages_fetched, total_results, quota_used):
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO searches (published_after, published_before, pages_fetched, total_results, quota_used)
        VALUES (?, ?, ?, ?, ?)
    """, (published_after, published_before, pages_fetched, total_results, quota_used))
    search_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return search_id


def link_search_results(search_id, video_ids):
    if not video_ids:
        return
    conn = get_connection()
    for rank, vid in enumerate(video_ids, 1):
        conn.execute("""
            INSERT OR IGNORE INTO search_results (search_id, video_id, rank_position)
            VALUES (?, ?, ?)
        """, (search_id, vid, rank))
    conn.commit()
    conn.close()


def get_videos_by_ids(video_ids):
    if not video_ids:
        return []
    conn = get_connection()
    placeholders = ','.join('?' for _ in video_ids)
    rows = conn.execute(
        f"SELECT * FROM videos WHERE video_id IN ({placeholders}) ORDER BY view_count DESC",
        list(video_ids)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_search_history():
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, published_after, published_before, pages_fetched,
               total_results, quota_used, searched_at
        FROM searches ORDER BY searched_at DESC LIMIT 50
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_search_results(search_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT v.* FROM videos v
        JOIN search_results sr ON v.video_id = sr.video_id
        WHERE sr.search_id = ?
        ORDER BY v.view_count DESC
    """, (search_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_quota_used_today():
    conn = get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(quota_used), 0) as total
        FROM searches
        WHERE date(searched_at) = date('now')
    """).fetchone()
    conn.close()
    return row['total']


def get_comments(video_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM comments WHERE video_id = ? ORDER BY like_count DESC
    """, (video_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def has_cached_comments(video_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM comments WHERE video_id = ?", (video_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] > 0


def insert_comments(comments):
    if not comments:
        return
    conn = get_connection()
    for c in comments:
        conn.execute("""
            INSERT OR REPLACE INTO comments
            (comment_id, video_id, author, text, like_count, reply_count, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            c['comment_id'], c['video_id'], c.get('author'),
            c.get('text'), c.get('like_count', 0),
            c.get('reply_count', 0), c.get('published_at')
        ))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print(f"Database initialized at {DB_PATH}")
