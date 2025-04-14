from flask import Flask,flash, request, jsonify, render_template, make_response,session, redirect, url_for, Response, send_from_directory,abort
import speech_recognition as sr

from pymongo.errors import PyMongoError

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
import re
from dateutil import parser
import pytz
from google.oauth2.service_account import Credentials  # Correct import
from googleapiclient.discovery import build
import os
import google_auth_oauthlib.flow

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from process import update_job_description,update_job_posting, update_process_status,update_getting_resumes_celery
from process import get_organization_details, get_user_organizations
from email_test import send_mail
import base64
import io
import uuid
from PyPDF2 import PdfReader
from celery import Celery
from celery.app.control import Inspect
import logging
from datetime import datetime, timedelta, timezone, time
import google.auth
from google.auth.transport.requests import Request  # Make sure to import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
from google.apps import meet_v2
import tempfile
from threading import Thread




from schedule_meeting import get_credentials, create_open_google_meet, handle_schedule, handle_reschedule, handle_cancel
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


# Google API credentials and scopes
SCOPES = [
    'https://www.googleapis.com/auth/meetings.space.created',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

#  Linkedin Client
CLIENT_ID = "78sqp6ad5vx02s"
CLIENT_SECRET = "WPL_AP1.5M5XItSYHSCTpVUg.bXZYvQ=="
REDIRECT_URI = "https://www.yourbestrecruiter.ai/auth/callback"



mongo_client = get_mongo_client()
db = mongo_client.get_database('recruiter')
users_collection = db.get_collection('users') if db.get_collection('users') is not None else db.create_collection('users')
text_data_collection = db.get_collection('text_data') if db.get_collection('text_data') is not None else db.create_collection('text_data')
process_collection = db.get_collection('process') if db.get_collection('process') is not None else db.create_collection('process')
jobs_collection = db.get_collection('jobs') if db.get_collection('jobs') is not None else db.create_collection('jobs')
linkedin_collection = db.get_collection('linkedin_users') if db.get_collection('linkedin_users') is not None else db.create_collection('linkedin_users')
selected_collection = db.get_collection('selected_candidates') if db.get_collection('selected_candidates') is not None  else db.create_collection('selected_candidates')
    
tickets_collection = db.get_collection('tickets')
reports_collection = db.get_collection('reports')
subscriptions_collection = db.get_collection('subscription') 




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


openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(
  api_key=os.environ['OPENAI_API_KEY'],  # this is also the default, it can be omitted
)

def async_file_cleanup(filepath):
    """Handle file deletion asynchronously"""
    try:
        os.remove(filepath)
    except Exception as e:
        print(f"Error during file cleanup: {e}")

def is_english(text):
    return bool(re.match(r'^[A-Za-z0-9\s.,!?\'\"()-]+$', text))

@app.route('/notifications_update', methods=['GET'])
def navbar():
    if 'user' in session:
        current_user = session['user']['_id']
        user = users_collection.find_one({'_id': ObjectId(current_user)})
        notifications = get_todays_interviews()
        notification_count = len(notifications) if notifications else 0
        is_superadmin = user.get('is_superadmin', False) if user else False

        # Construct the response dictionary correctly
        response = {
            'notification_count': notification_count,
            'is_superadmin': is_superadmin
        }
        return jsonify(response)  # Return the response as JSON
    else:
        # Handle the case where the user is not logged in.
        # You might return a default response or an error.
        response = {
            'notification_count': 0,
            'is_superadmin': False
        }
        return jsonify(response) #Or some error message, or redirect.

@app.route('/test', methods=['GET'])
def index_testing():
    return render_template('file4.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            temp_audio.write(audio_file.read())
            temp_audio_path = temp_audio.name

        try:
            # audio_file.save(temp_audio_path)

            with open(temp_audio_path, "rb") as audio:
                response = client.audio.transcriptions.create(
                    model="whisper-1",  # Whisper model
                    file=audio,
                    response_format="text",
                    language="en"   # Ensure response contains text
                )

            transcribed_text = response.strip() if response else ""

            

            print("Recognized text:", transcribed_text)
            

            # NEW RESPONSE FORMAT
            if isinstance(transcribed_text, str):
                print("Response is: ", transcribed_text)
                print("Transcribed text: ", transcribed_text)
                return jsonify({'text': transcribed_text})
            else:
                print("Unexpected response format: ", response)
                return jsonify({'error': 'Unexpected response format from OpenAI'}), 500


        except openai.OpenAIError as e:  # Note the change here!
            Thread(target=async_file_cleanup, args=(temp_audio_path,), daemon=True).start()
            return jsonify({'error': f'Failed to process audio with OpenAI: {str(e)}'}), 500
        except Exception as e:
            Thread(target=async_file_cleanup, args=(temp_audio_path,), daemon=True).start()
            return jsonify({'error': str(e)}), 500

    finally:
        try:
            Thread(target=async_file_cleanup, args=(temp_audio_path,), daemon=True).start()
            print(f"Temporary file {temp_audio_path} deleted.")
        except Exception as e:
            print(f"Error deleting temporary file: {e}")


#----------------------------------------------------------------------------------------
# 27/01/2025
def extract_job_info(text):
    try:
        print("GEMINI_API_KEY__:", GEMINI_API_KEY)

        # url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=AIzaSyCAy0tBG3nXf4FhUsfy-1rZ9XAdT0_rJZg"

        # Payload to be sent in the POST request
        payload = {"contents":[{"parts":[{"text":f"""Extract job information from the following text: {text}. Ensure to extract and include the following details but if not, don't include that section, formatted in markdown:

        📝 **Job Title**: 
        🎯 *Provide the job title*                          
        📢 **About the Job**: 
        ℹ️ *Provide a brief introduction to the role ine new line*  
        🏢 **Who We Are**: 
        🌍 *Give a short overview of the company in new line*
        💼 **Your New Role**:                                
        🎭 *Describe the job role in detail in new line*
        ✅ **Your Role Accountabilities**: 🏆 *List key responsibilities*
        🎓 **Qualifications & Experience**:📚 *Detail the required qualifications and experience.*
        🏠 **Hybrid Working**: 🏢🏡 *Describe the working conditions (onsite/hybrid/remote)*
        🚀 **How We Get Things Done**: 🌟 *Summarize the company's guiding principles*
        🤝 **Championing Inclusion at [Company]**: 🌍 *Highlight the company's diversity & inclusion efforts*  
        For inquiries mobile number if available.
        Ensure the output includes:

        Job title, bold and centered in content (if available)
        Ensure that each section starts on a new line for better readability, leave a small padding between each section.
        Complete description with all specified sections
        If any of the sections are not specified in the text, don't include that respective section. The generated job description must contain all the points mentioned above and be presented in proper markdown format. I want to extract minimum text from the text provided."""}]}]}
        
        headers = {
            "Content-Type": "application/json"
        }
        print("==============\n\n")
        # print("payload: ", payload)
        res = requests.post(url, data=json.dumps(payload), headers=headers)
        # print("res: ", res.json())
        all_items = res.json()['candidates'][0]['content']['parts'][0]['text']
        
        return all_items
    except:
        return None

SUPER_ADMIN_EMAILS =  ['super.admin@gmail.com']


@app.route('/register', methods=['GET', 'POST'])
def register():


    if request.method == 'GET':
        return render_template('registration.html')
    
    data = request.get_json()
    email = data["email"].lower()

    if users_collection.find_one({"registered_email": email}):
        return jsonify({"message": "User already exists"}), 400
    
    is_superadmin = email in SUPER_ADMIN_EMAILS
   
    
    new_user = {
        "username": data["username"],
        "company": data["company"],
        "country": data.get("country", ""),
        "created_at": datetime.utcnow(),
        "registered_email": email,
        "profileUrl": data.get("profileUrl", ""),
        "phone": data["phone"],
        "notes": "",
        "verification_status": "Pending",
        "user_type": "User",
        "password": generate_password_hash(data["password"]),
        "linkedin_id": None,  # Initially None until user connects LinkedIn
        "linkedin_email": None,  # Will be set when LinkedIn is connected
        "is_linkedin_connected": False,
        "subscription": {
            "is_subscribed": False,
            "plan": "trial",    
            "status": "active"
        },
        "features": {
            "first_job_uploaded": False
        },
        "is_superadmin": is_superadmin
    }

    users_collection.insert_one(new_user) #Replace with DB call      
    session['registration_data'] = data # Store for LinkedIn auth
    email_body = f"""
        Dear Recruiter,

        Congratulations! Your registration with YourBestRecruiterAI was successful. 🎉  

        🚀 Explore our AI-powered recruitment tools:  
        ✅ Post job listings and find the best-matched candidates effortlessly.  
        ✅ Schedule interviews and manage hiring efficiently.  
        ✅ Leverage AI to streamline your recruitment process.  

        Start your journey now and experience smarter hiring!  

        Best Regards,  
        YourBestRecruiterAI Team  
        """
    # send_mail(email, "Welcome to YourBestRecruiterAI – Your Registration is Successful!",email_body , attachment_paths=None)

    return jsonify({
        "message": "Super admin registered successfully" if is_superadmin else "User registered successfully"
    }), 201



@app.route("/login-linkedin")
def linkedin_login():
    
    session.pop('user', None)   
    print("Cleared existing session.")

    state = generate_random_string()
    session['state'] = state

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={state}"
        f"&scope=profile email w_member_social w_organization_social r_organization_social rw_organization_admin openid" # added w_member_social
        f"&prompt=login&force_account_selection=true"
    )
    return redirect(auth_url)


@app.route("/auth/callback")
def callback():
    try:
        session.pop('user', None)   
        print("Cleared existing session at callback.")

    
        code = request.args.get("code")
        state = request.args.get("state")
        
        if not code:
            return jsonify({"error": "Missing LinkedIn authorization code."}), 400
        if not state:
            return jsonify({"error": "Invalid state parameter."}), 400

    
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        }

        token_res = requests.post('https://www.linkedin.com/oauth/v2/accessToken', data=data)
        token_json = token_res.json()
        access_token = token_json.get("access_token")

        if not access_token:
            return jsonify({"error": "Failed to retrieve access token", "details": token_json}), 400

        registration_data = session.pop('registration_data', None)
        registered_email = registration_data.get('email').lower()
        

        profile_data = get_user_info(access_token)  # Function to fetch user info
        if not profile_data:
            return jsonify({"error": "Failed to fetch profile data from LinkedIn"}), 400
        


        # Extract profile details
        linkedin_email = profile_data.get("email")  
        linkedin_id = profile_data.get("sub")
        linkedin_username = f"{profile_data.get('given_name', '')} {profile_data.get('family_name', '')}".strip()
        picture = profile_data.get("picture", "")
        
        if not linkedin_email:
            return jsonify({"error": "LinkedIn did not return an email address."}), 400
        
        if users_collection.find_one({'linkedin_email': linkedin_email}):
            last_registered_user = users_collection.find_one(
                {"registered_email": registered_email}, sort=[("_id", -1)]
            )

            if last_registered_user:
                users_collection.delete_one({"_id": last_registered_user["_id"]})

            return jsonify({'error': 'This LinkedIn account is already linked to another user'}), 400

        
        if not registered_email:
            return jsonify({'error': 'Registered email is missing'}), 400

        update_data = {
            "access_token": access_token,
            "linkedin_email": linkedin_email,
            "linkedin_id": linkedin_id,
            "verification_status": "Approved",
            "linkedin_username": linkedin_username,
            "profile_picture": picture,
            "is_linkedin_connected": True,
            "user_linkedin_pages": get_user_organizations(access_token)
        }
            
        result = users_collection.update_one({"registered_email": registered_email}, {"$set": update_data})


        if result.modified_count == 1:
            user = users_collection.find_one({"registered_email": registered_email})
            session["user"] = {
                "_id": str(user["_id"]), 
                "email": user.get("linkedin_email"), 
                "username": user.get("username"),
                "is_superadmin": user.get("is_superadmin", False)
            }
        
            token = create_access_token(identity=user["linkedin_email"])
            return redirect(url_for("home", access_token=token, is_superadmin=user.get("is_superadmin", False)))

        else:
            return jsonify({"error": "Failed to update user data."}), 400

    except Exception as e:
        return jsonify({'error': 'Unexpected error occurred during LinkedIn callback', 'details': str(e)}), 500

    


    

