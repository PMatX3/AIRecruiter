import time
from bson import ObjectId
from flask import jsonify
from mongo_connection import get_mongo_client

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
    time.sleep(5)  # Simulating work
    update_process_status(job_id, "Creating Job description", "done")

def update_job_posting(job_id):
    update_process_status(job_id, "Job posting", "in_progress")
    time.sleep(5)  # Simulating work
    update_process_status(job_id, "Job posting", "done")

def update_getting_resumes(job_id):
    update_process_status(job_id, "Getting resumes from portal", "in_progress")
    time.sleep(5)  # Simulating work
    update_process_status(job_id, "Getting resumes from portal", "done")

def update_matching_resumes(job_id):
    update_process_status(job_id, "Matching resumes with job description", "in_progress")
    time.sleep(5)  # Simulating work
    update_process_status(job_id, "Matching resumes with job description", "done")

def update_sending_resumes(job_id):
    update_process_status(job_id, "Sending resumes to your email", "in_progress")
    time.sleep(5)  # Simulating work
    update_process_status(job_id, "Sending resumes to your email", "done")