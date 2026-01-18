import httpx
import json
import sys

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
        
    continuation = None
    try:
        results = data.get('contents', {}).get('twoColumnWatchNextResults', {}).get('results', {}).get('results', {}).get('contents', [])
        for item in results:
            if 'itemSectionRenderer' in item:
                contents = item['itemSectionRenderer'].get('contents', [])
                for c in contents:
                    if 'continuationItemRenderer' in c:
                        continuation = c['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token']
                        print("Token found:", continuation[:20] + "...")
                        break
            if continuation: break
    
        if continuation:
             print("Fetching comments with token...")
             comments_data = inner_tube_request("next", {"continuation": continuation})
             
             # DUMP THE FULL RESPONSE
             filename = "comments_debug_dump.json"
             with open(filename, "w") as f:
                 json.dump(comments_data, f, indent=2)
             print(f"Dumped response to {filename}")
             
             # Analyze structure
             on_response = comments_data.get('onResponseReceivedEndpoints', [])
             print(f"onResponseReceivedEndpoints length: {len(on_response)}")
             if len(on_response) > 0:
                 print("Keys in first item:", on_response[0].keys())
                 if 'appendContinuationItemsAction' in on_response[0]:
                     print("Found appendContinuationItemsAction")
                     items = on_response[0]['appendContinuationItemsAction'].get('continuationItems', [])
                     print(f"Items in appendContinuationItemsAction: {len(items)}")
                 elif 'reloadContinuationItemsCommand' in on_response[0]:
                     print("Found reloadContinuationItemsCommand")
                     items = on_response[0]['reloadContinuationItemsCommand'].get('continuationItems', [])
                     print(f"Items in reloadContinuationItemsCommand: {len(items)}")
                 else:
                     print("Unknown action key")
        else:
             print("No comment continuation found")

    except Exception as e:
        print(f"Error parsing: {e}")

if __name__ == "__main__":
    test_innertube_comments('iBdqTvC_Jzg')
