import imaplib 
import email
import os
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import boto3
from email import message_from_bytes
from email.parser import BytesParser
from email import policy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
SES_REGION = os.getenv('SES_REGION')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')

def clean_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()

def extract_attachments(email_message, subject_text, output_dir, email_address):
    if subject_text.lower() in email_message['subject'].lower():
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            if filename:
                filename = decode_header(filename)[0][0]
                filename = email_address + "_" + filename
                if isinstance(filename, bytes):
                    filename = filename.decode()
                
                filename = clean_filename(filename)
                # Check if the file is a PDF
                if filename.lower().endswith('.pdf'):
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))

def send_mail(recipient_email, subject, body, attachment_paths=None):
    # Create the email message
    message = MIMEMultipart()
    message['From'] = EMAIL_ADDRESS
    message['To'] = recipient_email
    message['Subject'] = subject

    # Add body to email
    message.attach(MIMEText(body, 'plain'))
    
    # Add attachment if provided
    if attachment_paths:
        for attachment_path in attachment_paths:
            with open(attachment_path, 'rb') as file:
                part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            message.attach(part)

    # Connect to Gmail's SMTP server
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("=============\n\n")
        print(message)
        print("=============\n\n")
        server.send_message(message)

    print("Email sent successfully")

def send_email_2(recipients, subject, username, reset_link):
    ses = boto3.client(
        'ses',
        region_name=SES_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    html_message = f"""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>Reset Your Password</title>
                        </head>
                        <body>
                            <div class="inbox-data-content-intro">

                            <div
                                style="
                                background-color: rgb(255, 255, 255);
                                border-radius: 10px;
                                padding: 40px;
                                box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 8px;
                                max-width: 400px;
                                margin: 0px auto;
                                "
                            >
                                <h1 style="color: rgb(51, 51, 51); margin-bottom: 20px">
                                Reset Your Password,
                                <span style="color: rgb(0, 123, 255); font-weight: bold">{username}</span>!
                                </h1>
                                <p style="color: rgb(102, 102, 102); margin-bottom: 30px">
                                You recently requested to reset your password. Click the button below to
                                reset it:
                                </p>
                                <a
                                href="{reset_link}"
                                style="
                                    display: inline-block;
                                    background-color: rgb(0, 123, 255);
                                    color: rgb(255, 255, 255);
                                    padding: 10px 20px;
                                    border-radius: 5px;
                                    text-decoration: none;
                                    margin-top: 20px;
                                    transition: background-color 0.3s;
                                "
                                >Reset Password</a
                                >
                                <p style="color: rgb(102, 102, 102); margin-bottom: 30px">
                                If you didn't request a password reset, you can ignore this email.
                                </p>
                                <div style="margin-top: 30px; color: rgb(153, 153, 153); font-size: 14px">
                                <p style="color: rgb(102, 102, 102); margin-bottom: 30px">
                                    If you encounter any issues, please contact support at
                                    <a href="mailto:support@yourbestcandidate.ai"
                                    >support@yourbestrecruiter.ai</a
                                    >.
                                </p>
                                <p style="color: rgb(102, 102, 102); margin-bottom: 30px">
                                    This email was sent automatically. Please do not reply to this email.
                                </p>
                                </div>
                            </div>
                            </div>
                        </body>
                        </html>
                    """

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={'ToAddresses': recipients},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Html': {'Data': html_message}
            }
        }
    )

def extract_email_address(email_address_bytes):
    # Parse the email
    email_message = BytesParser(policy=policy.default).parsebytes(email_address_bytes)
    
    # Get the 'to' field
    to = email_message['to']
    
    # Check if the 'to' field contains an email address in angle brackets or plain text
    if '<' in str(to) and '>' in str(to):
        # Extract email from format <email@example.com>
        email_address = str(to).split("<")[1].split(">")[0]
    else:
        # If no angle brackets, assume it's a plain email address
        email_address = str(to).strip()
    
    print("Extracted email Address:", email_address)
    return email_address

def get_resume(job_id):
    print("get resume for job_id: ", job_id)
    subject_text = job_id
    output_dir = 'attachments'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(output_dir + f"/{job_id}"):
        os.makedirs(output_dir + f'/{job_id}')
    output_dir = output_dir + f'/{job_id}'
    try:
        # Connect to the Gmail IMAP server
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select('inbox')

        # Search for emails with the specific subject text
        _, message_numbers = mail.search(None, f'SUBJECT "{job_id}"')
        print(f"message_numbers: {message_numbers}")
        for num in message_numbers[0].split():
            _, msg_data = mail.fetch(num, '(RFC822)')
            email_body = msg_data[0][1]
            email_address = extract_email_address(email_body)
            email_message = message_from_bytes(email_body)
            extract_attachments(email_message, subject_text, output_dir, email_address)
        mail.logout()
    except Exception as e:
        print(f"Error in get_resume: {str(e)}")
        raise


# if __name__ == '__main__':
#     get_resume("675c1596926db8aaa214e981")
#     send_mail(
#     'nak.logixbuilt@gmail.com',
#     'this is Test Email Subject',
#     'This is a test email body.',
#     'path/to/pdf'
# )
