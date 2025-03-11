import time
import logging
import json
from bson import ObjectId
from flask import jsonify
from mongo_connection import get_mongo_client
from job_post_scripts.linkedin_jobpost import post_job_description_to_linkedin
from email_test import get_resume,send_mail
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response, send_from_directory
from utils import extract_text_from_pdf
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from celery import Celery
from PyPDF2 import PdfMerger
import uuid

load_dotenv()

app = Flask(__name__)
# Initialize MongoDB connection
mongo_client = get_mongo_client()
db = mongo_client.get_database('recruiter')
jobs_collection = db.get_collection('jobs')
users_collection = db.get_collection('users')
job_description_collection = db.get_collection('job_description')
selected_collection = db.get_collection('selected_candidates')
resume_collection = db.get_collection('resumes')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',filename='app.log',
                    filemode='a')

celery_app = Celery('tasks', broker='redis://localhost:6379/0')


def update_process_status(job_id, status, status_value, log_message=None):
    print(f"update_process_status: {job_id}, {status}, {status_value}, {log_message}")
    try:
        # Log the input parameters
        logging.info(f"Attempting to update job {job_id}: {status} -> {status_value}")

        # Check if the job exists before updating
        job = jobs_collection.find_one({'_id': ObjectId(job_id)})
        if not job:
            print(f"Job {job_id} not found in the database")
            logging.error(f"Job {job_id} not found in the database")
            return
        # Perform the update
        if log_message:
            result = jobs_collection.update_one(
                {'_id': ObjectId(job_id)},
                {'$set': {f'process_status.{status}': status_value, 'log_message': log_message}}
            )
        else:
            result = jobs_collection.update_one(
                {'_id': ObjectId(job_id)},
                {'$set': {f'process_status.{status}': status_value}}
            )

        # Log detailed result information

        if result.modified_count > 0:
            logging.info(f"Successfully updated status for job {job_id}: {status} -> {status_value}")
        else:
            if result.matched_count > 0:
                logging.warning(f"Job {job_id} found but not modified. Current value might be the same as the new value.")
            else:
                logging.info(f"Update result: matched={result.matched_count}, modified={result.modified_count}")
                logging.error(f"Failed to update status for job {job_id}: {status} -> {status_value}. Job not found or no changes made.")
        # Log the updated job document
        updated_job = jobs_collection.find_one({'_id': ObjectId(job_id)})
        logging.info(f"Updated job document: {updated_job}")

    except Exception as e:
        print(f"Error updating process status for job {job_id}: {str(e)}")
        logging.error(f"Error updating process status for job {job_id}: {str(e)}", exc_info=True)

def update_job_description(job_id):
    logging.info(f"Starting job description update for job {job_id}")
    update_process_status(job_id, "Creating Job description", "in_progress")
    try:
        time.sleep(5)  # Simulating work
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
        logging.info(f"Job: {job}")

        if not job:
            raise ValueError(f"Job {job_id} not found")
        job_description = job['job_info']

        logging.info(f"Job description: {job_description}")
        status = 201            # post_job_description_to_linkedin(job_description)
        logging.info(f"Status: {status}")
        if status == 201:
            logging.info(f"Job {job_id} posted successfully to LinkedIn")
            update_process_status(job_id, "Job posting", "done")

            current_date = datetime.now()
            end_date = current_date + timedelta(minutes=5)
            print(f"======== current_date {current_date}")
            print(f"======== end_date: {end_date}")
            jobs_collection.update_one(
                {'_id': ObjectId(job_id)},
                {'$set': {
                    'posting_date': current_date,
                    'end_date': end_date
                }}
            )
            logging.info(f"Updated posting dates for job {job_id}")
        else:
            logging.error(f"Error posting job {job_id} to LinkedIn: status code {status}")
            update_process_status(job_id, "Job posting", "failed")
    except Exception as e:
        logging.info(f"Error in job posting process for job {job_id}: {str(e)}")
        update_process_status(job_id, "Job posting", "failed")



@celery_app.task
def update_getting_resumes_celery(job_id):
    print(f"update_getting_resumes_celery: {job_id}")
    update_getting_resumes(job_id)
    print(f"update getting resumes done")
    update_matching_resumes(job_id)
    print("update matching resumes done")
    update_sending_resumes(job_id)
    print("update sending resumes done")