def generate_random_string(length=32):
    """Generates a cryptographically secure random string."""
    alphabet = string.ascii_letters + string.digits + "-._~"
    random_string = ''.join(secrets.choice(alphabet) for _ in range(length))
    return random_string


def get_user_info(access_token):
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting user info: {e}")
        return None
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json()
    email = data.get('email').lower()
    password = data.get('password')
    
    user = users_collection.find_one({'registered_email': email})
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    verification_status = user.get('verification_status', '')

    if verification_status == 'Pending':
        return jsonify({'message': 'Your account is pending for Approval. Please wait for admin Approval.'}), 403
    elif verification_status == 'Rejected':
        return jsonify({'message': 'Your account has been Rejected. Please contact support for assistance.'}), 403
    
    # Create session and JWT token
    user['_id'] = str(user['_id'])
    session['user'] = user
    access_token = create_access_token(identity=email)

    
    job = jobs_collection.find_one({'userid': user['_id'], 'process_status': {'$elemMatch': {'$eq': 'in_progress'}}})
    if job:
        return redirect('/process')
    
    return jsonify({'access_token': access_token, 'is_superadmin': user.get('is_superadmin', False)}), 200

@app.context_processor
def inject_navbar_data():
    return {
        "user": session.get("user"),  # Fetch user from session
        "notification_count": session.get("notification_count", 0),
        "is_superadmin": session.get("is_superadmin", False),
    }


