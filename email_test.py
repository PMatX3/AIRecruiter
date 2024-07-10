import imaplib 
import email
import os
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def clean_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()

def extract_attachments(email_message, subject_text, output_dir):
    if subject_text.lower() in email_message['subject'].lower():
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename:
                filename = decode_header(filename)[0][0]
                if isinstance(filename, bytes):
                    filename = filename.decode()
                
                filename = clean_filename(filename)
                
                # Check if the file is a PDF
                if filename.lower().endswith('.pdf'):
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    print(f"Extracted PDF: {filename}")

def send_mail(recipient_email, subject, body, attachment_path=None):
    # Create the email message
    message = MIMEMultipart()
    message['From'] = 'sender_email'
    message['To'] = 'recipient_email'
    message['Subject'] = subject

    # Add body to email
    message.attach(MIMEText(body, 'plain'))

    # Add attachment if provided
    if attachment_path:
        with open(attachment_path, 'rb') as file:
            part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        message.attach(part)

    # Connect to Gmail's SMTP server
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login('sender_email', 'app_password')
        server.send_message(message)

    print("Email sent successfully")

def get_resume(email=None, password=None):
    email_address = 'email'
    password = 'password'  # Use an app-specific password
    imap_server = 'imap.gmail.com'
    subject_text = 'Up-4ever'  # The text to search for in the subject
    output_dir = 'attachments'  # Directory to save attachments

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Connect to the Gmail IMAP server
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(email_address, password)
    mail.select('inbox')

    # Search for emails with the specific subject text
    _, message_numbers = mail.search(None, f'SUBJECT "{subject_text}"')

    for num in message_numbers[0].split():
        _, msg_data = mail.fetch(num, '(RFC822)')
        print(msg_data)
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        extract_attachments(email_message, subject_text, output_dir)

    mail.logout()

if __name__ == '__main__':
    get_resume()
    # send_mail('recipient@example.com', 'Test Subject', 'This is a test email', 'path/to/attachment.pdf')
