import os
import re
import time
import sys

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# --- Multi-key rotation ---
_exhausted_keys = set()


def _load_keys():
    keys_str = os.getenv('YOUTUBE_API_KEYS', '')
    if keys_str:
        keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        if keys:
            return keys
    single = os.getenv('YOUTUBE_API_KEY', '')
    if single and single != 'your_key_here':
        return [single]
    return []


def get_youtube_client():
    keys = _load_keys()
    if not keys:
        raise ValueError(
            "No YouTube API keys configured. "
            "Add keys to .env as YOUTUBE_API_KEYS=key1,key2,key3"
        )
    available = [k for k in keys if k not in _exhausted_keys]
    if not available:
        raise ValueError("All API keys exhausted. Add more keys or try tomorrow.")
    return build('youtube', 'v3', developerKey=available[0]), available[0]


def mark_key_exhausted(key):
    _exhausted_keys.add(key)


def get_keys_status():
    keys = _load_keys()
    return {
        'total_keys': len(keys),
        'available_keys': len([k for k in keys if k not in _exhausted_keys]),
        'exhausted_keys': len(_exhausted_keys),
    }


def parse_duration(iso_duration):
    if not iso_duration:
        return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


# Script detection patterns for title language filtering
SCRIPT_PATTERNS = {
    'en':    re.compile(r'[a-zA-Z]'),
    'zh-TW': re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]'),
    'zh-CN': re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]'),
    'ja':    re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]'),
    'ko':    re.compile(r'[\uac00-\ud7af\u1100-\u11ff]'),
    'hi':    re.compile(r'[\u0900-\u097f]'),
    'ar':    re.compile(r'[\u0600-\u06ff]'),
    'th':    re.compile(r'[\u0e00-\u0e7f]'),
    'vi':    re.compile(r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]', re.IGNORECASE),
    'ru':    re.compile(r'[\u0400-\u04ff]'),
    'es':    re.compile(r'[a-zA-ZñáéíóúüÑÁÉÍÓÚÜ]'),
    'pt':    re.compile(r'[a-zA-ZãõáéíóúâêôàçÃÕÁÉÍÓÚÂÊÔÀÇ]'),
    'fr':    re.compile(r'[a-zA-ZàâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ]'),
    'de':    re.compile(r'[a-zA-ZäöüßÄÖÜ]'),
    'id':    re.compile(r'[a-zA-Z]'),
}

# Minimum ratio of script-matching characters in the title
SCRIPT_MIN_RATIO = 0.3


def title_matches_lang(title, lang_code):
    if not lang_code or lang_code not in SCRIPT_PATTERNS:
        return True
    pattern = SCRIPT_PATTERNS[lang_code]
    # Strip emoji, punctuation, numbers, spaces for counting
    chars = re.sub(r'[\s\d\W]', '', title, flags=re.UNICODE)
    if not chars:
        return False
    matches = len(pattern.findall(chars))
    ratio = matches / len(chars)
    # For CJK/non-Latin scripts, require at least 30% matching characters
    # For Latin-based languages (en, es, pt, fr, de, id), skip filtering
    # since they share the same script
    latin_langs = {'en', 'es', 'pt', 'fr', 'de', 'id', 'vi'}
    if lang_code in latin_langs:
        return True
    return ratio >= SCRIPT_MIN_RATIO


