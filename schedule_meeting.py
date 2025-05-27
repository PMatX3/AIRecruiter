import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.apps import meet_v2
from flask import jsonify
from email_test import send_mail
from mongo_connection import get_mongo_client

import pytz
from dateutil import parser
from datetime import datetime

mongo_client = get_mongo_client()
db = mongo_client.get_database('recruiter')

selected_collection = db.get_collection('selected_candidates') if db.get_collection('selected_candidates') is not None  else db.create_collection('selected_candidates')


# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/meetings.space.created', 'https://www.googleapis.com/auth/calendar']

def get_credentials():
    """Authenticate and return the credentials."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                    'static/json/yourbest_creds.json', 
                    SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            print('\nPlease visit this URL to authorize this application:')
            print(auth_url)
            print('\nAfter authorization, you will get a code. Enter it below:')
            code = input('Enter the authorization code: ')
            flow.fetch_token(code=code)
            creds = flow.credentials


        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

def create_open_google_meet():
    """Create an open Google Meet link using the Google Meet API."""
    # Get the credentials
    creds = get_credentials()

    # Create a synchronous client for the Google Meet API
    client = meet_v2.SpacesServiceClient(credentials=creds)

    # Initialize request argument(s)
    request = meet_v2.CreateSpaceRequest(
        space={
            "config": {
                "access_type": meet_v2.SpaceConfig.AccessType.OPEN,  # This makes the meeting open to anyone with the link
            }
        }
    )

    # Make the request
    response = client.create_space(request=request)

    # Extract the meeting URI from the response
    meeting_uri = response.meeting_uri
    print(f"Open Google Meet Link: {meeting_uri}")
    return meeting_uri


def handle_schedule(user_id, job_id,candidate_id, candidate_name, candidate_email, recruiter_email, datetime_str, user_timezone_str):
    print("user_id", user_id)
    print("job_id", job_id)
    print("candidate_id", candidate_id)
    print("candidate_name", candidate_name)
    print("candidate_email", candidate_email)
    print("recruiter_email", recruiter_email)
    print("datetime_str", datetime_str)
    print("user_timezone_str", user_timezone_str)
    try:
    
        user_timezone = pytz.timezone(user_timezone_str)
        local_time = parser.isoparse(datetime_str).astimezone(user_timezone)
        utc_time = local_time.astimezone(pytz.UTC)

       

        current_utc_time = datetime.now(pytz.UTC)

        if utc_time < current_utc_time:
            print("Error: Interview date is in the past.")
            return jsonify({"success": False, "error": "Interview date cannot be in the past"}), 400

        print("Step 2: Creating Google Meet link...")
        google_meet_link = create_open_google_meet()
        if not google_meet_link:
            print("Error: Failed to create Google Meet link.")
            return jsonify({"success": False, "error": "Failed to create Google Meet link"}), 500

        interview_datetime_local = utc_time.astimezone(user_timezone)
        formatted_local_datetime = interview_datetime_local.strftime("%d-%m-%Y %I:%M %p %Z")

        print(f"Formatted interview datetime for user: {formatted_local_datetime}")

        # Email Details for Schedule
        subject_candidate = "Google Meet Interview Scheduled"
        body_candidate = f"""Dear {candidate_name},\n\nYour interview has been scheduled for {formatted_local_datetime}.\n\nPlease join the meeting using the link below:\n{google_meet_link}\n\nBest regards,\nYour Recruitment Team"""

        subject_recruiter = f"Interview Scheduled with {candidate_name}"
        body_recruiter = f"""Dear Recruiter,\n\nAn interview has been scheduled with candidate {candidate_name} for {formatted_local_datetime}.\n\nYou can join the meeting using the following Google Meet link:\n{google_meet_link}\n\nPlease be prepared for the interview.\n\nBest regards,\nYour Recruitment Team"""

       

        print("Step 4: Updating database...")
        update_result = selected_collection.update_one(
            {
                "job_id": job_id,
                "user_id": user_id,
                "selected_candidates.candidate_id": candidate_id
            },
            {
                "$set": {
                    "selected_candidates.$.interview_date": utc_time.isoformat(),  # Store in UTC
                    "selected_candidates.$.status": "Scheduled",  # Set interview status
                    "selected_candidates.$.selection_status": "Interview Scheduled",
                    "selected_candidates.$.location": google_meet_link  # Store Google Meet link
                }
            }
        )

        print(f"MongoDB update result: {update_result.raw_result}")

        if update_result.modified_count == 0:
            print("Error: Failed to update interview date in the database.")
            return jsonify({"success": False, "error": "Failed to update interview date"}), 500

        
        print("Step 3: Sending emails...")
        email_sent_to_candidate = send_mail(candidate_email, subject_candidate, body_candidate)
        email_sent_to_recruiter = send_mail(recruiter_email, subject_recruiter, body_recruiter)

        print(f"Email sent status - Candidate: {email_sent_to_candidate}, Recruiter: {email_sent_to_recruiter}")

        if not email_sent_to_candidate or not email_sent_to_recruiter:
            print("Error: Failed to send emails.")
            return jsonify({"success": False, "error": " Failed to send emails"}), 500
        
        return jsonify({"success": True, "meet_link": google_meet_link, "local_datetime": formatted_local_datetime})

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return jsonify({"success": False, "error": f"An error occurred during scheduling: {str(e)}"}), 500

def handle_reschedule(user_id, job_id, candidate_id, candidate_name, candidate_email, recruiter_email, datetime_str, user_timezone_str):
    """Handles rescheduling an interview."""

    print(f"Handling reschedule request for user_id: {user_id}, \n candidate_id : {candidate_id}, \njob_id: {job_id}, \ncandidate: {candidate_name}")

    try:
        if datetime_str:
            user_timezone = pytz.timezone(user_timezone_str)
            local_time = parser.isoparse(datetime_str).astimezone(user_timezone)
            utc_time = local_time.astimezone(pytz.UTC)

            current_utc_time = datetime.now(pytz.UTC)
            if utc_time < current_utc_time:
                print("Attempted reschedule to a past date.")
                return jsonify({"success": False, "error": "New interview date cannot be in the past"}), 400

            google_meet_link = create_open_google_meet()
            if not google_meet_link:
                print("Failed to create Google Meet link.")
                return jsonify({"success": False, "error": "Failed to create Google Meet link"}), 500

            update_result = selected_collection.update_one(
                {
                    "job_id": job_id,
                    "user_id": user_id,
                    "selected_candidates.candidate_id": candidate_id
                },
                {
                    "$set": {
                        "selected_candidates.$.interview_date": utc_time.isoformat(),  # Store in UTC
                        "selected_candidates.$.status": "Rescheduled",  # Set interview status
                        "selected_candidates.$.location": google_meet_link  # Store Google Meet link
                    }
                }
            )

            print(f"MongoDB update result: modified_count={update_result.modified_count}")

            interview_datetime_local = utc_time.astimezone(user_timezone)
            formatted_local_datetime = interview_datetime_local.strftime("%d-%m-%Y %I:%M %p %Z")

            # Email Details for Reschedule
            subject_candidate = "Google Meet Interview Rescheduled"
            body_candidate = f"""Dear {candidate_name},\n\nYour interview has been rescheduled for {formatted_local_datetime}.\n\nPlease use the same meeting link.\n\nBest regards,\nYour Recruitment Team"""

            subject_recruiter = f"Interview with {candidate_name} Rescheduled"
            body_recruiter = f"""Dear Recruiter,\n\nAn interview with candidate {candidate_name} has been rescheduled for {formatted_local_datetime}.\n\nPlease use the same meeting link.\n\nBest regards,\nYour Recruitment Team"""

            if update_result.modified_count == 0:
                print("Failed to reschedule interview in database.")
                return jsonify({"success": False, "error": "Failed to reschedule interview"}), 500

            email_sent_to_candidate = send_mail(candidate_email, subject_candidate, body_candidate)
            email_sent_to_recruiter = send_mail(recruiter_email, subject_recruiter, body_recruiter)

            print(f"Email sent to candidate: {email_sent_to_candidate}, recruiter: {email_sent_to_recruiter}")

            if not email_sent_to_candidate or not email_sent_to_recruiter:
                print("Failed to send emails.")
                return jsonify({"success": False, "error": "Failed to send emails"}), 500

            print(f"Interview Rescheduled successfully for {candidate_name}.")
            return jsonify({"success": True, "message": "Interview rescheduled successfully."})
        else:
            print("datetime_str is missing")
            return jsonify({"success": False, "error": "Datetime string is missing"}),400

    except Exception as e:
        print(f"An error occurred during rescheduling: {str(e)}") #use exception instead of error to get the full stack trace
        return jsonify({"success": False, "error": f"An error occurred during rescheduling: {str(e)}"}), 500
    

def handle_cancel(user_id, job_id, candidate_id, candidate_name, candidate_email, recruiter_email, datetime_str, user_timezone_str):
    print("Cancel intercview called ")
    try:
        update_result = selected_collection.update_one(
            {
                "job_id": job_id,
                "user_id": user_id,
                "selected_candidates.candidate_id": candidate_id
            },
            {
                "$set": {
                    "selected_candidates.$.status": "Canceled",
                    "interview_date": None
                },
                "$unset": {
                    "selected_candidates.$.location": ""  # Removes 'location' field
                }
            }
        )

        if update_result.modified_count == 0:
            return jsonify({"success": False, "error": "Failed to cancel interview"}), 500

        # Email Details for Cancel
        subject_candidate = "Google Meet Interview Canceled"
        body_candidate = f"""Dear {candidate_name},\n\nYour interview has been canceled.\n\nBest regards,\nYour Recruitment Team"""

        subject_recruiter = f"Interview with {candidate_name} Canceled"
        body_recruiter = f"""Dear Recruiter,\n\nThe interview with candidate {candidate_name} has been canceled.\n\nBest regards,\nYour Recruitment Team"""
        
        email_sent_to_candidate = send_mail(candidate_email, subject_candidate, body_candidate)
        email_sent_to_recruiter = send_mail(recruiter_email, subject_recruiter, body_recruiter)

        if not email_sent_to_candidate or not email_sent_to_recruiter:
            return jsonify({"success": False, "error": "Failed to send cancellation emails"}), 500
        print(" interview Canceledd !!!!!!!")
        return jsonify({"success": True, "message": "Interview canceled successfully."})

    except Exception as e:
        return jsonify({"success": False, "error": f"An error occurred during cancellation: {str(e)}"}), 500

if __name__ =='__main__':
    get_credentials()
    