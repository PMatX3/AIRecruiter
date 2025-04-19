from flask import Flask, render_template, request, redirect, url_for, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import datetime


# Initialize Flask App
app = Flask(__name__)  
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for testing

# Logging Configuration


# Replace with your own credentials.json file path
CLIENT_SECRETS_FILE = "./static/json/credentials.json"
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Check if credentials.json exists
if os.path.exists(CLIENT_SECRETS_FILE):
    print("✅ Credentials file found: %s", CLIENT_SECRETS_FILE)
else:
   print("❌ Credentials file NOT found: %s", CLIENT_SECRETS_FILE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=url_for('callback', _external=True)
        )
        authorization_url, state = flow.authorization_url(access_type='offline')
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
      print("❌ Error in login: %s", str(e))
      return "Error in login. Check server logs."

@app.route('/callback')
def callback():
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=session.get('state'),
            redirect_uri=url_for('callback', _external=True)
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        session['credentials'] = credentials_to_dict(credentials)
        print("✅ Google OAuth successful!")
        return redirect(url_for('schedule_meeting'))
    except Exception as e:
      print("❌ Error in OAuth callback: %s", str(e))
      return "Error in OAuth callback. Check server logs."

@app.route('/schedule_meeting', methods=['GET', 'POST'])
def schedule_meeting():
    if 'credentials' not in session:
        print("⚠️ No credentials found in session. Redirecting to login.")
        return redirect(url_for('login'))

    credentials = session['credentials']
    service = build('calendar', 'v3', credentials=credentials)

    if request.method == 'POST':
        try:
            event = {
                'summary': request.form['summary'],
                'start': {
                    'dateTime': request.form['start'],
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': request.form['end'],
                    'timeZone': 'America/Los_Angeles',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': 'some-random-string',
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            }

            event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
            print("✅ Meeting scheduled: %s", event.get('htmlLink'))
            return f"Meeting scheduled: {event.get('htmlLink')}"
        except Exception as e:
          print("❌ Error scheduling meeting: %s", str(e))
          return "Error scheduling meeting. Check server logs."

    return render_template('schedule_meeting.html')

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

# if __name__ == '__main__':
#     app.run(debug=True, host="0.0.0.0", port=5001)
