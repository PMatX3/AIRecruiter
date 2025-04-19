import requests
from dotenv import load_dotenv
import os
import logging
from markdown_it import MarkdownIt
import html
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.footnote import footnote_plugin


md = (
    MarkdownIt('commonmark' ,{'breaks':True,'html':True})
    .use(front_matter_plugin)
    .use(footnote_plugin)
    .enable('table')
)

load_dotenv()
access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def post_job_description_to_linkedin(text):
    logging.info(f"Started posting job description to LinkedIn")
    try:
        logging.info(f"Trying to post job description to LinkedIn {text}")
        text = convert_text_to_linkedin_post_format_gemini(text)
        url = "https://api.linkedin.com/v2/ugcPosts"
        payload = {
            "author": "urn:li:organization:104525067",
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

        logging.info(f"Payload: {payload}")

        headers = {
            "Authorization": f"Bearer {access_token}"  # Ensure "Bearer" prefix is included
        }

        logging.info(f"Headers: {headers}")
        print("\n \n headers: ",headers)
        print(text)
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response: {response}")
        logging.info(f"Response: {response}")
        if response.status_code == 201:
            post_urn = response.headers.get('x-restli-id')
            print(post_urn)
            if post_urn:
                return response.status_code
            else:
                return response.status_code
        else:
            return response.status_code
    except Exception as e:
        print(e)
        return 500

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

def convert_text_to_linkedin_post_format_gemini(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

    payload = {"contents":[{"parts":[{"text":f"re-format text : {text} for linkedin post"}]}]}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    print(response)
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# post_urn = post_job_description_to_linkedin('this is test')

# from bs4 import BeautifulSoup
# def format_html_content(html_content):
#     """Converts HTML content into a LinkedIn-friendly formatted string."""
#     soup = BeautifulSoup(html_content, 'html.parser')
    
#     formatted_text = ''
#     for tag in soup:
#         if tag.name == 'p':
#             # Add double line breaks before and after paragraphs for proper spacing
#             formatted_text += f"\n\n{tag.get_text(strip=True)}"
#         elif tag.name == 'strong':
#             # Convert <strong> to bold text
#             formatted_text += f"**{tag.get_text(strip=True)}**"
#         elif tag.name == 'ul':
#             # Convert <ul> to bullet points
#             for li in tag.find_all('li'):
#                 formatted_text += f"\n- {li.get_text(strip=True)}"
#         elif tag.name == 'br':
#             # Convert <br> to single line break
#             formatted_text += '\n'
#         elif tag.name == 'h1':
#             # Convert <h1> to top-level heading
#             formatted_text += f"\n\n# {tag.get_text(strip=True)}\n"
#         elif tag.name == 'h2':
#             # Convert <h2> to second-level heading
#             formatted_text += f"\n\n## {tag.get_text(strip=True)}\n"
#         elif tag.name == 'h3':
#             # Convert <h3> to third-level heading
#             formatted_text += f"\n\n### {tag.get_text(strip=True)}\n"
#         elif tag.name == 'li':
#             # Convert <li> to list item with bullet point
#             formatted_text += f"\n- {tag.get_text(strip=True)}"
    
#     # Trim leading/trailing whitespace and encode special characters for JSON
#     return formatted_text.strip()

# # Example HTML content
# html_content = """
# <p><strong>Python Developer at Demoat</strong><br />
# <strong>About the job:</strong> Demoa t is seeking a talented and motivated Python Developer to join our growing team. As a Python Developer at Demoa t, you will be responsible for the design, development, and maintenance of various applications and projects.<br />
# <strong>Who We Are:</strong> Demoa t is a forward-thinking organization dedicated to fostering transparent and inclusive civic engagement. We empower communities by facilitating open dialogue and creating platforms for collective decision-making. We value integrity, inclusivity, and innovation, striving to build trust and collaboration among diverse groups.<br />
# <strong>Your New Role:</strong> You will work closely with other developers, product managers, and stakeholders to ensure the timely delivery of high-quality software solutions.<br />
# <strong>Your Role Accountabilities:</strong></p>
# <ul>
# <li>Design, develop, and maintain Python-based applications and services.</li>
# <li>Write clean, well-documented, and testable code adhering to established coding standards and best practices.</li>
# <li>Collaborate with other developers to implement and integrate new features, ensuring smooth integration with existing systems.</li>
# <li>Participate in code reviews and provide constructive feedback, fostering a culture of continuous improvement.</li>
# <li>Work with product managers and stakeholders to gather requirements, define technical specifications, and ensure alignment between development and business needs.</li>
# <li>Troubleshoot and resolve technical issues, identifying root causes and implementing efficient solutions.</li>
# <li>Stay up-to-date with the latest Python technologies and best practices, proactively exploring and adopting new technologies to enhance development efficiency and solution quality.</li>
# <li>Contribute to a positive and collaborative team environment, fostering open communication and knowledge sharing.</li>
# </ul>
# <p><strong>Qualifications & Experience:</strong></p>
# <ul>
# <li>3+ years of professional experience in Python development, demonstrating a strong understanding of Python programming principles, data structures, and algorithms.</li>
# <li>Experience with web frameworks such as Django, Flask, or FastAPI, demonstrating proficiency in building scalable and maintainable web applications.</li>
# </ul>
# """

# formatted_text_content = format_html_content(html_content)

# post_urn = post_job_description_to_linkedin(formatted_text_content)
# print(post_urn)
# comments = get_linkedin_post_comments("urn:li:activity:7123235869976612864", access_token)
# print(comments)
# # data = get_linkedin_post_details("urn:li:activity:7123235869976612864", access_token)
# # print(data)