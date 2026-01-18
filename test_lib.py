from youtubesearchpython import Video, VideosSearch
import json

def format_video(v):
    try:
        video_id = v.get('id')
        title = v.get('title', 'Unknown Title')
        thumbnails = v.get('thumbnails', [])
        thumbnail = ''
        if thumbnails and isinstance(thumbnails, list) and len(thumbnails) > 0:
            thumbnail = thumbnails[0].get('url', '')
        channel_data = v.get('channel') or v.get('author') or {}
        channel_name = channel_data.get('name', 'Unknown')
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

def test_get_video(id):
    try:
        video = Video.getInfo(id)
        if not video:
             print("Video not found")
             return
             
        related = []
        for r in video.get('suggestions', []):
            formatted = format_video(r)
            if formatted:
                related.append(formatted)
            
        res = {
            'id': str(video.get('id', id)),
            'title': str(video.get('title', 'Unknown Title')),
            'description': str(video.get('description', '')),
            'channel': str((video.get('channel') or video.get('author') or {}).get('name', 'Unknown')),
            'channelUrl': str((video.get('channel') or video.get('author') or {}).get('link', '')),
            'views': str((video.get('viewCount') or {}).get('text', '0') if isinstance(video.get('viewCount'), dict) else '0'),
            'uploaded': str(video.get('publishedTime', '')),
            'duration': str(video.get('duration', {}).get('label', 'N/A') if isinstance(video.get('duration'), dict) else video.get('duration', 'N/A')),
            'related': related
        }
        print("Success for " + id)
    except Exception as e:
        print(f"Video info error for {id}: {e}")

if __name__ == "__main__":
    ids = ['2sokLXhqRFQ', 'bM7PPSzCa40']
    for id in ids:
        test_get_video(id)
