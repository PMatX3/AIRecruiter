from flask import Flask, request, jsonify, render_template
import speech_recognition as sr
from PyPDF2 import PdfReader
from pydub import AudioSegment
import openai
from openai import OpenAI
import json
import os, time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AudioSegment.converter = "ffmpeg.exe"
AudioSegment.ffmpeg = "ffmpeg.exe"  # Some versions of pydub might require setting this as well
AudioSegment.ffprobe ="ffprobe.exe"  # ffprobe is part of ffmpeg and might also need to be specified

app = Flask(__name__)
openai_client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
def extract_job_info(text):

    # response = openai_client.chat.completions.create(
    #     model="gpt-3.5-turbo",
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant."},
    #         {"role": "user", "content": "Extract job information from the following text. Please give me dict format and don't forget to extract job_title,salary,start_date,close_date,email,mobile this things are must."},
    #         {"role": "user", "content": text}
    #     ]
    # )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

    # Payload to be sent in the POST request
    payload = {"contents":[{"parts":[{"text":f"Extract job information from the following text:{text}. Please give me clean dict format and don't forget to extract job_title,salary,start_date,close_date,email,mobile this things are must.Also, Job info founded or not I want  dict only. If the jobs is not specified in text then reply 'Jobs not found!'"}]}]}
    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(url, data=json.dumps(payload), headers=headers)
    print(res.json())
    all_items = res.json()['candidates'][0]['content']['parts'][0]['text']
    print('```' in all_items)
    if '```' in all_items:
        all_items = all_items.split('```json')[1].split('```')[0]
        all_items = json.loads(all_items)
    return all_items

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/audio-to-text', methods=['POST'])
def audio_to_text():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        start_time1 = time.time()
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
            return jsonify({'text': 'Speech recognition could not understand audio'})
        except sr.RequestError as e:
            return jsonify({'text': f'Could not request results from Google Speech Recognition service'})
        print('actual text',text)
        # Clean up the temporary files
        os.remove(temp_audio_path)
        os.remove(compatible_audio_path)
        end_time1 = time.time()
        print(f"Time taken to convert audio to text: {end_time1 - start_time1} seconds")
        start_time = time.time()

        job_info = extract_job_info(text)
        end_time = time.time()
        print(f"Time taken to extract job info: {end_time - start_time} seconds")
        job_info_json = json.dumps(job_info)
        return jsonify({'text': job_info_json})

@app.route('/pdf-to-text', methods=['POST'])
def pdf_to_text():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        pdf_reader = PdfReader(file)
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text()
        job_info = extract_job_info(text)
        job_info_json = json.dumps(job_info)
        return jsonify({'text': job_info_json})

if __name__ == '__main__':
    app.run(debug=True)