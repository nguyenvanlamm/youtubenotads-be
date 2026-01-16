from flask import Flask, request, jsonify
from flask_cors import CORS
from youtubesearchpython import VideosSearch, Video
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR

app = Flask(__name__)
CORS(app)
downloader = YoutubeCommentDownloader()

@app.route('/api/trending', methods=['GET'])
def get_trending():
    try:
        # Since Trending class doesn't exist, we search for a generic trending keyword
        trending_search = VideosSearch('trending music', limit=12)
        results = trending_search.result()
        
        videos = []
        for v in results.get('result', []):
            try:
                videos.append({
                    'id': v['id'],
                    'title': v['title'],
                    'thumbnail': v['thumbnails'][0]['url'] if v['thumbnails'] else '',
                    'channel': v.get('channel', {}).get('name', 'Unknown') if v.get('channel') else v.get('author', {}).get('name', 'Unknown'),
                    'duration': v.get('duration', 'N/A'),
                    'views': v.get('viewCount', {}).get('short', 'Unknown') if v.get('viewCount') else 'Unknown',
                    'uploaded': v.get('publishedTime', 'Recent')
                })
            except:
                continue
        return jsonify({'videos': videos})
    except Exception as e:
        print(f"Trending error: {e}")
        return jsonify({'error': str(e)}), 500

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
            try:
                videos.append({
                    'id': v['id'],
                    'title': v['title'],
                    'thumbnail': v['thumbnails'][0]['url'] if v['thumbnails'] else '',
                    'channel': v.get('channel', {}).get('name', 'Unknown') if v.get('channel') else v.get('author', {}).get('name', 'Unknown'),
                    'duration': v.get('duration', 'N/A'),
                    'views': v.get('viewCount', {}).get('short', 'Unknown') if v.get('viewCount') else 'Unknown',
                    'uploaded': v.get('publishedTime', 'Unknown')
                })
            except Exception as item_err:
                print(f"Error parsing item: {item_err}")
                continue
            
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
            try:
                related.append({
                    'id': r['id'],
                    'title': r['title'],
                    'thumbnail': r['thumbnails'][0]['url'] if r['thumbnails'] else '',
                    'channel': r.get('channel', {}).get('name', 'Unknown') if r.get('channel') else r.get('author', {}).get('name', 'Unknown'),
                    'duration': r.get('duration', 'N/A'),
                    'views': r.get('viewCount', {}).get('short', 'Unknown') if r.get('viewCount') else '',
                    'uploaded': r.get('publishedTime', '')
                })
            except:
                continue
            
        return jsonify({
            'id': video.get('id'),
            'title': video.get('title'),
            'description': video.get('description', ''),
            'channel': video.get('channel', {}).get('name', 'Unknown') if video.get('channel') else video.get('author', {}).get('name', 'Unknown'),
            'channelUrl': video.get('channel', {}).get('link', '') if video.get('channel') else video.get('author', {}).get('link', ''),
            'views': video.get('viewCount', {}).get('text', '0') if video.get('viewCount') else '0',
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
    print("🚀 Python Server running at http://localhost:3001")
    app.run(port=3001)