#get resumes from the gmail after 10 days from the posting date
def update_getting_resumes(job_id):
    print("Getting Resumes from the Emails")
    logging.info(f"Starting resume retrieval for job {job_id}")
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    
    if not job:
        print(f"Job {job_id} not found")
        return
    if job['process_status']['Job posting'] != "done":
        print(f"Job posting not completed for job {job_id}. Skipping resume retrieval.")
        return

    update_process_status(job_id, "Getting resumes from portal", "in_progress")
    
    if 'end_date' in job:
        end_date = job['end_date']
        tomorrow = datetime.now()
        # end_date = datetime.now() 
        # tomorrow = datetime.now() 
        
        if end_date.date() == tomorrow.date():
        
            print(f"End date {end_date} matches tomorrow for job {job_id}. Running email attachment retrieval.")
            try:
                get_resume(f"job_{str(job_id)}")
                print(f"Email attachments retrieved successfully for job {job_id}")
                update_process_status(job_id, "Getting resumes from portal", "done")
            except Exception as e:
                print(f"Error retrieving email attachments for job {job_id}: {str(e)}")
                print(f"Error retrieving email attachments for job {job_id}: {str(e)}")
                update_process_status(job_id, "Getting resumes from portal", "in_progress")
        else:
            print(f"End date {end_date} does not match tomorrow for job {job_id}. Keeping status as in_progress.")
            
            update_process_status(job_id, "Getting resumes from portal", "in_progress", log_message=f"This process will run on {end_date.date()}")
    else:
        print(f"End date not set for job {job_id}. Keeping status as in_progress.")
    
    resumes_dir = 'attachments'
    print(" Getting Resumes done !")
    if not os.path.exists(resumes_dir) or not os.listdir(resumes_dir):
        print(f"No resumes found for job {job_id}. Keeping status as in_progress.")
        update_process_status(job_id, "Matching resumes with job description", "not_started")
        update_process_status(job_id, "Sending resumes to your email", "not_started")

def update_matching_resumes(job_id):
    logging.info(f"Starting Resume matching for job {job_id}")
    print(f"Starting Resume matching for job {job_id}")
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    
    user_id= job['userid']
   
    if not job:
        logging.error(f"Job {job_id} not found")
        print(f"Job {job_id} not found")
        return
    # if job['process_status']['Getting resumes from portal'] != "done":
    #     logging.warning(f"Resume retrieval not completed for job {job_id}. Skipping matching process.")
    #     print(f"Resume retrieval not completed for job {job_id}. Skipping matching process.")
    #     return

    update_process_status(job_id, "Matching resumes with job description", "in_progress")
    try:
        job_description = job['job_info']
        resumes_dir = f'attachments/job_{job_id}'
        collected_resumes = [f for f in os.listdir(resumes_dir) if f.endswith('.pdf')]

        job_title = job.get('job_title')
        user_id= job['userid']
        try:
            resume_result = resume_collection.update_one(
                {
                'user_id': user_id, 
                'job_title': job_title},  # Filter criteria
                {'$set': {'collected_resumes': collected_resumes}},  # Update operation
                upsert=True  # Inserts if the document doesn't exist
            )

        except:
            print(f"An error occurred when store resume: {e}")
            return jsonify({"error": "An error occurred during processing"}), 500


        logging.info(f"Found {len(collected_resumes)} resumes for job {job_id}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
        current_job = jobs_collection.find_one({'_id': ObjectId(job_id)})
        
        matched_resumes = []
        top_candidates =[]
        
        for resume in collected_resumes:
            try:
                with open(os.path.join(resumes_dir, resume), 'rb') as file:
                    resume_text = extract_text_from_pdf(file)
                    
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"""Compare the following resume with the job description and determine if it's a good match. 
                            Job Description: {job_description}
                            Resume: `{resume_text}`
                            
                            
                            Provide a score from 0 to 100 indicating how well the resume matches the job description, 
                            and a brief explanation of your reasoning. Return your response in the following json format:
                            job_title: [job title]
                            email:[candidate email]
                            name: [name of the candidate]
                            Score: [score]
                            Explanation: [your explanation]
                            """
                        }]
                    }]
                }

                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=payload, headers=headers)
                result = response.json()['candidates'][0]['content']['parts'][0]['text']
                result = json.loads(result.replace("```json", "").replace("```", ""))
                
                print("  Result :\n\n", result)
                name = result['name']
                score = int(result['Score'])
                job_title = result['job_title']
                email = result['email']

                if score >= 60:
                    candidate = {
                        "candidate_id": str(uuid.uuid4()),
                        "candidate_name": name,
                        "email": email,
                        "score": score,
                        "filename": resume,
                        "status": "Pending",  # Default status
                        "interview_date": None
                    }
                    top_candidates.append(candidate)

                
                matched_resumes.append({
                    "filename": resume,
                    "score": score,
                    "analysis": result['Explanation'],
                    "candidate_name": name
                })
                logging.info(f"Resume {resume} matched with score {score} for job {job_id}")
                print(" Resume Matched!\n", matched_resumes)
                
            except Exception as e:
                print(f"Error processing resume {resume} for job {job_id}: {str(e)}")
                logging.error(f"Error processing resume {resume} for job {job_id}: {str(e)}")

        print(" Selected candidates:    List ", top_candidates)
        update_process_status(job_id, "Matching resumes with job description", "done")
        logging.info(f"Resume matching completed for job {job_id}. Matched {len(matched_resumes)} resumes.")
        jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {'matched_resumes': matched_resumes}}
        )
       
        # Clear existing selected candidates for this job before inserting new ones
        selected_collection.delete_many({'job_id': str(job_id)})
        
        # Insert new selected candidates
        if top_candidates:
            selected_collection.insert_one({
                'job_id': job_id,
                'user_id': user_id,
                'job_title': job_title,
                'selected_candidates': top_candidates
                
            })
            print(f"Inserted {len(top_candidates)} selected candidates")

        update_process_status(job_id, "Matching resumes with job description", "done")
        logging.info(f"Resume matching completed for job {job_id}. Matched {len(matched_resumes)} resumes.")
        
        return top_candidates
    
    except Exception as e:
        import traceback
        print(f"Error in resume matching process for job {job_id}: {str(e)} \n {traceback.format_exc()}")
        logging.error(f"Error in resume matching process for job {job_id}: {str(e)} \n {traceback.format_exc()}")
        update_process_status(job_id, "Matching resumes with job description", "in_progress")

