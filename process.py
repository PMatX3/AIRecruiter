import time
from bson import ObjectId
from flask import jsonify
from mongo_connection import get_mongo_client
from linkedin_jobpost import post_job_description_to_linkedin
from email_test import send_mail,get_resume
from flask import session

# Initialize MongoDB connection
mongo_client = get_mongo_client()
db = mongo_client.get_database('recruiter')
jobs_collection = db.get_collection('jobs')
job_description_collection = db.get_collection('job_description')

def update_process_status(job_id, status, status_value):
    jobs_collection.update_one(
        {'_id': ObjectId(job_id)},
        {'$set': {f'process_status.{status}': status_value}}
    )

def update_job_description(job_id):
    update_process_status(job_id, "Creating Job description", "in_progress")
    time.sleep(10)  # Simulating work
    update_process_status(job_id, "Creating Job description", "done")

def update_job_posting(job_id):
    update_process_status(job_id, "Job posting", "in_progress")
    job_description = jobs_collection.find_one({'_id': ObjectId(job_id)})['job_info']
    status = post_job_description_to_linkedin(job_description)
    if status == 201:
        print("Job posted successfully")
        update_process_status(job_id, "Job posting", "done")
        
        from datetime import datetime, timedelta

        # Get the current date and the date 10 days from now
        current_date = datetime.now()
        end_date = current_date + timedelta(days=10)

        # Update the job collection with the posting dates
        jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {
                'posting_date': current_date,
                'end_date': end_date
            }}
        )
    else:
        print(f"Error posting job: {status}")
        update_process_status(job_id, "Job posting", "in_progress")

def update_getting_resumes(job_id):
    import os  # Add this import at the top of the file
    
    # Check if job posting is completed
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if job['process_status']['Job posting'] != "done":
        print("Job posting is not completed. Skipping resume retrieval.")
        return

    update_process_status(job_id, "Getting resumes from portal", "in_progress")
    from datetime import datetime, timedelta    
    
    if job and 'end_date' in job:
        end_date = job['end_date']
        tomorrow = datetime.now() + timedelta(days=1)
        
        # Check if the end date matches tomorrow
        if end_date.date() == tomorrow.date():
            print(f"End date {end_date} matches tomorrow. Running email attachment retrieval.")
            
            # Run the email attachment retrieval function
            try:
                get_resume()  # Assuming this is the function to retrieve attachments from Gmail
                print("Email attachments retrieved successfully.")
                update_process_status(job_id, "Getting resumes from portal", "done")
            except Exception as e:
                print(f"Error retrieving email attachments: {str(e)}")
                update_process_status(job_id, "Getting resumes from portal", "in_progress")
        else:
            print(f"End date {end_date} does not match tomorrow. Keeping status as in_progress.")
    else:
        print("Job not found or end date not set. Keeping status as in_progress.")
    
    # Check if any resumes were found
    resumes_dir = 'attachments'
    if not os.path.exists(resumes_dir) or not os.listdir(resumes_dir):
        print("No resumes found. Keeping status as in_progress.")
        # Set subsequent processes to "not_started"
        update_process_status(job_id, "Matching resumes with job description", "not_started")
        update_process_status(job_id, "Sending resumes to your email", "not_started")

def update_matching_resumes(job_id):
    # Check if getting resumes is done
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if job['process_status']['Getting resumes from portal'] != "done":
        print("Getting resumes is not done. Skipping matching process.")
        return

    update_process_status(job_id, "Matching resumes with job description", "in_progress")
    # Get the job description
    job_description = job['job_description']

    # Get the collected resumes
    resumes_dir = 'attachments'  # Directory where resumes are stored
    collected_resumes = [f for f in os.listdir(resumes_dir) if f.endswith('.pdf')]

    # Use Gemini AI to match resumes with the job description
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

    matched_resumes = []
    for resume in collected_resumes:
        with open(os.path.join(resumes_dir, resume), 'rb') as file:
            resume_text = extract_text_from_pdf(file)

        payload = {
            "contents": [{
                "parts": [{
                    "text": f"""Compare the following resume with the job description and determine if it's a good match. 
                    Job Description: {job_description}
                    Resume: {resume_text}
                    
                    Provide a score from 0 to 100 indicating how well the resume matches the job description, 
                    and a brief explanation of your reasoning. Return your response in the following format:
                    Score: [score]
                    Explanation: [your explanation]
                    """
                }]
            }]
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()['candidates'][0]['content']['parts'][0]['text']

        score = int(result.split('\n')[0].split(':')[1].strip())
        if score >= 70:  # Consider resumes with a score of 70 or higher as good matches
            matched_resumes.append((resume, score, result))

    # Sort matched resumes by score in descending order
    matched_resumes.sort(key=lambda x: x[1], reverse=True)

    # Update the job document with matched resumes
    jobs_collection.update_one(
        {'_id': ObjectId(job_id)},
        {'$set': {'matched_resumes': [{'filename': r[0], 'score': r[1], 'analysis': r[2]} for r in matched_resumes]}}
    )
    update_process_status(job_id, "Matching resumes with job description", "done")

def update_sending_resumes(job_id):
    # Check if matching resumes is done
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if job['process_status']['Matching resumes with job description'] != "done":
        print("Matching resumes is not done. Skipping sending process.")
        return

    update_process_status(job_id, "Sending resumes to your email", "in_progress")
    send_mail(session['user']['email'], 
              "Matched Resumes for Your Job Posting",
              "Here are the matched resumes for your job posting.",
              attachment_path=None)  # We'll add attachment handling later if needed
    update_process_status(job_id, "Sending resumes to your email", "done")