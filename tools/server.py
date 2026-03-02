import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from flask import Flask, request, jsonify, render_template, Response

import db
import youtube_fetch
import youtube_comments
import export_csv
import notebooklm

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-me')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Honeypot check
    if data.get('website'):
        return jsonify({'error': 'Invalid submission'}), 400

    published_after = data.get('published_after')
    published_before = data.get('published_before')
    max_pages = min(int(data.get('max_pages', 1)), 10)
    query = data.get('query', '').strip()
    title_lang = data.get('title_lang', '').strip()
    audio_lang = data.get('audio_lang', '').strip()

    if not published_after or not published_before:
        return jsonify({'error': 'Both published_after and published_before are required'}), 400

    if published_after > published_before:
        return jsonify({'error': 'Start date must be before end date'}), 400

    try:
        result = youtube_fetch.search_top_videos(
            published_after, published_before, max_pages,
            query, title_lang, audio_lang
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


@app.route('/api/search/history')
def search_history():
    db.init_db()
    history = db.get_search_history()
    return jsonify(history)


@app.route('/api/search/<int:search_id>/results')
def search_results(search_id):
    videos = db.get_search_results(search_id)
    return jsonify(videos)


@app.route('/api/export/csv')
def export_csv_route():
    search_id = request.args.get('search_id', type=int)
    if not search_id:
        return jsonify({'error': 'search_id parameter required'}), 400

    videos = db.get_search_results(search_id)
    if not videos:
        return jsonify({'error': 'No results found for this search'}), 404

    csv_data = export_csv.export_to_string(videos)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=youtube_top_videos_{search_id}.csv'}
    )


@app.route('/api/export/selected-csv', methods=['POST'])
def export_selected_csv():
    data = request.get_json()
    if not data or not data.get('video_ids'):
        return jsonify({'error': 'video_ids required'}), 400

    video_ids = data['video_ids']
    videos = db.get_videos_by_ids(video_ids)
    if not videos:
        return jsonify({'error': 'No videos found'}), 404

    csv_data = export_csv.export_to_string(videos)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=youtube_selected_{len(videos)}.csv'}
    )


@app.route('/api/quota')
def quota():
    db.init_db()
    used = db.get_quota_used_today()
    keys_status = youtube_fetch.get_keys_status()
    daily_limit = keys_status['total_keys'] * 10000
    return jsonify({
        'used_today': used,
        'daily_limit': daily_limit,
        'remaining': max(0, daily_limit - used),
        'keys': keys_status,
    })


@app.route('/api/video/<video_id>/comments')
def video_comments(video_id):
    try:
        comments = youtube_comments.fetch_comments(video_id)
        return jsonify(comments)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to fetch comments: {str(e)}'}), 500


@app.route('/api/export/comments-csv', methods=['POST'])
def export_comments_csv():
    data = request.get_json()
    if not data or not data.get('video_ids'):
        return jsonify({'error': 'video_ids required'}), 400

    video_ids = data['video_ids']
    all_comments = []
    for vid in video_ids:
        try:
            comments = youtube_comments.fetch_comments(vid)
            all_comments.extend(comments)
        except Exception:
            pass

    if not all_comments:
        return jsonify({'error': 'No comments found'}), 404

    videos = db.get_videos_by_ids(video_ids)
    videos_map = {v['video_id']: v for v in videos}

    csv_data = export_csv.export_comments_to_string(all_comments, videos_map)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=youtube_comments_{len(video_ids)}videos.csv'}
    )


@app.route('/api/notebooklm/create', methods=['POST'])
def notebooklm_create():
    data = request.get_json()
    if not data or not data.get('urls'):
        return jsonify({'error': 'urls required'}), 400

    urls = data['urls'][:50]
    try:
        # Try headless first, fall back to non-headless for login
        result = notebooklm.create_notebook_with_urls(urls, headless=True)
        if isinstance(result, dict) and result.get('error') == 'login_required':
            # Auto-open browser for login + notebook creation
            result = notebooklm.create_notebook_with_urls(urls, headless=False)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'NotebookLM failed: {str(e)}'}), 500


@app.route('/api/notebooklm/login', methods=['POST'])
def notebooklm_login():
    try:
        notebooklm.login_to_google()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    db.init_db()

    keys_status = youtube_fetch.get_keys_status()
    if keys_status['total_keys'] == 0:
        print("\n  WARNING: No YouTube API keys configured!")
        print("  Edit .env and set YOUTUBE_API_KEYS=key1,key2,key3")
        print("  Get a key at: https://console.cloud.google.com\n")
    else:
        print(f"  API keys: {keys_status['total_keys']} configured ({keys_status['total_keys'] * 10000} daily units)")

    port = int(os.getenv('PORT', 5000))
    print(f"  Starting server at http://localhost:{port}")
    app.run(debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true', port=port)