@app.route('/profile', methods=['GET'])
def viewprofile():
    if 'user' not in session:
        return redirect(url_for('login'))

    loggedinUser = session['user']['_id']
    user = users_collection.find_one({'_id': ObjectId(loggedinUser)})

    if not user:
        return jsonify({'error': 'User not found'}), 404


    # Fetch notifications
    notifications = get_todays_interviews()
    notification_count = len(notifications) if notifications else 0
    is_superadmin = user.get('is_superadmin', False)

    # If AJAX request, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'username': user.get('username', ''),
            'email': user.get('registered_email', ''),
            'linkedin_email': user.get('linkedin_email', 'Not available'),
            'phone': user.get('phone', ''),
            'company': user.get('company', ''),
            'country': user.get('country', ''),
            'notification_count': notification_count,
            'is_superadmin': is_superadmin
        })

    # Render profile page with additional data
    return render_template(
        'profile.html',
        user=user,
        notification_count=notification_count,
        is_superadmin=is_superadmin
    )

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    loggedinUser = session['user']['_id']
    user = users_collection.find_one({'_id': ObjectId(loggedinUser)})

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.json
    
    update_fields = {
        'username': data.get('username', user['username']),
        'phone': data.get('phone', user['phone']),
        'company': data.get('company', user['company']),
    }
    
    if 'country' in data:
        update_fields['country'] = data['country']

    users_collection.update_one(
        {'_id': ObjectId(loggedinUser)},
        {'$set': update_fields}
    )

    return jsonify({'message': 'Profile updated successfully'}), 200
    

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')
    
    elif request.method == 'POST':
        from email_test import send_email_2
        DOMAIN = "https://www.yourbestrecruiter.ai"
        
        try:
            data = request.get_json()
            email = data['email']
            
            user = users_collection.find_one({'email': email})
            if not user:
                return jsonify({'message': 'User  not found'}), 404
            
            username = user['username']
            print(f"Username found: {username}")
            
            exp = datetime.utcnow() + timedelta(hours=1)
            reset_token = jwt.encode({'user_id': email, 'exp': exp}, app.secret_key, algorithm='HS256')
            path = url_for('change_password', token=reset_token)
            reset_link = f"{DOMAIN}{path}"
            print(f"Reset link generated: {reset_link}")
            
            send_email_2([email], 'Reset Password link', username, reset_link)
            print(f"Password reset link sent to email: {email}")
        
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return jsonify({'message': 'An error occurred while processing your request'}), 500

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
                user = users_collection.find_one({'registered_email': email})
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

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Clear user session
    session.pop("user", None)
    session.pop("access_token", None)
    session.clear()

    # LinkedIn logout URL (redirects to login after logout)
   
    # Create response and prevent caching
    response = make_response(redirect('/login'))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
    

@app.route('/pricing')
def pricing():
    if 'user'in session:
        return render_template('pricing.html')
    else:
        return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user' in session:
        current_user = session['user']['_id']
        print(" line 748 user is in the session : ", current_user)
        user = users_collection.find_one({'_id': ObjectId(current_user)})
        if user:
            verification_status = user.get('verification_status', '')
            if verification_status in ['Pending', 'Rejected']:
                requests.post(url_for('logout', _external=True))
                return redirect(url_for('login'))
            
            notifications = get_todays_interviews()
            notification_count = len(notifications) if notifications else 0
            is_superadmin = user.get('is_superadmin', False)
            first_job_uploaded = user["features"]["first_job_uploaded"]
            is_subscribed = user["subscription"]["is_subscribed"]
            access_token = user.get('access_token', 'not foound')

            print(" line 762 Access_token :  : ", access_token)
            return render_template('index.html', notification_count=notification_count, notifications=notifications, is_superadmin=is_superadmin, first_job_uploaded = first_job_uploaded, is_subscribed=is_subscribed )
        else:
            
            session.pop('user', None)
            print(" line 767 user is not in the session : ")
            return render_template('home.html')
        
    print(" line 768 user is not in the session : ")
    return render_template('home.html')

def create_or_get_job(user_id, job_info):
    # Find the highest job number for this user
    highest_job = jobs_collection.find_one(
        {'userid': user_id},
        sort=[('job_title', -1)]
    )

    if highest_job and 'job_title' in highest_job:
        # Attempt to split the job title and extract the job number
        job_title_parts = highest_job['job_title'].split('_')
        if len(job_title_parts) > 1 and job_title_parts[1].isdigit():
            job_number = int(job_title_parts[1]) + 1
        else:
            job_number = 1  # Default to 1 if the format is unexpected
    else:
        job_number = 1

    # existing_job = jobs_collection.find_one({
    #     'userid': user_id,
    #     'process_status.Creating Job description': 'not_started'
    # })

    if job_info:
        match = re.search(r'# \*\*(.*?)\*\*', job_info)
        if match:
            job_title = match.group(1)
            print("Job Title:", job_title)
        else:
            job_title = f'job_{job_number:03d}'
    
    print("job info is:", job_info)

    # title_match = re.search(r'<div align="center">(.*?)</div>|<center>(.*?)</center>|job title', job_info)
    # if title_match:
    #     job_title = title_match.group(1) if title_match.group(1) else title_match.group(0)
    # else:
    #     job_title = f'job_{job_number:03d}'
    
    print("job_title is:", job_title)
    
    # if existing_job:
    #     updated_job_info = job_info.replace("job_id", f"job_{str(existing_job['_id'])}")
    #     jobs_collection.update_one(
    #         {'_id': existing_job['_id']},
    #         {'$set': {
    #             'job_info': updated_job_info, 
    #             'job_title': job_title,
    #             'job_id': str(existing_job['_id']),
    #             'edited': False
    #         }}
    #     )
    #     return str(existing_job['_id'])
    # else:
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
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized access'}), 401
        
        user_id = session['user']['_id']
        user = users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.get('is_superadmin', False):    
            # Check if the user has already used the free trial feature
            if not user['subscription']['is_subscribed'] and user['features'].get('first_job_uploaded', False):
                print('Free Trial limit reached. Please subscribe to continue.')
                return jsonify({'error': 'Trial limit reached. Please subscribe to continue.'}), 403
        
        
        # Check if a file is uploaded     
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
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

         # Mark PDF upload as used in trial
        if not user['subscription']['is_subscribed']:
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"features.first_job_uploaded": True}}
            )

        result = text_data_collection.insert_one({'user_id': session['user']['_id'], 'text': text})
        
        job_info = extract_job_info(text)
        job_id = create_or_get_job(session['user']['_id'], job_info)

        
        return jsonify({'message': 'File processed and text saved to database.', 'job_id': job_id})
    
    except Exception as e:
        import traceback
        print(f"Error in PDF to text conversion: {str(e)}")
        print(traceback.format_exc())  # This will print the full stack trace
        return jsonify({'error': 'An error occurred during file processing'}), 500

