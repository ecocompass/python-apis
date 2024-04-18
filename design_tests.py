import time
import requests
import pytest
import random
import string
import logging

logger = logging.getLogger(__name__)

# Base URL of the API
BASE_URL = "http://prod.ecocompass.live:80"

def generate_random_user():
    part_one = ''.join(random.choice(string.ascii_letters) for _ in range(random.randint(3, 6)))
    part_two = ''.join(random.choice(string.ascii_letters) for _ in range(random.randint(3, 6)))
    username = f"{part_one.capitalize()} {part_two.capitalize()}"
    email = f"{part_one.lower()}{part_two.lower()}@example.com"
    password = f"{part_one.capitalize()}{part_two.capitalize()}"
    return username, email, password

def signup_user(email, username, password):
    url = f"{BASE_URL}/api/auth/signup"
    response = requests.post(url, json={"email": email, "username": username, "password": password})
    if response.status_code == 201:
        logger.info(f"Successfully signed up user: {email}")
    else:
        logger.error(f"Failed to sign up user: {email}. Response: {response.text}")
    return response

def login_user(email, password):
    url = f"{BASE_URL}/api/auth/login"
    response = requests.post(url, json={"email": email, "password": password})
    if response.status_code == 200:
        logger.info(f"Successfully logged in user: {email}")
    else:
        logger.error(f"Failed to log in user: {email}. Response: {response.text}")
    return response

def logout_user(token):
    url = f"{BASE_URL}/api/auth/logout"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        logger.info("Successfully logged out user.")
    else:
        logger.error(f"Failed to log out user. Response: {response.text}")
    return response

def protected_api_call(token):
    url = f"{BASE_URL}/protected"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        logger.info("Protected API call successful.")
    else:
        logger.error("Protected API call failed.")
    return response

@pytest.mark.order(1)
def test_signup_new_user_random():
    username, email, password = generate_random_user()
    signup_response = signup_user(email, username, password)
    assert signup_response.status_code == 201
    login_response = login_user(email, password)
    assert login_response.status_code == 200
    token = login_response.json().get('access_token')
    protected_response = protected_api_call(token)
    assert protected_response.status_code == 200

@pytest.mark.order(2)
def test_signup_existing_user():
    username, email, password = generate_random_user()
    first_signup_response = signup_user(email, username, password)
    assert first_signup_response.status_code == 201
    second_signup_response = signup_user(email, username, password)
    assert second_signup_response.status_code == 409

@pytest.mark.order(3)
def test_token_revocation():
    username, email, password = generate_random_user()
    signup_response = signup_user(email, username, password)
    assert signup_response.status_code == 201
    login_response = login_user(email, password)
    assert login_response.status_code == 200
    token = login_response.json().get('access_token')
    protected_response = protected_api_call(token)
    assert protected_response.status_code == 200
    logout_response = logout_user(token)
    assert logout_response.status_code == 200
    protected_response_after_logout = protected_api_call(token)
    assert protected_response_after_logout.status_code == 401

@pytest.fixture(scope="module")
def user_token():
    username, email, password = generate_random_user()
    signup_response = signup_user(email, username, password)
    assert signup_response.status_code == 201
    login_response = login_user(email, password)
    token = login_response.json().get('access_token')
    yield token
    logout_user(token)

@pytest.mark.order(4)
def test_create_and_get_preferences(user_token):
    create_url = f"{BASE_URL}/api/user/preferences"
    get_url = f"{BASE_URL}/api/user/preferences"
    headers = {'Authorization': f'Bearer {user_token}'}
    preferences = {
        "public_transport": "1",
        "bike_weight": "0",
        "walking_weight": "1",
        "driving_weight": "1"
    }
    create_response = requests.post(create_url, json=preferences, headers=headers)
    if create_response.status_code != 200:
        logger.error(create_response.text)
    assert create_response.status_code == 200
    
    get_response = requests.get(get_url, headers=headers)
    if get_response.status_code != 200:
        logger.error(get_response.text)
    assert get_response.status_code == 200
    logger.info(f"User preferences: {get_response.json()}")
    # assert get_response.json()["payload"]["public_transport"] == preferences["public_transport"]

@pytest.mark.order(5)
def test_create_and_delete_incident():
    create_url = f"{BASE_URL}/createIncident"
    incident = {
        "coordinates": [53.272262, -6.255912],
        "description": "Pytest: Test Minor crash on Highway R113 Ballinteer",
        "isJamcident": True,
        "roadClosed": True,
    }
    create_response = requests.post(create_url, json=incident)
    assert create_response.status_code == 201
    # Incident 99ca8855-db35-48cf-9fda-5b603294d4ca created successfully
    assert "Incident " in create_response.text
    assert " created successfully" in create_response.text

    incident_id = create_response.text.replace("Incident ", "").replace(" created successfully", "")
    delete_url = f"{BASE_URL}/deleteIncident/{incident_id}"
    delete_response = requests.delete(delete_url)
    assert delete_response.status_code == 200

@pytest.mark.order(1)
def test_user_profile(user_token):
    url = f"{BASE_URL}/api/user/profile"
    headers = {'Authorization': f'Bearer {user_token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        logger.info(f"Retrieved user profile successfully: {response.json()}")
    else:
        logger.error(f"Failed to retrieve user profile. Response: {response.text}")
    assert response.status_code == 200

# Coordinates data for testing
coordinates_pairs = [
    ("leapord's town to blackrock", '-6.1998406596697455,53.2555585979835', '-6.134367,53.293963'),
    ("killiney beach to airport", '-6.112460,53.254836', '-6.235733,53.425014'),
    ("rathmines to trinity", '-6.274100,53.324656', '-6.254582,53.343915')
]

@pytest.mark.parametrize("label,start,end", coordinates_pairs)
def test_routes_performance(label, start, end):
    url = f"{BASE_URL}/api/routes"
    params = {
        'startCoordinates': start,
        'endCoordinates': end
    }
    start_time = time.time()
    response = requests.get(url, params=params)
    elapsed_time = time.time() - start_time
    if response.status_code == 200 and elapsed_time < 5:
        logger.info(f"'{label}' Routes data for {start} to {end} retrieved in {elapsed_time:.2f} seconds.")
    else:
        logger.error(f"'{label}' Failed to retrieve or slow response for routes data. Response time: {elapsed_time:.2f} seconds. Response: {response.text}")
    assert response.status_code == 200
    assert elapsed_time < 5, f"Response time {elapsed_time:.2f} exceeds 5 seconds limit."

@pytest.mark.parametrize("label,start,end", coordinates_pairs)
def test_routes2_performance(label, start, end):
    url = f"{BASE_URL}/api/routes2"
    params = {
        'startCoordinates': start,
        'endCoordinates': end
    }
    start_time = time.time()
    response = requests.get(url, params=params)
    elapsed_time = time.time() - start_time
    if response.status_code == 200 and elapsed_time < 5:
        logger.info(f"'{label}' Routes2 data for {start} to {end} retrieved in {elapsed_time:.2f} seconds.")
    else:
        logger.error(f"'{label}' Failed to retrieve or slow response for routes2 data. Response time: {elapsed_time:.2f} seconds. Response: {response.text}")
    assert response.status_code == 200
    assert elapsed_time < 5, f"Response time {elapsed_time:.2f} exceeds 5 seconds limit."

if __name__ == "__main__":
    pytest.main(["-v", "--html=report.html"])
