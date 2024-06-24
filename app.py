from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import speech_recognition as sr
from pydub import AudioSegment
import openai
from openai import OpenAI
import json
import os, time
import requests
from flask_socketio import SocketIO, emit
from utils import extract_text_from_pdf, save_resumes_embedding, get_results
from dotenv import load_dotenv
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.footnote import footnote_plugin
from IPython.display import Markdown
import textwrap
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

AudioSegment.converter = "ffmpeg.exe"
AudioSegment.ffmpeg = "ffmpeg.exe"  # Some versions of pydub might require setting this as well
AudioSegment.ffprobe ="ffprobe.exe"  # ffprobe is part of ffmpeg and might also need to be specified

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
app.secret_key = os.getenv("SECRET_KEY")
jwt = JWTManager(app)

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client.get_database('your_database_name')
users_collection = db.get_collection('users')

openai_client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

socketio = SocketIO(app)

def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

md = (
    MarkdownIt('commonmark' ,{'breaks':True,'html':True})
    .use(front_matter_plugin)
    .use(footnote_plugin)
    .enable('table')
)

def extract_job_info(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

    # Payload to be sent in the POST request
    payload = {"contents":[{"parts":[{"text":f"""Extract job information from the following text: {text}. Please format the output as follows:
            About the job
            [Job Introduction]

            Who We Are…
            [Company Overview]

            Your New Role…
            [Job Role Description]

            Your Role Accountabilities…
            [Responsibilities and Accountabilities]

            Qualifications & Experience…
            [Qualifications and Experience]

            Hybrid Working
            [Working Conditions]

            How We Get Things Done…
            [Company Guiding Principles]

            Championing Inclusion at [Company]
            [Diversity and Inclusion Statement]

            For inquiries, contact [email] and [mobile].
            Ensure to extract and include:

            Job title (if available)
            Description (including all specified sections)
            Email (if available)
            Mobile (if available)
            If job description is not found in the text, please reply: 'Job description not found!' and If any of the point is not specified in the text just put 'Not specified!'. Extract job description in provided format only"""}]}]}
    
    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(url, data=json.dumps(payload), headers=headers)
    all_items = res.json()['candidates'][0]['content']['parts'][0]['text']
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

@app.route('/audio-to-text', methods=['POST'])
def audio_to_text():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        # Save the file temporarily
        temp_audio_path = os.path.join('temp', file.filename)
        file.save(temp_audio_path)

        # Convert audio to a compatible format (WAV)
        audio = AudioSegment.from_file(temp_audio_path)
        compatible_audio_path = "temp.wav"
        audio.export(compatible_audio_path, format="wav")

        recognizer = sr.Recognizer()
        audio_file = sr.AudioFile(compatible_audio_path)
        with audio_file as source:
            audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return jsonify({'text': 'Speech recognition could not understand audio'}), 400
        except sr.RequestError as e:
            return jsonify({'text': f'Could not request results from Google Speech Recognition service'}), 400
        print('actual text',text)
        # Clean up the temporary files
        os.remove(temp_audio_path)
        os.remove(compatible_audio_path)
        job_info = extract_job_info(text)

        with open('extracted_text.txt', 'w') as file:
            file.write(job_info)

        # Return a response without the text
        return jsonify({'message': 'Text extracted and saved to file.'})

@app.route('/pdf-to-text', methods=['POST'])
def pdf_to_text():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        text = extract_text_from_pdf(file)
        job_info = extract_job_info(text)
        with open('extracted_text.txt', 'w', encoding='utf-8') as file:
            file.write(job_info)

        # Return a response without the text
        return jsonify({'message': 'Text extracted and saved to file.'})

@app.route('/save-resumes-embedding', methods=['GET'])
def save_resumes():
    save_resumes_embedding()
    return jsonify({'message': 'Resumes embedding saved.'})

@app.route('/get-resumes', methods=['GET'])
def get_resumes():
    query = request.args.get('query')
    resumes = get_results(query)

    return resumes

@socketio.on('user_question')
def handle_user_question(data):
    query = data['query']
    entire_response = ''
    with open('extracted_text.txt', 'r', encoding='utf-8') as file:
        job_info_json = file.read()
    for message in get_results(query, job_info_json):
        entire_response += message
        rendered_response = md.render(entire_response)
        emit('bot_response', {'message': rendered_response})

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/save-text', methods=['POST'])
def save_text():
    data = request.get_json()
    if 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    text = data['text']
    with open('extracted_text.txt', 'w', encoding='utf-8') as file:
        file.write(text)

    return jsonify({'message': 'Text saved to file.'})


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


if __name__ == '__main__':
    socketio.run(app, debug=True)