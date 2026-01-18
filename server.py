from flask import Flask, request, jsonify
from flask_cors import CORS
import httpx
import json
from youtubesearchpython import VideosSearch, Video
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR

app = Flask(__name__)
CORS(app)
downloader = YoutubeCommentDownloader()

def inner_tube_request(endpoint, payload):
    url = f"https://www.youtube.com/youtubei/v1/{endpoint}?key=AIzaSyB5BoZcW8y7_Gk"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/"
    }
    client_context = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20231201.01.00",
                "hl": "en",
                "gl": "US",
                "utcOffsetMinutes": 0
            }
        }
    }
    client_context.update(payload)
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=client_context, headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"InnerTube error ({endpoint}): {str(e)}")
        return None

def format_video(v):
    try:
        # Extract individual fields with extreme safety
        video_id = v.get('id')
        title = v.get('title', 'Unknown Title')
        
        # Safe thumbnail extraction
        thumbnails = v.get('thumbnails', [])
        thumbnail = ''
        if thumbnails and isinstance(thumbnails, list) and len(thumbnails) > 0:
            thumbnail = thumbnails[0].get('url', '')

        # Safe channel/author extraction
        channel_data = v.get('channel') or v.get('author') or {}
        channel_name = channel_data.get('name', 'Unknown')
        
        # Other fields
        duration = v.get('duration', 'N/A')
        
        view_count_data = v.get('viewCount') or {}
        if isinstance(view_count_data, dict):
            views = view_count_data.get('short', 'Unknown')
        else:
            views = str(view_count_data)
            
        uploaded = v.get('publishedTime', 'Unknown')
        
        return {
            'id': str(video_id) if video_id else '',
            'title': str(title),
            'thumbnail': str(thumbnail),
            'channel': str(channel_name),
            'duration': str(duration),
            'views': str(views),
            'uploaded': str(uploaded)
        }
    except Exception as e:
        print(f"Error formatting video: {e}")
        return None

@app.route('/api/trending', methods=['GET'])
def get_trending():
    try:
        # Primary search: trending music with explicit region
        try:
            trending_search = VideosSearch('trending music', limit=12, language='en', region='US')
            results = trending_search.result()
        except Exception as e:
            print(f"Primary trending search failed: {str(e)}. Trying fallback...")
            # Fallback: simple trending keyword which seems more stable
            trending_search = VideosSearch('trending', limit=12)
            results = trending_search.result()
        
        # Check if results is None or missing the 'result' key
        if not results or not isinstance(results, dict) or 'result' not in results:
            print("Warning: YouTube search returned unexpected results format")
            return jsonify({'videos': []})

        videos = []
        for v in results.get('result', []):
            formatted = format_video(v)
            if formatted:
                videos.append(formatted)
                
        return jsonify({'videos': videos})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Trending error: {e}")
        # Return empty list instead of 500 to keep the UI functional
        return jsonify({'videos': [], 'error': str(e)}), 200

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    try:
        videos_search = VideosSearch(query, limit=20)
        results = videos_search.result()
        
        # print(f"DEBUG RESULTS: {results}") # Log this if needed
        
        videos = []
        for v in results.get('result', []):
            formatted = format_video(v)
            if formatted:
                videos.append(formatted)
            
        return jsonify({'videos': videos})
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<id>', methods=['GET'])
def get_video(id):
    try:
        # Use direct InnerTube Player API for stable metadata
        data = inner_tube_request("player", {"videoId": id})
        if not data:
            # Fallback to library if InnerTube fails
            video = Video.getInfo(id)
            if not video:
                return jsonify({'error': 'Video not found'}), 404
            data = video # Use library data as backup
        
        # Extract from InnerTube format or library fallback
        video_details = data.get('videoDetails', {})
        if not video_details and 'title' in data: # Library format
            video_details = data

        return jsonify({
            'id': str(video_details.get('videoId', id)),
            'title': str(video_details.get('title', 'Unknown Title')),
            'description': str(video_details.get('shortDescription', video_details.get('description', ''))),
            'channel': str(video_details.get('author', 'Unknown')),
            'views': f"{int(video_details.get('viewCount', 0)):,}" if str(video_details.get('viewCount', '0')).isdigit() else str(video_details.get('viewCount', '0')),
            'uploaded': '', 
            'duration': str(video_details.get('lengthSeconds', 'N/A')),
            'related': []
        })
    except Exception as e:
        print(f"Video info error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/comments/<id>', methods=['GET'])
def get_comments(id):
    try:
        # Fetching comments (first 50)
        comments_gen = downloader.get_comments_from_url(f'https://www.youtube.com/watch?v={id}', sort_by=SORT_BY_POPULAR)
        
        comments = []
        import itertools
        for comment in itertools.islice(comments_gen, 50):
            comments.append({
                'id': comment['cid'],
                'author': comment['author'],
                'text': comment['text'],
                'time': comment['time'],
                'authorThumb': comment['photo'],
                'likes': comment['votes']
            })
            
        return jsonify({'comments': comments})
    except Exception as e:
        print(f"Comments error: {e}")
        return jsonify({'comments': [], 'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
