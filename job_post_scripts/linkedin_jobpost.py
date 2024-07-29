import requests
from dotenv import load_dotenv
import os

load_dotenv()
access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")

def post_job_description_to_linkedin(text):
    url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": "urn:li:person:h7zeQ4FBG0",
        # "author": "urn:li:organization:219216776",
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
        "Authorization": f"Bearer {access_token}",
    }

    print(text)
    response = requests.post(url, json=payload, headers=headers)
    print(response)
    if response.status_code == 201:
        post_urn = response.headers.get('x-restli-id')
        if post_urn:
            return response.status_code
        else:
            return response.status_code
    else:
        return response.status_code


def get_linkedin_post_comments(post_urn, access_token):
    url = f"https://api.linkedin.com/v2/socialActions/{post_urn}/comments"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        comments = response.json()
        return comments
    else:
        print(f"Failed to fetch comments: {response.status_code}")
        return None

def get_linkedin_post_details(post_urn, access_token):
    url = f"https://api.linkedin.com/v2/ugcPosts/{post_urn}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        post_details = response.json()
        return post_details
    else:
        print(f"Failed to fetch post details: {response.status_code}")
        return None


# post_urn = post_job_description_to_linkedin("This is test job")
# print(post_urn)
# comments = get_linkedin_post_comments("urn:li:activity:7123235869976612864", access_token)
# print(comments)
# # data = get_linkedin_post_details("urn:li:activity:7123235869976612864", access_token)
# # print(data)