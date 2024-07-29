from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response, send_from_directory
import speech_recognition as sr
from pydub import AudioSegment
import openai
from openai import OpenAI
import json
import os, time
import requests
from flask_socketio import SocketIO, emit
from utils import extract_text_from_pdf, save_resumes_embedding, get_results
from mongo_connection import get_mongo_client
from dotenv import load_dotenv
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.footnote import footnote_plugin
from IPython.display import Markdown
import textwrap
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from process import (
    update_job_description,
    update_job_posting,
    update_getting_resumes,
    update_matching_resumes,
    update_sending_resumes,
    update_process_status
)
from datetime import datetime
import base64
import io
from PyPDF2 import PdfReader
from celery import Celery
from celery.app.control import Inspect

# Load environment variables
load_dotenv()

AudioSegment.converter = "ffmpeg.exe"
AudioSegment.ffmpeg = "ffmpeg.exe"  # Some versions of pydub might require setting this as well
AudioSegment.ffprobe ="ffprobe.exe"  # ffprobe is part of ffmpeg and might also need to be specified

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
app.secret_key = os.getenv("SECRET_KEY")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
app.config['REQUEST_TIMEOUT'] = 300  # 5 minutes timeout
jwt = JWTManager(app)

mongo_client = get_mongo_client()
db = mongo_client.get_database('recruiter')
users_collection = db.get_collection('users') if db.get_collection('users') is not None else db.create_collection('users')
text_data_collection = db.get_collection('text_data') if db.get_collection('text_data') is not None else db.create_collection('text_data')
process_collection = db.get_collection('process') if db.get_collection('process') is not None else db.create_collection('process')
jobs_collection = db.get_collection('jobs') if db.get_collection('jobs') is not None else db.create_collection('jobs')

openai_client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

md = (
    MarkdownIt('commonmark' ,{'breaks':True,'html':True})
    .use(front_matter_plugin)
    .use(footnote_plugin)
    .enable('table')
)

# Simulated process status
process_status = {
    "Creating Job description": "not_started",
    "Job posting": "not_started",
    "Getting resumes from portal": "not_started",
    "Matching resumes with job description": "not_started",
    "Sending resumes to your email": "not_started"
}

# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

