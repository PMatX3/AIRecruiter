from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response, send_from_directory
import speech_recognition as sr
from pydub import AudioSegment
import openai
from openai import OpenAI
import json
import traceback
import os, time, random, string
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
import jwt
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
    update_process_status,
    update_getting_resumes_celery
)
from datetime import datetime
import base64
import io
from PyPDF2 import PdfReader
from celery import Celery
from celery.app.control import Inspect
import logging
from datetime import timedelta

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='app.log', filemode='a')

# Example usage of logging
logging.info("Application startup")

# AudioSegment.converter = "ffmpeg.exe"
# AudioSegment.ffmpeg = "ffmpeg.exe"  # Some versions of pydub might require setting this as well
# AudioSegment.ffprobe ="ffprobe.exe"  # ffprobe is part of ffmpeg and might also need to be specified
AudioSegment.converter = "/usr/bin/ffmpeg"
AudioSegment.ffmpeg = "/usr/bin/ffmpeg"
AudioSegment.ffprobe = "/usr/bin/ffprobe"


app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
app.secret_key = os.getenv("SECRET_KEY")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
app.config['REQUEST_TIMEOUT'] = 300  # 5 minutes timeout
jwt_manager = JWTManager(app)

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
print("celery broker url: ", app.config['CELERY_BROKER_URL'])
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


def extract_job_info(text):
    try:
        print("GEMINI_API_KEY__:", GEMINI_API_KEY)

        # url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=AIzaSyCAy0tBG3nXf4FhUsfy-1rZ9XAdT0_rJZg"

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
        If any of the sections are not specified in the text, don't include that respective section. The generated job description must contain all the points mentioned above and be presented in proper markdown format. I want to extract minimum text from the text provided. To Apply section must be : 'To Apply: Send you resume to airecruiter@gmail.com and must use 'job_id' in the subject line otherwise, it will not be considered'"""}]}]}
        
        headers = {
            "Content-Type": "application/json"
        }
        print("==============")
        print("payload: ", payload)
        res = requests.post(url, data=json.dumps(payload), headers=headers)
        print("res: ", res.json())
        all_items = res.json()['candidates'][0]['content']['parts'][0]['text']
        return all_items
    except:
        return None

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('registration.html')
    data = request.get_json()
    username = data.get('username')
    phone = data.get('phone')
    email = data.get('email')
    password = data.get('password')
    print("username: ", username)
    print("phone: ", phone)
    print("email: ", email)
    print("password: ", password)
    if users_collection.find_one({'username': username}):
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = generate_password_hash(password)
    print("hashed_password: ", hashed_password)
    users_collection.insert_one({'username': username, 'phone': phone, 'email': email, 'password': hashed_password})
    print("User registered successfully")
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

# @app.route('/forgot_password_template', methods=['GET'])
# def forgot_password():
    

@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')
    elif request.method == 'POST':
        from email_test import send_email_2
        from datetime import datetime, timedelta
        DOMAIN = "https://www.yourbestrecruiter.ai"
        data = request.get_json()

        email = data['email']
        user = users_collection.find_one({'email': email})
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        username = user['username']
        exp = datetime.utcnow() + timedelta(hours=1)
        reset_token = jwt.encode({'user_id': email, 'exp': exp}, app.secret_key, algorithm='HS256')
        path = url_for('change_password', token=reset_token)
        reset_link = f"{DOMAIN}{path}"
        send_email_2([email], 'Reset Password link', username , reset_link)

    return jsonify({'message': 'Password reset link sent to email'}), 200

@app.route('/change_password', methods=['POST','GET'])
def change_password():
    if request.method == 'GET':
        token = request.args.get('token', None)
        print("token: ", token)
        if token:
            try:
                decoded_token = jwt.decode(token, app.secret_key, algorithms=['HS256'])
                email = decoded_token.get('user_id')
                print("email: ", email)
                user = users_collection.find_one({'email': email})
                print("user: ", user)
                if user:
                    return render_template('change_password.html', user_id=email)
                else:
                    return jsonify({'message': 'User not found'}), 404
            except jwt_manager.ExpiredSignatureError:
                return 'Token has expired', 401
            except jwt_manager.InvalidTokenError:
                return 'Invalid token', 401
        user_id = session.get('user_id')
        return render_template('change_password.html', user_id=user_id)
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('hidden_email')
        password = data.get('password')
        print("email: ", email)
        print("password: ", password)

        users_collection.update_one({'email': email}, {'$set': {'password': generate_password_hash(password)}})
        return redirect(url_for('login'))
    