@app.route('/check-upload-status', methods=['GET'])
def check_upload_status():
    try:
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized access'}), 401

        user_id = session['user']['_id']
        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"features.first_job_uploaded": 1, "subscription.is_subscribed": 1,"is_superadmin":1})

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Return upload status
        return jsonify({
            "first_job_uploaded": user.get('features', {}).get('first_job_uploaded', False),
            "is_subscribed": user.get('subscription', {}).get('is_subscribed', False),
            "is_superadmin": user.get('is_superadmin', False)
        })
    

    except Exception as e:
        return jsonify({'error': 'Error checking upload status'}), 500

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
    
    return render_template('process.html', organizations=session.get('organizations', []))

@app.route('/help')
def help_center():
    # Check if 'user' is in session to determine if the user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))

    loggedinUser = session['user']['_id']
    user = users_collection.find_one({'_id': ObjectId(loggedinUser)})

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return render_template('help.html', user=user, username=user.get('username', ''), email=user.get('email', ''))

@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    

    data = request.get_json()
    print(" Ticket Data: ", data)
    username = data.get('username')
    email = data.get('email')
    subject = data.get('subject')
    message = data.get('message')
    userId = session['user']['_id']

    if not username or not email or not subject or not message:
        return jsonify({'error': 'Missing fields'}), 400
    
    ticket_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    updated_at = ''

    ticket = {
        'ticketId': ticket_id,
        'userId': ObjectId(userId),
        'username': username,
        'email': email,
        'subject': subject,
        'message': message,
        'createdAt': created_at,
        'updatedAt': updated_at,
        'status': 'Open',
        'admin_response': '',
    }

    tickets_collection.insert_one(ticket)

    return jsonify({'success': True, 'ticketId': ticket_id}), 200



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

@app.route('/clean', methods=['DELETE'])
def clean_all_jobs():
    try:
        # Delete all jobs from the jobs collection
        result = jobs_collection.delete_many({})
        
        # Return the count of deleted jobs
        return jsonify({'message': f'Deleted {result.deleted_count} jobs.'}), 200

    except Exception as e:
        print(f"Error cleaning all jobs: {str(e)}")
        return jsonify({'error': 'An error occurred while cleaning all jobs.'}), 500

@app.route('/start-process', methods=['GET','POST'])
def start_process():
    # Get all jobs from the collection
    all_jobs = jobs_collection.find({})
    data = request.get_json()
    
   
    selected_orgs = data.get('selected_orgs', [])
    
    active_tasks = []
    active_dict = celery.control.inspect().active()
    if active_dict:
        active_tasks = [task.id for tasks in active_dict.values() for task in tasks]
    
    for job in all_jobs:
        job_id = str(job['_id'])

        process_status = job.get('process_status', {})
        # Check if the job is already completed or in progress
        if any(status == "done" for status in process_status.values()) or job_id in active_tasks:
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
                },
                'selected_orgs': selected_orgs
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
    print("method run process called ")
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
    
    
    update_process_status(job_id, "Getting resumes from portal", "in_progress", log_message=f"This process will run")
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
    try:
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized access'}), 401
        
        user_id = session['user']['_id']

        # Check if the user has already used the service
        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"features.first_job_uploaded": 1, "subscription.is_subscribed": 1})

        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # If service has already been used and user is not subscribed, restrict access
        if user.get('features', {}).get('first_job_uploaded', False) and not user.get('subscription', {}).get('is_subscribed', False):
            return jsonify({'error': 'Trial limit reached. Please subscribe to continue.'}), 403
        
        data = request.get_json()
        
        if 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400

        text = data['text']
        job_info = extract_job_info(text)
        if not job_info:
            return jsonify({'error': 'Failed to extract job information from text'}), 400
        
        # Create or get job ID
        job_id = create_or_get_job(session['user']['_id'], job_info)
        print("New job id : ", job_id)

        # Mark the feature as used after first successful access
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"features.first_job_uploaded": True}}
        )
        return jsonify({'message': 'PDF processed and text saved to database.', 'job_id': job_id})
    
    except Exception as e:
        print(f"Error in text processing: {str(e)}")
        return jsonify({'error': 'An error occurred while processing the text'}), 500

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
   
    user = users_collection.find_one({'_id': ObjectId(current_user)})
    print("Current user : ", user.get('username'))
    print("user_organizations: ", session.get('organizations', []))
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

@app.route('/interviews', methods=['GET'])
def interview():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    currentUser = session['user']['_id']
    user = users_collection.find_one({'_id': ObjectId(currentUser)})

    if not user:
        return jsonify({'error': 'User not found'}), 404


    # Fetch notifications
    notifications = get_todays_interviews()
    notification_count = len(notifications) if notifications else 0
    is_superadmin = user.get('is_superadmin', False)

    return render_template(
        "interviews.html",
        user=user,
        notification_count=notification_count,
        is_superadmin=is_superadmin
    )


@app.route('/candidates', methods=['GET'])
def getCandidates():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    loggedinUser = session['user']['_id']
    user = users_collection.find_one({'_id': ObjectId(loggedinUser)})

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return render_template('new_candidates.html')

        