def extract_job_info(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

    # Payload to be sent in the POST request
    payload = {"contents":[{"parts":[{"text":f"""Extract job information from the following text: {text}. Ensure to extract and include the following details but if not, don't include that section, formatted in markdown:

    About the job: Provide the job introduction.
    Who We Are: Offer a brief overview of the company.
    Your New Role: Describe the job role.
    Your Role Accountabilities: List the responsibilities and accountabilities.
    Qualifications & Experience: Detail the required qualifications and experience.
    Hybrid Working: Describe the working conditions.
    How We Get Things Done: Summarize the company's guiding principles.
    Championing Inclusion at [Company]: Include the company's diversity and inclusion statement.
    For inquiries, include the contact email and mobile number if available.
    Ensure the output includes:

    Job title (if available)
    Complete description with all specified sections
    Email (if available)
    Mobile (if available)
    If any of the sections are not specified in the text, don't include that respective section. The generated job description must contain all the points mentioned above and be presented in proper markdown format. I want to extract minimum text from the text provided."""}]}]}
    
    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(url, data=json.dumps(payload), headers=headers)
    all_items = res.json()['candidates'][0]['content']['parts'][0]['text']
    print(all_items)
    return all_items

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('registration.html')
    data = request.get_json()
    username = data.get('username')
    phone = data.get('phone')
    email = data.get('email')
    password = data.get('password')

    if users_collection.find_one({'username': username}):
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = generate_password_hash(password)
    users_collection.insert_one({'username': username, 'phone': phone, 'email': email, 'password': hashed_password})
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    data = request.get_json()
    username = data.get('email')
    password = data.get('password')

    user = users_collection.find_one({'email': username})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    user['_id'] = str(user['_id'])
    session['user'] = user
    access_token = create_access_token(identity=username)

    # Check if any process is in progress
    job = jobs_collection.find_one({'userid': user['_id'], 'process_status': {'$elemMatch': {'$eq': 'in_progress'}}})
    if job:
        return redirect('/process')

    return jsonify({'access_token': access_token}), 200

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

def create_or_get_job(user_id, job_info):
    # Find the highest job number for this user
    highest_job = jobs_collection.find_one(
        {'userid': user_id},
        sort=[('job_title', -1)]
    )

    if highest_job:
        job_number = int(highest_job['job_title'].split('_')[1]) + 1
    else:
        job_number = 1

    job_title = f'job_{job_number:03d}'

    existing_job = jobs_collection.find_one({
        'userid': user_id,
        'process_status.Creating Job description': 'not_started'
    })
    
    if existing_job:
        jobs_collection.update_one(
            {'_id': existing_job['_id']},
            {'$set': {'job_info': job_info, 'job_title': job_title}}
        )
        return str(existing_job['_id'])
    else:
        new_job = {
            'userid': user_id,
            'created_at': datetime.utcnow(),
            'job_info': job_info,
            'job_title': job_title,
            'edited': False,
            'process_status': {
                "Creating Job description": "not_started",
                "Job posting": "not_started",
                "Getting resumes from portal": "not_started",
                "Matching resumes with job description": "not_started",
                "Sending resumes to your email": "not_started"
            }
        }
        result = jobs_collection.insert_one(new_job)
        return str(result.inserted_id)

@app.route('/audio-to-text', methods=['POST'])
def audio_to_text():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        # Save the uploaded file temporarily
        temp_filename = 'temp_audio.' + file.filename.split('.')[-1]
        file.save(temp_filename)

        # Convert the audio to WAV format
        audio = AudioSegment.from_file(temp_filename)
        audio.export("temp_audio.wav", format="wav")

        # Perform speech recognition
        recognizer = sr.Recognizer()
        with sr.AudioFile("temp_audio.wav") as source:
            audio_data = recognizer.record(source)
        
        try:
            text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return jsonify({'error': 'Speech recognition could not understand the audio'})
        except sr.RequestError:
            return jsonify({'error': 'Could not request results from speech recognition service'})

        # Clean up temporary files
        os.remove(temp_filename)
        os.remove("temp_audio.wav")

        # Save the extracted text to the database
        text_data_collection.insert_one({'user_id': session['user']['_id'], 'text': text})

        # Extract job information
        job_info = extract_job_info(text)
        
        # Create or get job ID
        job_id = create_or_get_job(session['user']['_id'], job_info)

        return jsonify({'message': 'Audio processed and text saved to database.', 'job_id': job_id})

@app.route('/pdf-to-text', methods=['POST'])
def pdf_to_text():
    print("PDF to text conversion started")
    try:
        data = request.json
        print(f"Received data: {data.keys()}")
        
        if 'content' not in data:
            print("Error: No file content in the request")
            return jsonify({'error': 'No file content'}), 400
        
        file_name = data.get('name', 'unnamed.pdf')
        file_content = data['content']
        
        print(f"Processing file: {file_name}")
        
        # Decode base64 content
        pdf_bytes = base64.b64decode(file_content)
        pdf_file = io.BytesIO(pdf_bytes)
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_file)
        print(f"Text extracted from PDF, length: {len(text)}")

        # Save the extracted text to the database
        result = text_data_collection.insert_one({'user_id': session['user']['_id'], 'text': text})
        print(f"Text saved to database with ID: {result.inserted_id}")

        # Extract job information
        job_info = extract_job_info(text)
        print("Job information extracted")
        
        # Create or get job ID
        job_id = create_or_get_job(session['user']['_id'], job_info)
        print(f"Job created or retrieved with ID: {job_id}")

        print("PDF processing completed successfully")
        return jsonify({'message': 'PDF processed and text saved to database.', 'job_id': job_id})
    except Exception as e:
        import traceback
        print(f"Error in PDF to text conversion: {str(e)}")
        print(traceback.format_exc())  # This will print the full stack trace
        return jsonify({'error': 'An error occurred during PDF processing'}), 500

@app.route('/save-resumes-embedding', methods=['GET'])
def save_resumes():
    save_resumes_embedding()
    return jsonify({'message': 'Resumes embedding saved.'})

