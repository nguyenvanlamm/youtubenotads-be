try:
    from youtubesearchpython import Comments
    print("Comments class imports successfully")
    try:
        comments = Comments('2sokLXhqRFQ')
        print("Comments instantiation success")
        if comments.hasMoreComments:
             res = comments.get()
             print(f"Fetched {len(res['result'])} comments")
    except Exception as e:
        print(f"Comments fetch failed: {e}")
except ImportError:
    print("Comments class NOT found")
