from flask import Flask, request, jsonify
from flask_cors import CORS
from youtubesearchpython import VideosSearch, Video
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR

app = Flask(__name__)
CORS(app)
downloader = YoutubeCommentDownloader()

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
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'channel': channel_name,
            'duration': duration,
            'views': views,
            'uploaded': uploaded
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
            print(f"Primary trending search failed: {e}. Trying fallback...")
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
        # Get video details
        video = Video.getInfo(id)
        if not video:
             return jsonify({'error': 'Video not found'}), 404
             
        # Format related videos
        related = []
        for r in video.get('suggestions', []):
            formatted = format_video(r)
            if formatted:
                related.append(formatted)
            
        return jsonify({
            'id': video.get('id'),
            'title': video.get('title'),
            'description': video.get('description', ''),
            'channel': (video.get('channel') or video.get('author') or {}).get('name', 'Unknown'),
            'channelUrl': (video.get('channel') or video.get('author') or {}).get('link', ''),
            'views': (video.get('viewCount') or {}).get('text', '0') if isinstance(video.get('viewCount'), dict) else '0',
            'uploaded': video.get('publishedTime', ''),
            'duration': video.get('duration', {}).get('label', 'N/A') if isinstance(video.get('duration'), dict) else video.get('duration', 'N/A'),
            'related': related
        })
    except Exception as e:
        print(f"Video info error: {e}")
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
