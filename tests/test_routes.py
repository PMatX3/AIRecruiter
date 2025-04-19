# import unittest
# from app import app
# from flask import json
# import io

# class TestAPI(unittest.TestCase):
#     def setUp(self):
#         self.app = app.test_client()
#         self.app.testing = True
#         # Add a login step to get a valid session
#         response = self.app.post('/login', json={
#             'email': 'test1@gmail.com',
#             'password': '123'
#         })
#         self.assertEqual(response.status_code, 200)

#     def test_register(self):
#         response = self.app.post('/register', json={
#             'username': 'testuser',
#             'phone': '1234567890',
#             'email': 'newuser@example.com',
#             'password': 'password123'
#         })
#         self.assertEqual(response.status_code, 201)

#     def test_login(self):
#         # First, register a new user
#         register_response = self.app.post('/register', json={
#             'username': 'testloginuser',
#             'phone': '1234567890',
#             'email': 'testlogin@example.com',
#             'password': 'password123'
#         })
#         self.assertEqual(register_response.status_code, 201, f"Registration failed: {register_response.data}")

#         # Now try to login with the new user
#         login_response = self.app.post('/login', json={
#             'email': 'testlogin@example.com',
#             'password': 'password123'
#         })
#         self.assertEqual(login_response.status_code, 200, f"Login failed: {login_response.data}")
        
#         # Print response data for debugging
#         print(f"Login response: {login_response.data}")

#     def test_logout(self):
#         response = self.app.get('/logout')
#         self.assertEqual(response.status_code, 302)

#     def test_home(self):
#         response = self.app.get('/')
#         self.assertIn(response.status_code, [200, 302])

#     # def test_audio_to_text(self):
#     #     data = {}
#     #     response = self.app.post('/audio-to-text', data=data, content_type='multipart/form-data')
#     #     self.assertEqual(response.status_code, 400)

#     def test_update_jobdesc(self):
#         # First, create a job to update
#         create_response = self.app.post('/save-text', json={'text': 'Initial job description'})
#         self.assertEqual(create_response.status_code, 200)
#         job_id = json.loads(create_response.data)['job_id']
        
#         # Now update the job
#         response = self.app.post('/update_jobdesc', json={
#             'text': 'Updated job description',
#             'job_id': job_id
#         })
#         self.assertEqual(response.status_code, 200)

#     def test_start_process(self):
#         response = self.app.get('/start-process')
#         self.assertEqual(response.status_code, 200)

#     def test_save_text(self):
#         response = self.app.post('/save-text', json={'text': 'Some job description text'})
#         self.assertEqual(response.status_code, 200)

#     def test_get_jobs(self):
#         response = self.app.get('/jobs')
#         self.assertEqual(response.status_code, 200)

#     def test_get_all_jobs_progress(self):
#         response = self.app.get('/all-jobs-progress')
#         self.assertEqual(response.status_code, 200)

#     def test_delete_job(self):
#         # First, create a job to delete
#         create_response = self.app.post('/save-text', json={'text': 'Job to delete'})
#         self.assertEqual(create_response.status_code, 200)
#         job_id = json.loads(create_response.data)['job_id']
        
#         # Now delete the job
#         response = self.app.delete(f'/delete-job/{job_id}')
#         self.assertEqual(response.status_code, 200)

# if __name__ == '__main__':
#     unittest.main()

import pytest
from flask import session
from app import app, mongo_client, jobs_collection, users_collection
from bson import ObjectId
from werkzeug.security import generate_password_hash
import json
from unittest.mock import patch, MagicMock
import io

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db(monkeypatch):
    mock_mongo = MagicMock()
    monkeypatch.setattr('app.mongo_client', mock_mongo)
    return mock_mongo

@pytest.fixture
def mock_users_collection(mock_db):
    return mock_db.get_database.return_value.get_collection.return_value

@pytest.fixture
def mock_jobs_collection(mock_db):
    return mock_db.get_database.return_value.get_collection.return_value

def test_register(client, mock_users_collection):
    mock_users_collection.find_one.return_value = None
    mock_users_collection.insert_one.return_value = MagicMock()

    response = client.post('/register', json={
        'username': 'testuser',
        'phone': '1234567890',
        'email': 'test@example1.com',
        'password': 'password123'
    })

    assert response.status_code == 201
    assert b'User registered successfully' in response.data

def test_login_success(client, mock_users_collection):
    hashed_password = generate_password_hash('password123')
    mock_users_collection.find_one.return_value = {
        '_id': ObjectId('123456789012345678901234'),
        'email': 'test@example1.com',
        'password': hashed_password
    }

    response = client.post('/login', json={
        'email': 'test@example1.com',
        'password': 'password123'
    })

    assert response.status_code == 200
    assert b'access_token' in response.data

def test_login_failure(client, mock_users_collection):
    mock_users_collection.find_one.return_value = None

    response = client.post('/login', json={
        'email': 'nonexistent@example.com',
        'password': 'wrongpassword'
    })

    assert response.status_code == 401
    assert b'Invalid credentials' in response.data