@app.route('/selected_candidates', methods=['GET'])
def get_selected_candidates():
    if 'user' not in session or '_id' not in session['user']:
        return jsonify({'error': 'User not authenticated'}), 401

    current_user_id = session['user']['_id']
    if not current_user_id:
        return jsonify({'error': 'Invalid user ID'}), 400

    try:
        user = users_collection.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Fetch all jobs where "Matching resumes with job description" is "done"
        jobs = jobs_collection.find({'userid': str(user['_id']),"process_status.Matching resumes with job description": "done"})
        
        # Prepare job data
        job_data = []
        for job in jobs:
            job_id = str(job['_id'])
            job_title = job['job_title']
            
            
            selected_job = selected_collection.find_one({'job_id':job_id})
            
            # Fetch selected candidates for this job
            candidates = selected_job.get('selected_candidates',[]) if selected_job else []
            
            job_data.append({
                'user_id': str(user['_id']),
                'job_id': job_id,
                'job_title': job_title,
                'selected_candidates': candidates
            })
        
        return jsonify({'jobs': job_data})
    
    except Exception as e:
        print("Error:\n", str(e))
        logging.error(f"Error fetching jobs: {str(e)}")
        return jsonify({'error': 'Error fetching jobs'}), 500
    


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
    
@app.route('/attachments/<job_id>/<filename>')
def serve_file(job_id, filename):
    directory = os.path.join('attachments', f'job_{job_id}')

    if not os.path.exists(directory):
        abort(404) 

    return send_from_directory(directory, filename)

def create_google_meet_event(datetime_str, candidate_email, recruiter_email):
    try:
        creds = get_credentials()
    
        if not creds:
            print("Failed to authenticate. Please check the error messages above.")
            return

        # Create Calendar service
        calendar_service = build('calendar', 'v3', credentials=creds)

        # Correct datetime parsing with milliseconds and 'Z'
        try:
            event_start = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")  # With milliseconds
        except ValueError:
            event_start = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")  # Without milliseconds
        event_end = event_start + timedelta(hours=1)

        # Prepare the event details
        event = {
            'summary': 'Interview with Candidate',
            'description': 'Google Meet Interview',
            'start': {
                'dateTime': event_start.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': event_end.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': candidate_email},
                {'email': recruiter_email},
            ],
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),  # Random ID for the meeting
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet',
                    },
                    'status': {
                        'statusCode': 'success',
                    }
                }
            },
        }

        # Create the event and get the Meet link
        event_result = calendar_service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'
        ).execute()
        

        meet_link = event_result['conferenceData']['entryPoints'][0]['uri']
        return meet_link
    except HttpError as error:
        print(f"Error creating Google Meet event: {error}")
        return None




# Route to handle scheduling
# @app.route('/schedule_meeting', methods=['POST'])
# def schedule_meeting():
#     print("Received request at /schedule_meeting")
#     try:
#         data = request.json
#         print("Request data:", data)
#         user_id = session['user']['_id']
#         job_id = data.get('job_id') 
#         candidate_name = data.get("candidate_name")
#         candidate_email = data.get("candidate_email")
#         recruiter_email = data.get("recruiter_email")
#         datetime_str = data.get("datetime")
#         user_timezone_str = data.get("timezone", "UTC")
#         action = data.get("action")

#         print(" UserId : ", user_id)
#         print(" job_id : ", job_id)
        
        
#         # Validate required fields
#         if not all([candidate_name, candidate_email, recruiter_email, datetime_str]):
#             print("Missing required data in request")
#             return jsonify({"success": False, "error": "Missing data"}), 400
        
#         # Convert user-provided datetime to UTC
#         try:
#             user_timezone = pytz.timezone(user_timezone_str)  # Get user timezone
#             local_time = parser.isoparse(datetime_str).astimezone(user_timezone)  # Convert to local timezone
#             utc_time = local_time.astimezone(pytz.UTC)  # Convert to UTC for database storage
#         except (ValueError, pytz.exceptions.UnknownTimeZoneError) as e:
#             print("Error parsing datetime:", str(e))
#             return jsonify({"success": False, "error": f"Invalid datetime or timezone: {str(e)}"}), 400
        
#         # Validate that interview date is not in the past
#         current_utc_time = datetime.now(pytz.UTC)
#         if utc_time < current_utc_time:
#             print("Interview date is in the past")
#             return jsonify({"success": False, "error": "Interview date cannot be in the past"}), 400
        
#         # Find the candidate inside "selected_candidates"
#         print("Searching for candidate in database...")
#         candidate_doc = selected_collection.find_one({
#             "job_id": job_id,
#             "user_id": user_id,
#             "selected_candidates.candidate_name": candidate_name
#         })
        
#         if not candidate_doc:
#             print("Candidate not found in database")
#             return jsonify({"success": False, "error": "Candidate not found"}), 404
        
#         # Generate Google Meet link
#         print("Generating Google Meet link...")
#         google_meet_link = create_open_google_meet()
        
#         if not google_meet_link:
#             print("Failed to create Google Meet link")
#             return jsonify({"success": False, "error": "Failed to create Google Meet link"}), 500
        
#         # Convert UTC time to the user's timezone for display
#         interview_datetime_local = utc_time.astimezone(user_timezone)
#         formatted_local_datetime = interview_datetime_local.strftime("%d-%m-%Y %I:%M %p %Z")

#         # Email Details
#         subject_candidate = "Google Meet Interview Scheduled"
#         body_candidate = f"""
#         Dear {candidate_name},

#         Your interview has been scheduled for {formatted_local_datetime}.

#         Please join the meeting using the link below:
#         {google_meet_link}

#         Best regards,
#         Your Recruitment Team
#         """
        
#         subject_recruiter = f"Interview Scheduled with {candidate_name}"
#         body_recruiter = f"""
#         Dear Recruiter,

#         An interview has been scheduled with candidate {candidate_name} for {formatted_local_datetime}.

#         You can join the meeting using the following Google Meet link:
#         {google_meet_link}

#         Please be prepared for the interview.

#         Best regards,
#         Your Recruitment Team
#         """
        
#         # Send emails
#         print("Sending email to candidate...")
#         email_sent_to_candidate = send_mail(candidate_email, subject_candidate, body_candidate)
        
#         print("Sending email to recruiter...")
#         email_sent_to_recruiter = send_mail(recruiter_email, subject_recruiter, body_recruiter)
        
