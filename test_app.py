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

@pytest.fixture
def jwt_token():
    # Generate a JWT token with a mock payload
    payload = {"userID": 123}
    secret_key = "your_secret_key"  # Replace with your actual secret key
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def test_user_preferences_add(client, mocker):
    # Mocking database connection
    mocker.patch("app.databaseconn")

    # Mocking JWT identity
    mocker.patch("app.get_jwt_identity", return_value={"userID": 123})

    # Mocking cursor execution
    cursor_mock = mocker.Mock()
    mocker.patch("app.databaseconn.cursor", return_value=cursor_mock)

    # Mocking execute and commit methods
    cursor_mock.execute.return_value = None
    cursor_mock.commit.return_value = None

    # Test data
    test_data = {
        "public_transport": 1,
        "bike_weight": 0,
        "walking_weight": 1,
        "driving_weight": 1
    }

    # Sending POST request
    response = client.post("/api/user/preferences", json=test_data)

    # Asserting response
    assert response.status_code == 200
    assert response.json == {"message": "User preferences updated or added"}

    # Asserting database interactions
    cursor_mock.execute.assert_called_once()
    cursor_mock.commit.assert_called_once()