def test_logout(client):
    with client.session_transaction() as sess:
        sess['user'] = {'_id': '123456789012345678901234'}

    response = client.get('/logout')
    assert response.status_code == 302
    assert 'login' in response.location

@pytest.mark.parametrize('route', ['/audio-to-text', '/pdf-to-text', '/save-text'])
def test_authenticated_routes(client, route):
    response = client.post(route)
    assert response.status_code == 401 or response.status_code == 302

def test_get_jobs(client, mock_jobs_collection):
    with client.session_transaction() as sess:
        sess['user'] = {'_id': '123456789012345678901234'}

    mock_jobs_collection.find.return_value = [
        {'_id': ObjectId('123456789012345678901234'), 'title': 'Job 1'},
        {'_id': ObjectId('123456789012345678901235'), 'title': 'Job 2'}
    ]

    response = client.get('/jobs')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[0]['title'] == 'Job 1'
    assert data[1]['title'] == 'Job 2'

def test_get_job_desc(client, mock_jobs_collection):
    job_id = '123456789012345678901234'
    mock_jobs_collection.find_one.return_value = {
        '_id': ObjectId(job_id),
        'job_info': '# Job Description\n\nThis is a test job.',
        'edited': False
    }

    response = client.get(f'/get_jobdesc/{job_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert '<h1>Job Description</h1>' in data['description']
    assert data['edited'] is False

def test_update_job_desc(client, mock_jobs_collection):
    job_id = '123456789012345678901234'
    new_desc = '# Updated Job Description\n\nThis is an updated test job.'

    mock_jobs_collection.update_one.return_value = MagicMock(modified_count=1)

    response = client.post('/update_jobdesc', json={
        'job_id': job_id,
        'text': new_desc
    })

    assert response.status_code == 200
    assert b'Job description updated successfully' in response.data

def test_delete_job(client, mock_jobs_collection):
    with client.session_transaction() as sess:
        sess['user'] = {'_id': '123456789012345678901234'}

    job_id = '123456789012345678901234'
    mock_jobs_collection.find_one.return_value = {
        '_id': ObjectId(job_id),
        'userid': '123456789012345678901234'
    }
    mock_jobs_collection.delete_one.return_value = MagicMock(deleted_count=1)

    response = client.delete(f'/delete-job/{job_id}')
    assert response.status_code == 200
    assert b'Job deleted successfully' in response.data

@patch('app.extract_text_from_pdf')
@patch('app.extract_job_info')
@patch('app.create_or_get_job')
def test_pdf_to_text(mock_create_job, mock_extract_job_info, mock_extract_text, client, mock_text_data_collection):
    mock_extract_text.return_value = "Extracted PDF text"
    mock_extract_job_info.return_value = "Extracted job info"
    mock_create_job.return_value = "new_job_id"

    with client.session_transaction() as sess:
        sess['user'] = {'_id': '123456789012345678901234'}

    response = client.post('/pdf-to-text', data={
        'file': (io.BytesIO(b"dummy pdf content"), 'test.pdf')
    }, content_type='multipart/form-data')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'PDF processed and text saved to database.'
    assert data['job_id'] == 'new_job_id'

@patch('app.sr.Recognizer')
@patch('app.AudioSegment')
@patch('app.extract_job_info')
@patch('app.create_or_get_job')
def test_audio_to_text(mock_create_job, mock_extract_job_info, mock_audio_segment, mock_recognizer, client, mock_text_data_collection):
    mock_recognizer.return_value.recognize_google.return_value = "Transcribed audio text"
    mock_extract_job_info.return_value = "Extracted job info"
    mock_create_job.return_value = "new_job_id"

    with client.session_transaction() as sess:
        sess['user'] = {'_id': '123456789012345678901234'}

    response = client.post('/audio-to-text', data={
        'file': (io.BytesIO(b"dummy audio content"), 'test.wav')
    }, content_type='multipart/form-data')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Audio processed and text saved to database.'
    assert data['job_id'] == 'new_job_id'

def test_start_process(client, mock_jobs_collection):
    mock_jobs_collection.find.return_value = [
        {'_id': ObjectId('123456789012345678901234'), 'process_status': {'Creating Job description': 'not_started'}},
        {'_id': ObjectId('123456789012345678901235'), 'process_status': {'Creating Job description': 'done'}}
    ]

    with patch('app.run_process.delay') as mock_run_process:
        response = client.get('/start-process')
        assert response.status_code == 200
        assert b'Process started for all unprocessed jobs' in response.data
        mock_run_process.assert_called_once_with('123456789012345678901234')

def test_get_status(client, mock_jobs_collection):
    job_id = '123456789012345678901234'
    mock_jobs_collection.find_one.return_value = {
        '_id': ObjectId(job_id),
        'process_status': {
            'Creating Job description': 'done',
            'Job posting': 'in_progress'
        }
    }

    response = client.get(f'/status/{job_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['Creating Job description'] == 'done'
    assert data['Job posting'] == 'in_progress'

if __name__ == '__main__':
    pytest.main()