@app.route('/terms_of_services', methods=['GET'])
def terms_of_services():
    return render_template('terms_services.html')

@app.route('/privacy_policy', methods=['GET'])
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/change_password_template', methods=['POST'])
def change_password_post():
    return render_template('change_password.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    user = users_collection.find_one({'email': email})
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Generate a random 6-digit OTP
    otp = ''.join(random.choice(string.digits) for _ in range(6))
    
    
    return jsonify({'message': 'OTP sent to email'}), 200

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html')
    else:
        return render_template('home.html')

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

    existing_job = jobs_collection.find_one({
        'userid': user_id,
        'process_status.Creating Job description': 'not_started'
    })
    
    job_title = f'job_{job_number:03d}'
    
    if existing_job:
        updated_job_info = job_info.replace("job_id", f"job_{str(existing_job['_id'])}")
        jobs_collection.update_one(
            {'_id': existing_job['_id']},
            {'$set': {'job_info': updated_job_info, 
                      'job_title': job_title,
                      'job_id': str(existing_job['_id']),
                      'edited': False
                      }}
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
        updated_job_info = job_info.replace("job_id", f"job_{str(result.inserted_id)}")
        jobs_collection.update_one(
            {'_id': result.inserted_id},
            {'$set': {'job_info': updated_job_info}}
        )
        return str(result.inserted_id)

@app.route('/audio-to-text', methods=['POST'])
def audio_to_text():
    print("Starting audio-to-text conversion")
    if 'file' not in request.files:
        print("Error: No file part in the request")
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        print("Error: No selected file")
        return jsonify({'error': 'No selected file'})
    if file:
        print(f"Processing file: {file.filename}")
        # Save the uploaded file temporarily
        temp_filename = 'temp_audio.' + file.filename.split('.')[-1]
        file.save(temp_filename)
        print(f"Temporary file saved: {temp_filename}")

        # Convert the audio to WAV format
        audio = AudioSegment.from_file(temp_filename)
        audio.export("temp_audio.wav", format="wav")
        print("Audio converted to WAV format")

        # Perform speech recognition
        recognizer = sr.Recognizer()
        with sr.AudioFile("temp_audio.wav") as source:
            audio_data = recognizer.record(source)
        print("Audio data recorded")
        
        try:
            text = recognizer.recognize_google(audio_data)
            print("Speech recognition successful")
        except sr.UnknownValueError:
            print("Error: Speech recognition could not understand the audio")
            return jsonify({'error': 'Speech recognition could not understand the audio'})
        except sr.RequestError:
            print("Error: Could not request results from speech recognition service")
            return jsonify({'error': 'Could not request results from speech recognition service'})

        # Clean up temporary files
        os.remove(temp_filename)
        os.remove("temp_audio.wav")
        print("Temporary files cleaned up")

        # Save the extracted text to the database
        text_data_collection.insert_one({'user_id': session['user']['_id'], 'text': text})
        print("Extracted text saved to database")

        # Extract job information
        job_info = extract_job_info(text)
        print("Job information extracted")
        
        # Create or get job ID
        job_id = create_or_get_job(session['user']['_id'], job_info)
        print(f"Job created or retrieved with ID: {job_id}")

        print("Audio-to-text conversion completed successfully")
        return jsonify({'message': 'Audio processed and text saved to database.', 'job_id': job_id})

@app.route('/pdf-to-text', methods=['POST'])
def pdf_to_text():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        print("file found")
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        print("file not empty")
        # Determine file type based on the extension
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        print("file extension: ", file_extension)
        if file_extension not in ['pdf', 'txt']:
            return jsonify({'error': 'Unsupported file type'}), 400
        print("file extension supported")
        if file_extension == 'pdf':
            text = extract_text_from_pdf(file)
        elif file_extension == 'txt':
            text = file.read().decode('utf-8')  # Assuming UTF-8 encoding for text files
        print("text extracted")
        print("text: ", text)
        result = text_data_collection.insert_one({'user_id': session['user']['_id'], 'text': text})
        
        job_info = extract_job_info(text)
        job_id = create_or_get_job(session['user']['_id'], job_info)
        print("job_id: ", job_id)
        return jsonify({'message': 'File processed and text saved to database.', 'job_id': job_id})
    except Exception as e:
        import traceback
        print(f"Error in PDF to text conversion: {str(e)}")
        print(traceback.format_exc())  # This will print the full stack trace
        return jsonify({'error': 'An error occurred during file processing'}), 500

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
        if 'log_message' in job:
            print("log_message: ", job['log_message'])
            return job['process_status'], job['log_message']
        return job['process_status'], None
    return None, None

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
def process():
    # Check if 'user' is in session to determine if the user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))
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

@app.route('/re-run-process', methods=['POST'])
def re_run_process():
    data = request.get_json()
    job_id = data.get('job_id')
    end_date = datetime.now() - timedelta(days=1)
    print(f"=== end_date: {end_date}")
    update_getting_resumes_celery.apply_async((job_id,), eta=str(end_date))
    job_data = jobs_collection.find_one({'_id': ObjectId(job_id)})
    return jsonify({'matched_resumes': job_data['matched_resumes']})

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
        print("job_id: ==>", job_id)
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
        print(f"====================== \n\n statred")
        try:
            run_process.delay(job_id)
        except Exception as e:
            print(f"Error in run_process: {str(e)}")
            print(traceback.format_exc())

    return jsonify({'message': 'Process started for all unprocessed jobs.'})

@app.route('/get-matched-resumes/<job_id>', methods=['GET'])
def get_matched_resumes(job_id):
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    return jsonify({'matched_resumes': job['matched_resumes']})

@celery.task
def run_process(job_id):
    try:
        update_job_description(job_id)
    except Exception as e:
        import traceback
        print("print traceback \n", traceback.print_exc())
        print(f"Error in update_job_description: {str(e)}")

    try:
        update_job_posting(job_id)
    except Exception as e:
        print(f"Error in update_job_posting: {str(e)}")
        
    

    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    update_process_status(job_id, "Getting resumes from portal", "in_progress", log_message=f"This process will run on {job['end_date'].date()}")
    try:
        if 'end_date' in job:
            update_getting_resumes_celery.apply_async((job_id,), eta=job['end_date'])
    except Exception as e:
        print(f"Error in update_getting_resumes: {str(e)}")

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
                print("============")
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
    process_status, log_message = get_process_status(job_id)
    if process_status:
        return jsonify({'process_status': process_status, 'log_message': log_message})
    return jsonify({'error': 'Job not found'}), 404

@app.route('/save-text', methods=['POST'])
def save_text():
    data = request.get_json()
    
    if 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    text = data['text']
    job_info = extract_job_info(text)
    if not job_info:
        return jsonify({'error': 'Failed to extract job information from text'}), 400
    
    # Create or get job ID
    job_id = create_or_get_job(session['user']['_id'], job_info)

    return jsonify({'message': 'PDF processed and text saved to database.', 'job_id': job_id})

# @app.route('/upload-file', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'})
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'})
#     if file:
#         file.save(os.path.join('uploads', file.filename))
#         return jsonify({'message': 'File uploaded successfully', 'filename': file.filename})
#     return jsonify({'error': 'File upload failed'})

@app.route('/jobs', methods=['GET'])
def get_jobs():
    if not 'user' in session:
        return jsonify({'error': 'User not authenticated'}), 401
    if '_id' not in session['user']:
        return jsonify({'error': 'User not authenticated'}), 401
    
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
            process_status, log_message = get_process_status(job_id)
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

@app.route('/test', methods=['GET'])
def test():
    return render_template('test.html')

@app.route('/save-interview', methods=['POST'])
def save_interview():
    try:
        data = request.json
        filename = f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        return {'status': 'success'}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)
    #socketio.run(app, debug=True)
