import requests

def post_job_to_jobspider(job_data, username, password):
    # JobSpider's login URL
    login_url = "https://www.jobspider.com/job/UserLogin.asp"
    
    # Login data
    login_payload = {
        "username": username,
        "password": password
    }
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Attempt login
    login_response = session.post(login_url, data=login_payload)
    if login_response.status_code != 200:
        print(f"Failed to login. Status code: {login_response.status_code}")
        return

    # JobSpider's job posting URL
    post_url = "https://www.jobspider.com/job/PostJob1.asp"

    # Job data to be submitted
    job_payload = {
        "job_title": job_data["title"],
        "job_description": job_data["description"],
        "company_name": job_data["company"],
        "location": job_data["location"],
    }

    # Send POST request to post job
    response = session.post(post_url, data=job_payload)

    # Check response
    if response.status_code == 200:
        print("Job posted successfully!")
    else:
        print(f"Failed to post job. Status code: {response.status_code}")

# Example usage
job_data = {
    "title": "Software Developer",
    "description": "We are looking for a skilled software developer...",
    "company": "Tech Solutions Inc.",
    "location": "New York, NY",
}

username = "Testdemo"
password = "Test@123"

post_job_to_jobspider(job_data, username, password)