#         if not email_sent_to_candidate or not email_sent_to_recruiter:
#             print("Failed to send one or more emails")
#             return jsonify({"success": False, "error": "Failed to send emails"}), 500
        
#         # Update MongoDB to store interview date
#         print("Updating database with interview date...")
#         update_result = selected_collection.update_one(
#             {
#                 "job_id": job_id,  # Ensure it's the correct job posting
#                 "user_id": user_id,  # Ensure it's the correct user (recruiter/employer)
#                 "selected_candidates": {
#                     "$elemMatch": {
#                         "candidate_name": candidate_name,
#                     }
#                 }
#             },
#             {
#                 "$set": {
#                     "selected_candidates.$.interview_date": utc_time.isoformat(), # Store in UTC
#                     "selected_candidates.$.status": "Scheduled", # Set interview status
#                     "selected_candidates.$.location": google_meet_link  # Store Google Meet link
#                 }
#             }
#         )
        
#         if update_result.modified_count == 0:
#             print("Failed to update interview date")
#             return jsonify({"success": False, "error": "Failed to update interview date"}), 500
        
#         print("Interview successfully scheduled")
#         return jsonify({
#             "success": True,
#             "meet_link": google_meet_link,
#             "local_datetime": formatted_local_datetime
#         })

#     except Exception as e:
#         print("An unexpected error occurred:", traceback.format_exc())
#         return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500
        

UTC = pytz.utc  # Define UTC timezone

@app.route('/schedule_meeting', methods=['POST'])
def schedule_meeting():
    print(" schedule meeting api called ")
    try:
        data = request.json
        print("Request data:", data)
        user_id = session['user']['_id']
        job_id = data.get('job_id')
        candidate_id = data.get('candidate_id')
        candidate_name = data.get("candidate_name")
        candidate_email = data.get("candidate_email")
        recruiter_email = data.get("recruiter_email")
        datetime_str = data.get("datetime")
        user_timezone_str = data.get("timezone", "UTC")
        action = data.get("action")

       
        print("candidate id :", candidate_id)
        if not all([candidate_name, candidate_email, recruiter_email]):
            print("Missing required data in request")
            return jsonify({"success": False, "error": "Missing data"}), 400

        # Find the candidate document (as before) ...

        if action == "schedule":
            print("------------- schedule meeting --------------")
            # --- Scheduling Logic ---
            return handle_schedule(user_id, job_id, candidate_id, candidate_name, candidate_email, recruiter_email, datetime_str, user_timezone_str)

        elif action == "reschedule":
            print("<><><><><><> Re-schedule meeting <><><><><><>")
            # --- Reschedule Logic ---
            return handle_reschedule(user_id, job_id, candidate_id, candidate_name, candidate_email, recruiter_email, datetime_str, user_timezone_str)

        elif action == "cancel":
            print("============= cancel meeting =============")
            # --- Cancel Logic ---
            return handle_cancel(user_id, job_id, candidate_id, candidate_name, candidate_email, recruiter_email, datetime_str, user_timezone_str)

        else:
            print("Invalid action provided")
            return jsonify({"success": False, "error": "Invalid action"}), 400

    except Exception as e:
        print("An unexpected error occurred:", traceback.format_exc())
        return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500
    
def get_todays_interviews():
    # print("\n🔍 Fetching today's interviews...")  # Debug Log

    current_user_id = session.get('user', {}).get('_id')
    if not current_user_id:
        # print("🚫 Unauthorized access detected!")
        return jsonify({"error": "Unauthorized"}), 401

    user_timezone_str = request.headers.get("Time-Zone", "UTC")
    try:
        user_timezone = pytz.timezone(user_timezone_str)
    except pytz.UnknownTimeZoneError:
        print(f"⚠️ Invalid timezone received: {user_timezone_str}. Defaulting to UTC.")
        user_timezone = UTC

    today_utc = datetime.now(UTC).date()
    today_local = datetime.now(user_timezone).date()

    # Correct way to get start and end of day:
    start_of_day_local = user_timezone.localize(datetime.combine(today_local, time.min))
    end_of_day_local = user_timezone.localize(datetime.combine(today_local, time.max))

    start_of_day_utc = start_of_day_local.astimezone(pytz.UTC)
    end_of_day_utc = end_of_day_local.astimezone(pytz.UTC)
    # print(f"📅 Checking interviews between {start_of_day_utc} and {end_of_day_utc}")

    interviews = selected_collection.find({
        "user_id": current_user_id,
        "selected_candidates.interview_date": {
            "$gte": start_of_day_utc.isoformat(),  # Convert to ISO format for MongoDB
            "$lt": end_of_day_utc.isoformat()
        }
    })

    notifications = []
    for interview in interviews:
        # print(f"📝 Found Interview: {interview}")
        for candidate in interview.get("selected_candidates", []):
            interview_date_str = candidate.get("interview_date")

            if interview_date_str:  # Check if interview_date_str is NOT None or empt
                try:
                    interview_date_utc = parser.isoparse(interview_date_str)
                    interview_date_utc = interview_date_utc.replace(tzinfo=pytz.UTC)
                    interview_date_local = interview_date_utc.astimezone(user_timezone)

                    if interview_date_local.date() == today_local:
                        interview_time_local = interview_date_local.strftime("%I:%M %p %Z")
                        # print(f"📢 Notification for {candidate['candidate_name']} at {interview_time_local}")
                        notifications.append({
                            "job_title": interview.get("job_title", "Unknown Job"),
                            "candidate_name": candidate.get("candidate_name", "Unknown Candidate"),
                            "interview_time": interview_time_local,
                            "message": f"Interview scheduled at {interview_time_local} {user_timezone.zone}"
                        })
                    

                except ValueError as e:
                    print(f"⚠️ Date Parsing Error: {e} for date: {interview_date_str}")
                    continue  # Skip to the next candidate

            elif interview_date_str is None: # Explicitly check for None
                # print(f"⚠️ No interview date found for {candidate.get('candidate_name', 'Unknown')}")
                continue # Skip to the next candidate

            else: # Empty string case
                # print(f"⚠️ No interview date found for {candidate.get('candidate_name', 'Unknown')}")
                continue # Skip to the next candidate


    return notifications


@app.route("/get_notifications")
def get_notifications():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    notifications = get_todays_interviews() 
    
    return jsonify(notifications)