@app.route('/get-resumes', methods=['GET'])
def get_resumes():
    query = request.args.get('query')
    resumes = get_results(query)

    return resumes

@app.route('/chat', methods=['POST'])
def chat():
    query = request.json['query']
    
    def generate():
        entire_response = ''
        with open('extracted_text.txt', 'r', encoding='utf-8') as file:
            job_info_json = file.read()
        for message in get_results(query, job_info_json):
            yield message

    return Response(generate(), mimetype='text/event-stream')

def get_process_status(job_id):
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if job:
        return job['process_status']
    return None

def reset_process_status(job_id):
    process_status = {
        "Creating Job description": "not_started",
        "Job posting": "not_started",
        "Getting resumes from portal": "not_started",
        "Matching resumes with job description": "not_started",
        "Sending resumes to your email": "not_started"
    }
    jobs_collection.update_one(
        {'_id': ObjectId(job_id)},
        {'$set': {'process_status': process_status}}
    )

@app.route('/process')
def demo():
    return render_template('process.html')

@app.route('/get_jobdesc/<job_id>', methods=['GET'])
def get_jobdesc(job_id):
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if job:
        return jsonify({'description': md.render(job['job_info']), 'edited': job['edited']})
    else:
        return jsonify({'error': 'Job description not found'}), 404

@app.route('/update_jobdesc', methods=['POST'])
def update_jobdesc():
    data = request.get_json()
    new_desc = data['text']
    job_id = data.get('job_id')
    
    if not job_id:
        return jsonify({'error': 'Job ID is required'}), 400
    
    result = jobs_collection.update_one(
        {'_id': ObjectId(job_id)},
        {'$set': {'job_info': new_desc, 'edited': True}}
    )
    
    if result.modified_count > 0:
        return jsonify({'message': 'Job description updated successfully.'})
    else:
        return jsonify({'error': 'Job not found or no changes made.'}), 404

@app.route('/start-process', methods=['GET'])
def start_process():
    # Get all jobs from the collection
    all_jobs = jobs_collection.find({})
    
    # Get the list of job IDs that are currently being processed
    active_tasks = []
    active_dict = celery.control.inspect().active()
    print(active_dict)
    if active_dict:
        active_tasks = [task.id for tasks in active_dict.values() for task in tasks]
    
    for job in all_jobs:
        job_id = str(job['_id'])
        
        # Check if the job is already completed or in progress
        if any(status == "done" for status in job['process_status'].values()) or job_id in active_tasks:
            print(f"Job {job_id} is already completed or in progress")
            continue
        
        # Update the job with process status
        jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {
                'process_status': {
                    "Creating Job description": "not_started",
                    "Job posting": "not_started",
                    "Getting resumes from portal": "not_started",
                    "Matching resumes with job description": "not_started",
                    "Sending resumes to your email": "not_started"
                }
            }}
        )
        
        # Start the process as a Celery task
        run_process.delay(job_id)

    return jsonify({'message': 'Process started for all unprocessed jobs.'})

@celery.task
def run_process(job_id):
    update_job_description(job_id)
    update_job_posting(job_id)
    update_getting_resumes(job_id)
    update_matching_resumes(job_id)
    update_sending_resumes(job_id)

