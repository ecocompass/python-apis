import pytest
from app import app
from unittest.mock import patch

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_signup_existing_user(client):
    # Define a test user that already exists in the database
    existing_user = {
        'username': 'Jane Doe',
        'password': 'password123',
        'email': 'jane@example.com'
    } 
    # Make a POST request to the signup endpoint to create the user
    client.post('/api/auth/signup', json=existing_user)
    
    # Make another POST request with the same email
    response = client.post('/api/auth/signup', json=existing_user)
    # Assert that the response status code is 409 (conflict)
    assert response.status_code == 409
    # Assert that the response contains the expected message
    assert response.json['message'] == 'User already exists'

def test_invalid_username_format(client):
    # Define a test user with an invalid username format
    invalid_user = {
        'username': 'InvalidUsernameFormat',
        'password': 'password123',
        'email': 'invalid@example.com'
    }
    
    # Make a POST request to the signup endpoint with the invalid user
    response = client.post('/api/auth/signup', json=invalid_user)
    
    # Assert that the response status code is 400
    assert response.status_code == 400

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Invalid username format'

def test_login_success(client):
    # Define a test user
    test_user = {
        'email': 'test@test.com',
        'password': 'test_password'
    }
    
    # Make a POST request to the login endpoint
    response = client.post('/api/auth/login', json=test_user)
    
    # Assert that the response status code is 200
    assert response.status_code == 200

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Login successful'
    
    # Assert that the response contains an access token
    assert 'access_token' in response.json

def test_missing_username_field(client):
    # Define a test user with missing username field
    missing_username_user = {
        'password': 'password123',
        'email': 'john@example.com'
    }
    # Make a POST request to the signup endpoint with the user missing the username field
    response = client.post('/api/auth/signup', json=missing_username_user)
    
    # Assert that the response status code is 400
    assert response.status_code == 400

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Empty Username'

def test_login_success(client):
    # Define a test user
    test_user = {
        'email': 'test@test.com',
        'password': 'test_password'
    }
    
    # Make a POST request to the login endpoint
    response = client.post('/api/auth/login', json=test_user)
    
    # Assert that the response status code is 200
    assert response.status_code == 200

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Login successful'
    
    # Assert that the response contains an access token
    assert 'access_token' in response.json

def test_login_invalid_email(client):
    # Define a test user with an invalid email
    invalid_email_user = {
        'email': 'test@testtest.com',
        'password': 'test_password'
    }
    
    # Make a POST request to the login endpoint with the invalid email user
    response = client.post('/api/auth/login', json=invalid_email_user)
    
    # Assert that the response status code is 401
    assert response.status_code == 401

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Invalid email or password'

def test_login_invalid_password(client):
    # Define a test user with invalid password
    invalid_password_user = {
        'email': 'test@test.com',
        'password': 'pass'
    }
    
    # Make a POST request to the login endpoint with the invalid password user
    response = client.post('/api/auth/login', json=invalid_password_user)
    
    # Assert that the response status code is 401
    assert response.status_code == 401

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Invalid email or password'

def test_login_missing_email(client):
    # Define a test user with missing email
    missing_email_user = {
        'password': 'password123'
    }
    
    # Make a POST request to the login endpoint with the user missing the email field
    response = client.post('/api/auth/login', json=missing_email_user)
    
    # Assert that the response status code is 401
    assert response.status_code == 400

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Empty email or password'

def test_login_missing_password(client):
    # Define a test user with missing password
    missing_password_user = {
        'email': 'john@example.com'
    }
    
    # Make a POST request to the login endpoint with the user missing the password field
    response = client.post('/api/auth/login', json=missing_password_user)
    
    # Assert that the response status code is 401
    assert response.status_code == 400

    # Assert that the response contains the expected message
    assert response.json['message'] == 'Empty email or password'

@patch('app.generate_access_token')
def test_logout_success(mock_generate_access_token, client):
    # Mock the generate_access_token function to return a dummy token
    mock_generate_access_token.return_value = 'dummy_token'

    # Make a DELETE request to the logout endpoint with the access token in the header
    response = client.delete('/api/auth/logout', headers={'Authorization': 'Bearer dummy_token'})
    
    # Assert that the response status code is 200
    assert response.status_code == 200

    # Assert that the response contains the expected message
    assert response.json['msg'] == 'Access token revoked'
