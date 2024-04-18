import requests
import pytest
import random
import string

# Base URL of the API
BASE_URL = "http://prod.ecocompass.live:80"


def generate_random_user():
    # Generates a username consisting of two random alphabetic sequences separated by a space
    part_one = ''.join(random.choice(string.ascii_letters) for _ in range(random.randint(3, 6)))
    part_two = ''.join(random.choice(string.ascii_letters) for _ in range(random.randint(3, 6)))
    username = f"{part_one.capitalize()} {part_two.capitalize()}"
    email = f"{part_one.lower()}{part_two.lower()}@example.com"
    password = f"{part_one.capitalize()}{part_two.capitalize()}"
    return username, email, password


def signup_user(email, username, password):
    url = f"{BASE_URL}/api/auth/signup"
    response = requests.post(url, json={
        "email": email,
        "username": username,
        "password": password
    })
    return response


def login_user(email, password):
    url = f"{BASE_URL}/api/auth/login"
    response = requests.post(url, json={
        "email": email,
        "password": password
    })
    return response


def logout_user(token):
    url = f"{BASE_URL}/api/auth/logout"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.delete(url, headers=headers)
    return response


def protected_api_call(token):
    url = f"{BASE_URL}/protected"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    return response


@pytest.mark.order(1)
def test_signup_new_user_random():
    username, email, password = generate_random_user()
    # Sign up a new, randomly generated user
    signup_response = signup_user(email, username, password)
    assert signup_response.status_code == 201

    # Log in the newly created random user
    login_response = login_user(email, password)
    assert login_response.status_code == 200
    token = login_response.json().get('access_token')

    # Make a protected API call with the new user's token
    protected_response = protected_api_call(token)
    assert protected_response.status_code == 200


@pytest.mark.order(2)
def test_signup_existing_user():
    username, email, password = generate_random_user()
    # First, sign up the new user
    first_signup_response = signup_user(email, username, password)
    assert first_signup_response.status_code == 201

    # Try to sign up the same user again
    second_signup_response = signup_user(email, username, password)
    assert second_signup_response.status_code == 409  # Assuming 409 Conflict is the response for an existing user


@pytest.mark.order(3)
def test_token_revocation():
    username, email, password = generate_random_user()
    # Sign up new user
    signup_response = signup_user(email, username, password)
    assert signup_response.status_code == 201

    # Log in new user
    login_response = login_user(email, password)
    assert login_response.status_code == 200
    token = login_response.json().get('access_token')

    # Make a protected API call
    protected_response = protected_api_call(token)
    assert protected_response.status_code == 200

    # Logout user
    logout_response = logout_user(token)
    assert logout_response.status_code == 200

    # Try to use the same token after logout
    protected_response_after_logout = protected_api_call(token)
    assert protected_response_after_logout.status_code == 401


if __name__ == "__main__":
    pytest.main(["-v", "--html=report.html"])
