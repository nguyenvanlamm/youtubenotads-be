from flask import Flask, request, jsonify
from flask_cors import CORS
import httpx
import json
from youtubesearchpython import VideosSearch, Video

app = Flask(__name__)
CORS(app)

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
        if not data or not data.get('videoDetails'):
            print("Player endpoint failed/incomplete. Trying 'next' endpoint...")
            next_data = inner_tube_request("next", {"videoId": id})
            if next_data:
                # Extract metadata from next response
                try:
                    results = next_data.get('contents', {}).get('twoColumnWatchNextResults', {}).get('results', {}).get('results', {}).get('contents', [])
                    primary = None
                    secondary = None
                    for item in results:
                        if 'videoPrimaryInfoRenderer' in item:
                            primary = item['videoPrimaryInfoRenderer']
                        if 'videoSecondaryInfoRenderer' in item:
                            secondary = item['videoSecondaryInfoRenderer']
                    
                    if primary:
                        # Extract title
                        title_runs = primary.get('title', {}).get('runs', [])
                        title = "".join([r.get('text', '') for r in title_runs])
                        
                        # Extract views
                        view_count = primary.get('viewCount', {}).get('videoViewCountRenderer', {}).get('viewCount', {}).get('simpleText', '0 views')
                        
                        # Extract date
                        date = primary.get('dateText', {}).get('simpleText', '')
                        
                        # Extract channel and description from secondary
                        channel = "Unknown"
                        description = ""
                        if secondary:
                            owner_runs = secondary.get('owner', {}).get('videoOwnerRenderer', {}).get('title', {}).get('runs', [])
                            channel = "".join([r.get('text', '') for r in owner_runs])
                            
                            desc_runs = secondary.get('attributedDescription', {}).get('content', '')
                            # Description often comes as a string in newer api or runs in older
                            if isinstance(desc_runs, list):
                                description = "".join([r.get('text', '') for r in desc_runs])
                            else:
                                description = str(desc_runs)

                        return jsonify({
                            'id': id,
                            'title': title,
                            'description': description,
                            'channel': channel,
                            'views': view_count,
                            'uploaded': date,
                            'duration': 'N/A', # Duration not easily available in next endpoint without complex parsing
                            'related': []
                        })
                except Exception as e:
                    print(f"Error parsing next endpoint for metadata: {e}")

        # Fallback to library if InnerTube fails
        if not data:
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
        print(f"Fetching comments for {id}...")
        # Step 1: Get the initial next response to find the comments continuation token
        initial_data = inner_tube_request("next", {"videoId": id})
        if not initial_data:
             print("No initial data from InnerTube")
             return jsonify({'comments': []})

        continuation = None
        # Deep search for the continuation token in the initial response
        try:
            results = initial_data.get('contents', {}).get('twoColumnWatchNextResults', {}).get('results', {}).get('results', {}).get('contents', [])
            print(f"Searching {len(results)} items in initial response")
            for item in results:
                if 'itemSectionRenderer' in item:
                    contents = item['itemSectionRenderer'].get('contents', [])
                    print(f"Found itemSectionRenderer with {len(contents)} contents")
                    for c in contents:
                        if 'continuationItemRenderer' in c:
                            continuation = c['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token']
                            print(f"Found continuation token: {continuation[:20]}...")
                            break
                if continuation: break
        except Exception as e:
            print(f"Error searching for continuation: {e}")
            pass
            
        if not continuation:
            print("No continuation token found")
            return jsonify({'comments': []})
            
        # Step 2: Fetch the actual comments using the token
        comments_data = inner_tube_request("next", {"continuation": continuation})
        if not comments_data:
             print("No data from comments request")
             return jsonify({'comments': []})
             
        comments = []
        
        # Method 1: Check for frameworkUpdates (New Format)
        framework_updates = comments_data.get('frameworkUpdates', {})
        entity_batch_update = framework_updates.get('entityBatchUpdate', {})
        mutations = entity_batch_update.get('mutations', [])
        
        if mutations:
            print(f"Found {len(mutations)} mutations in frameworkUpdates")
            for mutation in mutations:
                payload = mutation.get('payload', {})
                if 'commentEntityPayload' in payload:
                    cep = payload['commentEntityPayload']
                    properties = cep.get('properties', {})
                    author_info = cep.get('author', {})
                    toolbar = cep.get('toolbar', {})
                    
                    # Extract fields
                    cid = properties.get('commentId', '')
                    author = author_info.get('displayName', 'Unknown')
                    avatar = author_info.get('avatarThumbnailUrl', '')
                    time_published = properties.get('publishedTime', '')
                    content_body = properties.get('content', {}).get('content', '')
                    
                    # Likes are tricky in this format
                    likes = toolbar.get('likeCountLiked', '0')
                    if not likes or likes.strip() == '':
                        likes = '0'
                        
                    comments.append({
                        'id': cid,
                        'author': author,
                        'text': content_body,
                        'time': time_published,
                        'authorThumb': avatar,
                        'likes': likes
                    })
            print(f"Parsed {len(comments)} comments from frameworkUpdates")

        # Method 2: Old Format (Fallback)
        if not comments:
            try:
                # The structure for continuation response is usually here
                on_response = comments_data.get('onResponseReceivedEndpoints', [])
                batch = []
                for endpoint in on_response:
                    if 'appendContinuationItemsAction' in endpoint:
                        batch.extend(endpoint['appendContinuationItemsAction'].get('continuationItems', []))
                    elif 'reloadContinuationItemsCommand' in endpoint:
                        batch.extend(endpoint['reloadContinuationItemsCommand'].get('continuationItems', []))

                print(f"Found {len(batch)} items in legacy batch")

                for item in batch:
                    comment_thread = item.get('commentThreadRenderer', {})
                    comment = comment_thread.get('comment', {}).get('commentRenderer', {})
                    if not comment: continue
                    
                    text_runs = comment.get('contentText', {}).get('runs', [])
                    text = "".join([r.get('text', '') for r in text_runs])
                    
                    author = comment.get('authorText', {}).get('simpleText', 'Unknown')
                    time = comment.get('publishedTimeText', {}).get('runs', [{}])[0].get('text', '')
                    likes = comment.get('voteCount', {}).get('simpleText', '0')
                    cid = comment.get('commentId', '')
                    
                    thumbnails = comment.get('authorThumbnail', {}).get('thumbnails', [])
                    authorThumb = thumbnails[0].get('url', '') if thumbnails else ''
                    
                    comments.append({
                        'id': cid,
                        'author': author,
                        'text': text,
                        'time': time,
                        'authorThumb': authorThumb,
                        'likes': likes
                    })
                if len(comments) > 0:
                    print(f"Parsed {len(comments)} comments from legacy format")
            except Exception as e:
                print(f"Error parsing legacy comments json: {e}")
            
        return jsonify({'comments': comments})

    except Exception as e:
        print(f"Comments error: {str(e)}")
        return jsonify({'comments': [], 'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
