import csv
import io
import json
import os
from datetime import datetime


EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.tmp', 'exports')

COLUMNS = [
    'Title', 'Channel', 'Views', 'Likes', 'Comments',
    'Duration (seconds)', 'Publish Date', 'Tags', 'Description',
    'Thumbnail URL', 'Video URL', 'Category ID', 'Video ID'
]


def video_to_row(v):
    tags = v.get('tags', '[]')
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    return [
        v.get('title', ''),
        v.get('channel_title', ''),
        v.get('view_count', 0),
        v.get('like_count', 0),
        v.get('comment_count', 0),
        v.get('duration_seconds', 0),
        v.get('publish_date', ''),
        '|'.join(tags) if isinstance(tags, list) else str(tags),
        v.get('description', ''),
        v.get('thumbnail_url', ''),
        v.get('video_url', ''),
        v.get('category_id', ''),
        v.get('video_id', '')
    ]


def export_to_csv(videos, filename=None):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    if not filename:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for v in videos:
            writer.writerow(video_to_row(v))

    return filepath


def export_to_string(videos):
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(COLUMNS)
    for v in videos:
        writer.writerow(video_to_row(v))
    return output.getvalue()