@app.route('/get_All_interviews', methods=['GET'])
def getAll_ScheduledInterviews():
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user_id = session['user']['_id']  

    if not current_user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user_timezone = request.args.get("timezone", "UTC")
    try:
        user_tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        print(f"⚠️ Invalid timezone received: {user_timezone}. Defaulting to UTC.")
        user_tz = pytz.UTC

    query = {
        "user_id": current_user_id,  
        "selected_candidates": {
            "$elemMatch": {
                "interview_date": {"$exists": True, "$ne": None}  # Remove "$type": "date"
            }
        }
    }

    scheduledInterviews = list(selected_collection.find(query))
    interviews = []

    for interview in scheduledInterviews:
        job_id = interview.get("job_id", "Unknown")
        job_title = interview.get("job_title", "Unknown")

        for candidate in interview.get("selected_candidates", []):
            interview_date_str = candidate.get("interview_date")

            if interview_date_str:  
                try:
                    # Convert stored ISO string to datetime with UTC timezone
                    interview_date_utc = parser.isoparse(interview_date_str).replace(tzinfo=pytz.UTC)
                    
                    # Convert UTC to user's time zone
                    interview_date_local = interview_date_utc.astimezone(user_tz)

                    date_str = interview_date_local.strftime("%Y-%m-%d")
                    time_str = interview_date_local.strftime("%I:%M")
                    location = candidate.get("location",'') # default location
                    status = candidate.get("status",'Pending') # default status
                    
                    interviews.append({
                        "id": str(interview["_id"]),
                        "job_id": job_id,
                        "job_title": job_title,
                        "candidate_id": candidate.get("candidate_id", "Unknown"),
                        "candidate_name": candidate.get("candidate_name", "Unknown"),
                        "email": candidate.get("email", "Unknown"),
                        "date": date_str,
                        "time": time_str,
                        "location": location,
                        "status": status,
                        "interview_date": interview_date_local.strftime("%Y-%m-%d %I:%M %p %Z")
                    })
                except ValueError as e:
                    print(f"⚠️ Date Parsing Error: {e} for date: {interview_date_str}")
                    continue  # Skip to the next candidate

    return jsonify(interviews)

# ------------------------------------------ Candidate feedback Routes ----------------------------------------------- #

