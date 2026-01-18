from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
import yt_dlp

app = Flask(__name__)
CORS(app)
downloader = YoutubeCommentDownloader()

@app.route('/api/proxy', methods=['GET', 'OPTIONS'])
def proxy():
    if request.method == 'OPTIONS':
        return '', 204
    
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Forward headers that might be needed
        headers = {
            'User-Agent': request.headers.get('User-Agent'),
            'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.9'),
        }
        
        # Make the request to YouTube
        resp = requests.get(url, headers=headers, stream=True)
        
        # Forward the response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'access-control-allow-origin']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        print(f"Proxy error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<id>', methods=['GET'])
def get_video_info(id):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f'https://www.youtube.com/watch?v={id}'
            info = ydl.extract_info(url, download=False)
            
            # Format output for frontend
            return jsonify({
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description', ''),
                'channel': info.get('uploader', 'Unknown'),
                'views': f"{info.get('view_count', 0):,}",
                'uploaded': info.get('upload_date', ''),
                'duration': str(info.get('duration', 0)),
                'related': [] # For now
            })
    except Exception as e:
        print(f"yt-dlp error: {e}")
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
    app.run(port=5000)
