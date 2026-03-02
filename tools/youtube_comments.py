import os
import sys
import time

from googleapiclient.errors import HttpError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import youtube_fetch


def fetch_comments(video_id, max_pages=5):
    # Return cached if available
    if db.has_cached_comments(video_id):
        return db.get_comments(video_id)

    db.init_db()
    youtube, current_key = youtube_fetch.get_youtube_client()

    all_comments = []
    page_token = None

    for page in range(max_pages):
        try:
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': 100,
                'order': 'relevance',
                'textFormat': 'plainText',
            }
            if page_token:
                params['pageToken'] = page_token

            response = youtube.commentThreads().list(**params).execute()

            for item in response.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']
                all_comments.append({
                    'comment_id': item['id'],
                    'video_id': video_id,
                    'author': snippet.get('authorDisplayName', ''),
                    'text': snippet.get('textDisplay', ''),
                    'like_count': snippet.get('likeCount', 0),
                    'reply_count': item['snippet'].get('totalReplyCount', 0),
                    'published_at': snippet.get('publishedAt', ''),
                })

            page_token = response.get('nextPageToken')
            if not page_token:
                break

            if page < max_pages - 1:
                time.sleep(0.2)

        except HttpError as e:
            if e.resp.status == 403:
                if 'commentsDisabled' in str(e):
                    return []
                # Try rotating to next key
                youtube_fetch.mark_key_exhausted(current_key)
                try:
                    youtube, current_key = youtube_fetch.get_youtube_client()
                    continue
                except ValueError:
                    raise ValueError("All API keys exhausted. Add more keys or try tomorrow.")
            if e.resp.status == 404:
                return []
            raise

    db.insert_comments(all_comments)
    return all_comments