def search_top_videos(published_after, published_before, max_pages=1, query='',
                      title_lang='', audio_lang=''):
    youtube, current_key = get_youtube_client()
    db.init_db()

    all_video_ids = []
    quota_used = 0
    page_token = None

    # Build search query: combine user query with audio language keyword
    search_q = query.strip() if query else ''
    if audio_lang:
        search_q = f'{search_q} {audio_lang}'.strip()
    if not search_q:
        search_q = ' '

    # Map title language codes to relevanceLanguage (ISO 639-1)
    lang_map = {
        'en': 'en', 'zh-TW': 'zh-Hant', 'zh-CN': 'zh-Hans',
        'ja': 'ja', 'ko': 'ko', 'es': 'es', 'pt': 'pt',
        'fr': 'fr', 'de': 'de', 'hi': 'hi', 'ar': 'ar',
        'th': 'th', 'vi': 'vi', 'id': 'id', 'ru': 'ru',
    }

    # Step 1: Search for video IDs by view count
    for page in range(max_pages):
        try:
            params = {
                'part': 'id',
                'type': 'video',
                'order': 'viewCount',
                'publishedAfter': f"{published_after}T00:00:00Z",
                'publishedBefore': f"{published_before}T23:59:59Z",
                'maxResults': 50,
                'q': search_q,
            }
            if title_lang and title_lang in lang_map:
                params['relevanceLanguage'] = lang_map[title_lang]
            if page_token:
                params['pageToken'] = page_token

            response = youtube.search().list(**params).execute()
            quota_used += 100

            video_ids = [item['id']['videoId'] for item in response.get('items', [])
                         if item['id'].get('videoId')]
            all_video_ids.extend(video_ids)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

            if page < max_pages - 1:
                time.sleep(0.2)

        except HttpError as e:
            if e.resp.status == 403:
                mark_key_exhausted(current_key)
                try:
                    youtube, current_key = get_youtube_client()
                    continue  # Retry with new key
                except ValueError:
                    raise ValueError("All API keys exhausted. Add more keys or try tomorrow.")
            raise

    if not all_video_ids:
        search_id = db.log_search(published_after, published_before, max_pages, 0, quota_used)
        return {'search_id': search_id, 'total_results': 0, 'quota_used': quota_used, 'videos': []}

    # Step 2: Check cache
    cached_ids = db.get_cached_video_ids(all_video_ids)
    uncached_ids = [vid for vid in all_video_ids if vid not in cached_ids]

    # Step 3: Fetch details for uncached videos
    if uncached_ids:
        for i in range(0, len(uncached_ids), 50):
            batch = uncached_ids[i:i + 50]
            details = None
            for _attempt in range(len(_load_keys())):
                try:
                    details = youtube.videos().list(
                        part='snippet,statistics,contentDetails',
                        id=','.join(batch)
                    ).execute()
                    quota_used += 1
                    break
                except HttpError as e:
                    if e.resp.status == 403:
                        mark_key_exhausted(current_key)
                        try:
                            youtube, current_key = get_youtube_client()
                        except ValueError:
                            raise ValueError("All API keys exhausted. Add more keys or try tomorrow.")
                    else:
                        raise

            if details:
                videos_to_insert = []
                for item in details.get('items', []):
                    snippet = item['snippet']
                    stats = item.get('statistics', {})
                    content = item.get('contentDetails', {})
                    duration_iso = content.get('duration', '')

                    videos_to_insert.append({
                        'video_id': item['id'],
                        'title': snippet.get('title', ''),
                        'channel_title': snippet.get('channelTitle', ''),
                        'channel_id': snippet.get('channelId', ''),
                        'description': snippet.get('description', ''),
                        'tags': snippet.get('tags', []),
                        'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                        'publish_date': snippet.get('publishedAt', ''),
                        'duration': duration_iso,
                        'duration_seconds': parse_duration(duration_iso),
                        'view_count': int(stats.get('viewCount', 0)),
                        'like_count': int(stats.get('likeCount', 0)),
                        'comment_count': int(stats.get('commentCount', 0)),
                        'category_id': snippet.get('categoryId', ''),
                        'video_url': f"https://www.youtube.com/watch?v={item['id']}"
                    })

                db.insert_videos(videos_to_insert)

    # Step 4: Log search and link results
    search_id = db.log_search(
        published_after, published_before,
        min(max_pages, page + 1), len(all_video_ids), quota_used
    )
    db.link_search_results(search_id, all_video_ids)

    # Step 5: Return all videos sorted by views, filtered by title language
    videos = db.get_videos_by_ids(all_video_ids)

    if title_lang:
        videos = [v for v in videos if title_matches_lang(v.get('title', ''), title_lang)]

    return {
        'search_id': search_id,
        'total_results': len(videos),
        'quota_used': quota_used,
        'videos': videos
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fetch top YouTube videos by date range')
    parser.add_argument('--after', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--before', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--pages', type=int, default=1, help='Number of pages (50 results each)')
    args = parser.parse_args()

    result = search_top_videos(args.after, args.before, args.pages)
    print(f"Found {result['total_results']} videos (quota used: {result['quota_used']})")
    for v in result['videos'][:10]:
        print(f"  {v['view_count']:>15,} views | {v['title'][:60]}")