@app.route('/save_feedback/<candidate_id>', methods=['POST'])
def save_feedback(candidate_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        print(" Candidate id :========= ", candidate_id)
        if not candidate_id:
            return jsonify({'error': 'Invalid candidate ID'}), 400
        
        data = request.get_json()
        print(" Data ::: ", data)
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        next_round = data.get('nextRound')
        feedback = data.get('feedback')
        selection_status = data.get('selectionStatus')

        print (f" Data : {next_round}, {feedback}, {selection_status  } ")

        if not next_round or not feedback or not selection_status:
            return jsonify({'error':'Missing require fields'}), 400
        
        selected_collection.update_one(
            {'selected_candidates.candidate_id': candidate_id},
            {'$set': {
                'selected_candidates.$.next_round': next_round,
                'selected_candidates.$.interviwer_feedback': feedback,
                'selected_candidates.$.selection_status': selection_status
            }})
        
        return jsonify({'message': 'Feedback saved successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    data = request.get_json()


# ------------------------------------------ Admin Routes -----------------------------------------------

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'GET':
        return render_template('admin_login.html')

    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            print("admin_panel: Invalid request (no JSON data)")
            return jsonify({'message': 'Invalid request'}), 400

        email = data.get('email').lower()
        password = data.get('password')

        if not email or not password:
            print("admin_panel: Email or password missing")
            return jsonify({'message': 'Email and password are required'}), 400

        user = users_collection.find_one({"registered_email": email})

        if not user:
            print(f"admin_panel: User not found: {email}")
            return jsonify({'message': 'Invalid credentials'}), 401

        if check_password_hash(user['password'], password):
            if user.get("user_type") == "Admin":
                access_token = create_access_token(identity=email)
                user['_id'] = str(user['_id'])
                session['user'] = user
                print(f"admin_panel: Login successful for {email}")
                return jsonify({'access_token': access_token, 'message': 'Login successful'}), 200
            else:
                print(f"admin_panel: Access denied for non-admin user: {email}")
                return jsonify({'message': 'Access denied. Only admins can log in.'}), 403
        else:
            print(f"admin_panel: Invalid password for {email}")
            return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/admin/dashboard')
def admin_dashboard():
   

    if 'user' not in session:
        return redirect(url_for('admin_panel'))
    
    current_user = session['user']['_id']
    user = users_collection.find_one({'_id': ObjectId(current_user)})


    if user and user.get("user_type") == "Admin":
        update_report()

        report = reports_collection.find_one({"report_type": "User Activity"}, sort=[("generated_at", -1)])
        report_data = report.get("data", {}) if report else {
            "total_users": 0,
            "active_trials": 0,
            "subscribed_users": 0,
            "open_tickets": 0,
        }
        print("admin_dashboard: report_data : ", report_data)
        return render_template('admin.html', report=report_data, user=user)
    else:
        session.pop('user', None)  # Remove unauthorized user from session
        return redirect(url_for('admin_panel'))  # Redirect to login page


def update_report():
    total_users = users_collection.count_documents({})
    active_trials = users_collection.count_documents({"subscription.status": "active", "subscription.is_subscribed": False})
    subscribed_users = users_collection.count_documents({"subscription.is_subscribed": True})
    open_tickets = tickets_collection.count_documents({"status": "Open"})
    pending_approvals = users_collection.count_documents({"verification_status": "Pending"})
    report_data = {
        "report_type": "User Activity",
        "generated_at": datetime.utcnow(),
        "data": {
            "total_users": total_users,
            "active_trials": active_trials,
            "subscribed_users": subscribed_users,
            "open_tickets": open_tickets,
            "pending_approvals": pending_approvals
        }
    }

    reports_collection.update_one({"report_type": "User Activity"}, {"$set": report_data}, upsert=True)
    print("update_report: Report updated")

@app.route('/get-users', methods=['GET'])
def get_users():

    users = users_collection.find({})
    user_list = []

    for user in users:
        user_list.append({
            "user_id": str(user.get("_id", "")),
            "username": user.get("username", "N/A"),
            "company": user.get("company", "N/A"),
            "registered_email": user.get("email", "N/A"),
            "verification_status": user.get("verification_status", "Pending"),
            "user_type": user.get("user_type", "User"),
            "created_at": user.get("created_at", datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S'),
            "trial_days_left": user.get("trial_days_left", 0),
            "notes": user.get("notes", ""),
        })

    print(f"get_users: Returning user list with {len(user_list)} users")
    return jsonify({"success": True, "users": user_list})

@app.route('/update-user-status', methods=['POST'])
def update_user_status():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()

    print("Data :\n",data)
    user_email = data.get("email")
    new_status = data.get("new_status")


    result = users_collection.update_one({"registered_email": user_email}, {"$set": {"verification_status": new_status}})

    if result.modified_count > 0:

        send_mail(user_email, "Your request has been Approved", " We are pleased to inform you that your registration request has been approved.\n ")
        return jsonify({"success": True, "message": f"User status updated to {new_status} "}), 200
    else:
        return jsonify({"success": False, "message": "No changes made"}), 400


@app.route('/get-tickets', methods=['GET'])
def get_tickets():
    try:
        tickets = list(tickets_collection.find({}))

        serialized_tickets = []
        for ticket in tickets:
            serialized_ticket = {
                "_id": str(ticket["_id"]),
                "createdAt": ticket.get("createdAt",''),
                "updated_at": ticket.get("updated_at",''),
                "ticketId": ticket.get("ticketId",'Not available'),
                "userId": str(ticket.get("userId")),
                "username": ticket.get("username"),
                "emailAddress": ticket.get("email",'email not found'),
                "subject": ticket.get("subject",'No subject'),
                "message": ticket.get("message",'No message'),
                "status": ticket.get("status"),
                "admin_notes": ticket.get("admin_notes",'')
            }
            serialized_tickets.append(serialized_ticket)

        return jsonify({"success": True, "tickets": serialized_tickets}), 200

    except Exception as e:
        print(f"Error retrieving tickets: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route('/delete-user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Deletes a user by their ID."""
    try:
        # Validate user_id
        if not ObjectId.is_valid(user_id):
            return jsonify({'message': 'Invalid user ID'}), 400

        result = users_collection.delete_one({'_id': ObjectId(user_id)})

        if result.deleted_count == 1:
            return jsonify({'message': 'User deleted successfully'}), 200
        else:
            return jsonify({'message': 'User not found'}), 404

    except InvalidUserId:
        return jsonify({'message': 'Invalid user ID'}), 400
    except UserNotFound:
        return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        print(f"Error retrieving user: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/edit-user/<user_id>', methods=['GET'])
def edit_user(user_id):
    """Deletes a user by their ID."""
    try:
        # Validate user_id
        if not ObjectId.is_valid(user_id):
            return jsonify({'message': 'Invalid user ID'}), 400

        object_id = ObjectId(user_id)

        user  = users_collection.find_one({'_id': object_id}, projection={'_id': 0})
        if user:
            user['_id'] = str(object_id) #add _id to return object
            return jsonify(user), 200
        else: 
            return jsonify({'message': 'User not found'}), 404    


    except Exception as e:
        print(f"Error deleting user: {e}")  # Log the error
        return jsonify({'message': 'Internal server error'}), 500 


@app.route('/edit-user/<user_id>', methods=['PUT'])
def update_user_route(user_id):
    try:
        object_id = ObjectId(user_id)
        data = request.get_json()

        if not data:
            return jsonify({'message': 'Invalid request data'}), 400
        
        update_fields = {}

        # Update basic user fields
        for field in ['username', 'email', 'phone', 'company', 'country', 'verification_status', 'user_type', 'is_superadmin', 'notes', 'features']:
            if field in data:
                update_fields[field] = data[field]

        # Update subscription fields and convert date strings to datetime
        if 'subscription' in data:
            subscription = data['subscription']
            sub_update = {}

            for field in ['is_subscribed', 'plan', 'status']:
                if field in subscription:
                    sub_update[field] = subscription[field]

            if sub_update:
                update_fields['subscription'] = sub_update

        if not update_fields:
            return jsonify({'message': 'No valid fields provided for update'}), 400

        update_result = users_collection.update_one(
            {'_id': object_id},
            {'$set': update_fields}
        )

        if update_result.modified_count == 1:
            return jsonify({'message': 'User updated successfully'}), 200
        elif update_result.matched_count == 1 and update_result.modified_count == 0:
            return jsonify({'message': 'User data was the same, no changes made'}), 200
        else:
            return jsonify({'message': 'User not found'}), 404

    except Exception as e:
        print(f"Error updating user: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/add-user', methods=['POST'])
def add_user():
    try:
        data = request.get_json()

        if not data:
            raise InvalidRequestData("Request body is missing or invalid JSON.")

        required_fields = ["username", "email", "phone", "password", "company", "verification_status", "user_type"]
        for field in required_fields:
            if field not in data:
                raise InvalidRequestData(f"Missing required field: {field}")

        email = data["email"]

        if users_collection.find_one({"registered_email": email}):
            return jsonify({"message": "User with this email already exists"}), 400

        is_superadmin = data.get("is_superadmin", False)  # Default to False if not provided
        if isinstance(is_superadmin, str):
            is_superadmin = is_superadmin.lower() == 'true'

        user = {
            "username": data["username"],
            "email": email,
            "phone": data["phone"],
            "password": generate_password_hash(data["password"]),
            "company": data["company"],
            "country": data.get("country", ""),
            "created_at": datetime.utcnow(),
            "verification_status": data["verification_status"],
            "user_type": data["user_type"],
            "is_superadmin": is_superadmin,
            "notes": data.get("notes", "")
        }

        users_collection.insert_one(user)
        return jsonify({"message": "User created successfully"}), 201  # Use 201 for resource creation

    except InvalidRequestData as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"message": "Internal server error"}), 500, 500   

@app.route('/signout')
def admin_signout():
    session.clear()
    response = make_response(redirect(url_for("admin_panel")))  # Create response

    # Force browser to not cache the page
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    response.headers["Cache-Control"] = "post-check=0, pre-check=0"

    return response


class InvalidUserId(Exception):
    pass

class UserNotFound(Exception):
    pass

class InvalidRequestData(Exception):
    pass


import secrets
import string


@app.route('/check-linkedin-pages')
def check_linkedin_pages():
    if 'user' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    user_id = session['user']['_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})


    
    if not user or 'user_linkedin_pages' not in user or not user['user_linkedin_pages']:
        return jsonify({'pages': []})
    
    return jsonify({'pages': user['user_linkedin_pages']})




if __name__ == '__main__':
    
    app.run(debug=True, host="0.0.0.0", port=8000)
    #socketio.run(app, debug=True)