def combine_pdfs(file_paths, output_path):
    try:
        merger = PdfMerger()
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"File {file_path} does not exist. Skipping.")
                continue  # Skip files that do not exist
            merger.append(file_path)
        merger.write(output_path)
        merger.close()
        print(f"Combined PDF created successfully at {output_path}")
        return True
    except Exception as e:
        print(f"Error combining PDFs: {str(e)}")
        return False

def update_sending_resumes(job_id):
    logging.info(f"Starting resume sending process for job {job_id}")
    print(f"Starting resume sending process for job {job_id}")
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    user = users_collection.find_one({'_id': ObjectId(job['userid'])})
    if not job:
        logging.error(f"Job {job_id} not found")
        print(f"Job not found")
        return
    if job['process_status']['Matching resumes with job description'] != "done":
        print(f"Resume matching process is  not completed")
        logging.warning(f"Resume matching not completed for job {job_id}. Skipping sending process.")
        return

    update_process_status(job_id, "Sending resumes to your email", "in_progress")
    resumes_dir = f'resumes/job_{job_id}'
    
    if not os.path.exists(resumes_dir):
        os.makedirs(resumes_dir)
    
    matched_resumes = job.get('matched_resumes', [])
    file_paths = [f'attachments/job_{job_id}/{resume["filename"]}' for resume in matched_resumes if int(resume['score']) >= 60]
   
    # Save Combined PDFs in this Path
    combined_pdf_path = os.path.join(resumes_dir, f"combined_resumes_{job_id}.pdf")

    print(" File Path is : ", file_paths)
    print(" combined_pdf_path : ", combined_pdf_path)
    # Call the combine_pdfs function
    if not combine_pdfs(file_paths, combined_pdf_path):
        print("Error in combining PDFs.")
        update_process_status(job_id, "Sending resumes to your email", "in_progress")
        return

    try:
        print(" Sending Mail to Matched Resumes")
        send_mail(user['email'], 
                  "Matched Resumes for Your Job Posting",
                  "Here are the matched resumes for your job posting.",
                  attachment_paths=[combined_pdf_path])
        update_process_status(job_id, "Sending resumes to your email", "done")
        logging.info(f"Resumes sent successfully for job {job_id}")
        print("Resumes sent successfully")
    except Exception as e:
        logging.error(f"Error sending resumes for job {job_id}: {str(e)}")
        print(f"Error sending resumes for job {job_id}: {str(e)}")
        update_process_status(job_id, "Sending resumes to your email", "in_progress")

@celery_app.task
def task_update_getting_resumes(job_id):
    update_getting_resumes(job_id)

@celery_app.task
def task_update_matching_resumes(job_id):
    update_matching_resumes(job_id)

@celery_app.task
def task_update_sending_resumes(job_id):
    update_sending_resumes(job_id)

def check_enddate():
    logging.info("Starting end date check for all jobs")
    current_date = datetime.now().date()
    
    jobs = jobs_collection.find({'end_date': {'$lte': current_date}})
    
    for job in jobs:
        job_id = str(job['_id'])
        logging.info(f"Processing job {job_id} with end date {job['end_date']}")
        
        # Chain the tasks
        chain = (
            task_update_getting_resumes.s(job_id) |
            task_update_matching_resumes.s(job_id) |
            task_update_sending_resumes.s(job_id)
        )
        chain.apply_async()

    logging.info("End date check completed")

# Schedule the check_enddate function to run daily
# @celery_app.task
# def scheduled_check_enddate():
#     check_enddate()

# Set up the scheduled task
celery_app.conf.beat_schedule = {
    'check-enddate-daily': {
        'task': 'process.scheduled_check_enddate',
        'schedule': 86400,  # 24 hours in seconds
    },
}

# if __name__ == "__main__":
    # get_resume('job_67a5fdf0a26dd6fdefaf5c80')
    # update_getting_resumes_celery('67a5fdf0a26dd6fdefaf5c80')
    # update_getting_resumes('67a5fdf0a26dd6fdefaf5c80')
    # update_matching_resumes('67a5fdf0a26dd6fdefaf5c80')
    # update_sending_resumes('67a5fdf0a26dd6fdefaf5c80')
    
    