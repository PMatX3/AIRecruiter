import time
import logging
from bson import ObjectId
from flask import jsonify
from mongo_connection import get_mongo_client
from job_post_scripts.linkedin_jobpost import post_job_description_to_linkedin
from email_test import send_mail, get_resume
from flask import session
from utils import extract_text_from_pdf
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Initialize MongoDB connection
mongo_client = get_mongo_client()
db = mongo_client.get_database('recruiter')
jobs_collection = db.get_collection('jobs')
job_description_collection = db.get_collection('job_description')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_process_status(job_id, status, status_value):
    try:
        result = jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {f'process_status.{status}': status_value}}
        )
        if result.modified_count > 0:
            logging.info(f"Updated status for job {job_id}: {status} -> {status_value}")
        else:
            logging.warning(f"Failed to update status for job {job_id}: {status} -> {status_value}")
    except Exception as e:
        logging.error(f"Error updating process status for job {job_id}: {str(e)}")

def update_job_description(job_id):
    logging.info(f"Starting job description update for job {job_id}")
    update_process_status(job_id, "Creating Job description", "in_progress")
    try:
        time.sleep(10)  # Simulating work
        update_process_status(job_id, "Creating Job description", "done")
        logging.info(f"Job description update completed for job {job_id}")
    except Exception as e:
        logging.error(f"Error updating job description for job {job_id}: {str(e)}")
        update_process_status(job_id, "Creating Job description", "in_progress")

def update_job_posting(job_id):
    logging.info(f"Starting job posting update for job {job_id}")
    update_process_status(job_id, "Job posting", "in_progress")
    try:
        job = jobs_collection.find_one({'_id': ObjectId(job_id)})
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job_description = job['job_info']
        status = post_job_description_to_linkedin(job_description)
        if status == 201:
            logging.info(f"Job {job_id} posted successfully to LinkedIn")
            update_process_status(job_id, "Job posting", "done")

            current_date = datetime.now()
            end_date = current_date + timedelta(days=10)

            jobs_collection.update_one(
                {'_id': ObjectId(job_id)},
                {'$set': {
                    'posting_date': current_date,
                    'end_date': end_date
                }}
            )
            logging.info(f"Updated posting dates for job {job_id}")
            
            time_to_sleep = (end_date - current_date).total_seconds()
            logging.info(f"Sleeping for {time_to_sleep} seconds until end date for job {job_id}")
            time.sleep(time_to_sleep)
        else:
            logging.error(f"Error posting job {job_id} to LinkedIn: status code {status}")
            update_process_status(job_id, "Job posting", "in_progress")
    except Exception as e:
        logging.error(f"Error in job posting process for job {job_id}: {str(e)}")
        update_process_status(job_id, "Job posting", "in_progress")

def update_getting_resumes(job_id):
    logging.info(f"Starting resume retrieval for job {job_id}")
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if not job:
        logging.error(f"Job {job_id} not found")
        return
    if job['process_status']['Job posting'] != "done":
        logging.warning(f"Job posting not completed for job {job_id}. Skipping resume retrieval.")
        return

    update_process_status(job_id, "Getting resumes from portal", "in_progress")
    from datetime import datetime, timedelta    
    
    if 'end_date' in job:
        end_date = job['end_date']
        tomorrow = datetime.now() + timedelta(days=1)
        
        if end_date.date() == tomorrow.date():
            logging.info(f"End date {end_date} matches tomorrow for job {job_id}. Running email attachment retrieval.")
            try:
                get_resume()
                logging.info(f"Email attachments retrieved successfully for job {job_id}")
                update_process_status(job_id, "Getting resumes from portal", "done")
            except Exception as e:
                logging.error(f"Error retrieving email attachments for job {job_id}: {str(e)}")
                update_process_status(job_id, "Getting resumes from portal", "in_progress")
        else:
            logging.info(f"End date {end_date} does not match tomorrow for job {job_id}. Keeping status as in_progress.")
    else:
        logging.warning(f"End date not set for job {job_id}. Keeping status as in_progress.")
    
    resumes_dir = 'attachments'
    if not os.path.exists(resumes_dir) or not os.listdir(resumes_dir):
        logging.warning(f"No resumes found for job {job_id}. Keeping status as in_progress.")
        update_process_status(job_id, "Matching resumes with job description", "not_started")
        update_process_status(job_id, "Sending resumes to your email", "not_started")

def update_matching_resumes(job_id):
    logging.info(f"Starting resume matching for job {job_id}")
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if not job:
        logging.error(f"Job {job_id} not found")
        return
    if job['process_status']['Getting resumes from portal'] != "done":
        logging.warning(f"Resume retrieval not completed for job {job_id}. Skipping matching process.")
        return

    update_process_status(job_id, "Matching resumes with job description", "in_progress")
    try:
        job_description = job['job_description']
        resumes_dir = 'attachments'
        collected_resumes = [f for f in os.listdir(resumes_dir) if f.endswith('.pdf')]
        logging.info(f"Found {len(collected_resumes)} resumes for job {job_id}")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
        matched_resumes = []

        for resume in collected_resumes:
            try:
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
                response.raise_for_status()
                result = response.json()['candidates'][0]['content']['parts'][0]['text']

                score = int(result.split('\n')[0].split(':')[1].strip())
                if score >= 70:
                    matched_resumes.append((resume, score, result))
                    logging.info(f"Resume {resume} matched with score {score} for job {job_id}")
            except Exception as e:
                logging.error(f"Error processing resume {resume} for job {job_id}: {str(e)}")

        matched_resumes.sort(key=lambda x: x[1], reverse=True)
        jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {'matched_resumes': [{'filename': r[0], 'score': r[1], 'analysis': r[2]} for r in matched_resumes]}}
        )
        update_process_status(job_id, "Matching resumes with job description", "done")
        logging.info(f"Resume matching completed for job {job_id}. Matched {len(matched_resumes)} resumes.")
    except Exception as e:
        logging.error(f"Error in resume matching process for job {job_id}: {str(e)}")
        update_process_status(job_id, "Matching resumes with job description", "in_progress")

def update_sending_resumes(job_id):
    logging.info(f"Starting resume sending process for job {job_id}")
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if not job:
        logging.error(f"Job {job_id} not found")
        return
    if job['process_status']['Matching resumes with job description'] != "done":
        logging.warning(f"Resume matching not completed for job {job_id}. Skipping sending process.")
        return

    update_process_status(job_id, "Sending resumes to your email", "in_progress")
    try:
        send_mail(session['user']['email'], 
                  "Matched Resumes for Your Job Posting",
                  "Here are the matched resumes for your job posting.",
                  attachment_path=None)
        update_process_status(job_id, "Sending resumes to your email", "done")
        logging.info(f"Resumes sent successfully for job {job_id}")
    except Exception as e:
        logging.error(f"Error sending resumes for job {job_id}: {str(e)}")
        update_process_status(job_id, "Sending resumes to your email", "in_progress")