def check_and_queue_in_progress_jobs():
    try:
        # Ensure Celery app is properly initialized
        if not celery or not celery.control:
            print("Celery app is not properly initialized. Skipping task queue check.")
            return

        # Check if Celery worker is running
        try:
            celery.control.ping(timeout=1)
        except TimeoutError:
            print("No Celery workers are currently running. Please start a Celery worker.")
            return

        # Get all active and reserved tasks
        i = Inspect(app=celery)
        active_tasks = i.active() or {}
        reserved_tasks = i.reserved() or {}
        
        # Combine all task IDs
        all_task_ids = set()
        all_task_ids.update([task['id'] for worker_tasks in active_tasks.values() for task in worker_tasks])
        all_task_ids.update([task['id'] for worker_tasks in reserved_tasks.values() for task in worker_tasks])

        print(f"Current active and reserved tasks: {all_task_ids}")

        # Find all jobs with in-progress or not_started status
        in_progress_jobs = jobs_collection.find({
            "$or": [
                { "process_status.Creating Job description": { "$in": ["not_started", "in_progress"] } },
                { "process_status.Job posting": { "$in": ["not_started", "in_progress"] } },
                { "process_status.Getting resumes from portal": { "$in": ["not_started", "in_progress"] } },
                { "process_status.Matching resumes with job description": { "$in": ["not_started", "in_progress"] } },
                { "process_status.Sending resumes to your email": { "$in": ["not_started", "in_progress"] } }
            ]
        });
        for job in in_progress_jobs:
            job_id = str(job['_id'])
            
            # Check if this job is already in the Celery queue or running
            if job_id not in all_task_ids:
                # If not, add it to the Celery queue
                run_process.apply_async((job_id,), task_id=job_id)
                print(f"Added job {job_id} to Celery queue")
            else:
                print(f"Job {job_id} is already in progress or queued")

        print(f"Total jobs checked: {len(list(in_progress_jobs))}")
        print(f"Total tasks in queue after check: {len(all_task_ids)}")

    except Exception as e:
        print(f"An error occurred while checking and queueing jobs: {str(e)}")

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    process_status = get_process_status(job_id)
    if process_status:
        return jsonify(process_status)
    return jsonify({'error': 'Job not found'}), 404

@app.route('/save-text', methods=['POST'])
def save_text():
    data = request.get_json()
    if 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    text = data['text']

    job_info = extract_job_info(text)
    
    # Create or get job ID
    job_id = create_or_get_job(session['user']['_id'], job_info)

    return jsonify({'message': 'PDF processed and text saved to database.', 'job_id': job_id})

@app.route('/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        file.save(os.path.join('uploads', file.filename))
        return jsonify({'message': 'File uploaded successfully', 'filename': file.filename})
    return jsonify({'error': 'File upload failed'})

@app.route('/jobs', methods=['GET'])
def get_jobs():
    current_user = session['user']['_id']
    print(current_user)
    user = users_collection.find_one({'_id': ObjectId(current_user)})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    jobs = jobs_collection.find({'userid': str(user['_id'])})
    job_list = []
    for job in jobs:
        job['_id'] = str(job['_id'])  # Convert ObjectId to string
        job_list.append(job)

    return jsonify(job_list)

@app.route('/all-jobs-progress', methods=['GET'])
def get_all_jobs_progress():
    if 'user' not in session or '_id' not in session['user']:
        return jsonify({'error': 'User not authenticated'}), 401
    
    current_user_id = session['user']['_id']
    if not current_user_id:
        return jsonify({'error': 'Invalid user ID'}), 400

    try:
        user = users_collection.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        jobs = jobs_collection.find({'userid': str(user['_id'])})
        progress_data = {}

        for job in jobs:
            job_id = str(job['_id'])
            process_status = get_process_status(job_id)
            if process_status:
                steps = list(process_status.values())
                completed_steps = steps.count('done')
                progress = round((completed_steps / len(steps)) * 100)
                progress_data[job_id] = progress

        return jsonify(progress_data)
    except Exception as e:
        return jsonify({'error': 'Invalid user ID format'}), 400

@app.route('/delete-job/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    if 'user' not in session or '_id' not in session['user']:
        return jsonify({'error': 'User not authenticated'}), 401

    current_user_id = session['user']['_id']
    
    try:
        # Check if the job exists and belongs to the current user
        job = jobs_collection.find_one({'_id': ObjectId(job_id), 'userid': str(current_user_id)})
        
        if not job:
            return jsonify({'error': 'Job not found or you do not have permission to delete it'}), 404
        
        # Delete the job from the jobs collection
        result = jobs_collection.delete_one({'_id': ObjectId(job_id)})
        
        if result.deleted_count == 1:
            # Also delete the corresponding job description if it exists
            jobs_collection.delete_one({'_id': ObjectId(job_id)})
            
            return jsonify({'message': 'Job deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete the job'}), 500
    
    except Exception as e:
        return jsonify({'error': 'Invalid job ID format'}), 400


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)
    #socketio.run(app, debug=True)
