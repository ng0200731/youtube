import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from flask import Flask, request, jsonify, render_template, Response

import db
import youtube_fetch
import export_csv

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


@app.route('/api/quota')
def quota():
    db.init_db()
    used = db.get_quota_used_today()
    return jsonify({
        'used_today': used,
        'daily_limit': 10000,
        'remaining': max(0, 10000 - used)
    })


if __name__ == '__main__':
    db.init_db()

    api_key = os.getenv('YOUTUBE_API_KEY', '')
    if not api_key or api_key == 'your_key_here':
        print("\n  WARNING: YouTube API key not configured!")
        print("  Edit .env and set YOUTUBE_API_KEY=<your_key>")
        print("  Get a key at: https://console.cloud.google.com\n")

    port = int(os.getenv('PORT', 5000))
    print(f"  Starting server at http://localhost:{port}")
    app.run(debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true', port=port)
