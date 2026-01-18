from youtubesearchpython import Comments
import json

def test_comments():
    print("Fetching comments for 2sokLXhqRFQ...")
    try:
        comments_helper = Comments('2sokLXhqRFQ')
        print(f"Initial fetch: {len(comments_helper.comments['result'])} comments")
        
        while comments_helper.hasMoreComments and len(comments_helper.comments['result']) < 50:
            print("Fetching more...")
            comments_helper.getNextComments()
            print(f"Total now: {len(comments_helper.comments['result'])}")
            
        # Verify structure
        if len(comments_helper.comments['result']) > 0:
            c = comments_helper.comments['result'][0]
            print("Sample comment keys:", c.keys())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_comments()
