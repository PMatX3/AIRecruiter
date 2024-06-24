import requests

def post_job_description_to_linkedin(text):
    url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": "urn:li:person:AkmRuLQhVO",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    headers = {
        "Authorization": "Bearer AQWxIcTKA13m1wXCv1D175n3NdFJCs6_Lm7liHMk9erMWYltRk_ywrBv7mbdvBzFWyHvhYsBMgRM773-4XxKQSMuCxaPoyQjO9rK5t92q_T-IqKQxBy68EO_3NQzfsDDj48o5fF_gY3e7yk3Cd3zExlvqWYL8OBp--73QkKmldBlHPFbrFFTtoQu8agkPrXdBrz6MHOoZlyk7QGra8lF-iKzXbqBQzYh2tw2yb7y84SxY6DzZMXGZ63mdd3oLRphrjMS95AWy8HF5KgC65G-Xyq61KLeAytPAV86z8UKzA3ifBw_7jrJGYn0yly4Giia1jWdJ-i9cjZjBxiwGqYKnuP55Iz6Yw",
        "X-Restli-Protocol-Version":"2.0.0"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response)
    if response.status_code == 201:
        return "Job description posted successfully on LinkedIn."
    else:
        return "Failed to post job description on LinkedIn."


post_job_description_to_linkedin("This is test job")