import httpx
import json

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

def test_innertube_comments(video_id):
    print(f"Testing InnerTube 'next' for {video_id}...")
    data = inner_tube_request("next", {"videoId": video_id})
    if not data:
        print("No data from next endpoint")
        return
        
    print("Received data from next endpoint")
    # write to file for inspection
    with open("next_response.json", "w") as f:
        json.dump(data, f, indent=2)
    
    # Try to find comment continuation
    try:
        continuation = None
        # This path is complex, need to search recursively or know the path
        # Usually: contents -> twoColumnWatchNextResults -> results -> results -> contents -> ... -> itemSectionRenderer -> contents -> continuationItemRenderer
        
        # A simple search helper
        def find_key(obj, key):
            if isinstance(obj, dict):
                if key in obj: return obj[key]
                for k, v in obj.items():
                    res = find_key(v, key)
                    if res: return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_key(item, key)
                    if res: return res
            return None

        # Look for "continuationItemRenderer" which often holds the token
        # But specifically for comments, it's often in a section with header "Comments"
        
        # Let's just dump the keys of 'twoColumnWatchNextResults'
        tcr = data.get('contents', {}).get('twoColumnWatchNextResults', {})
        print("twoColumnWatchNextResults keys:", tcr.keys())
        
        # results -> results -> contents -> [videoPrimaryInfo, videoSecondaryInfo, itemSectionRenderer (comments?)]
        results = tcr.get('results', {}).get('results', {}).get('contents', [])
        print(f"Found {len(results)} items in results contents")
        
        for i, item in enumerate(results):
             if 'itemSectionRenderer' in item:
                 print(f"Item {i} is itemSectionRenderer")
                 contents = item['itemSectionRenderer'].get('contents', [])
                 for c in contents:
                     if 'continuationItemRenderer' in c:
                         print("Found continuationItemRenderer in itemSectionRenderer")
                         continuation = c['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token']
                         print("Token found:", continuation[:20] + "...")
                         break
        
        if continuation:
             print("Fetching comments with token...")
             comments_data = inner_tube_request("next", {"continuation": continuation})
             with open("comments_response.json", "w") as f:
                 json.dump(comments_data, f, indent=2)
             print("Comments fetched!")
        else:
             print("No comment continuation found")

    except Exception as e:
        print(f"Error parsing: {e}")

if __name__ == "__main__":
    test_innertube_comments('2sokLXhqRFQ')
