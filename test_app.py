import datetime
import unittest
import json
import requests


class TestUserFlow(unittest.TestCase):
    def setUp(self):
        self.base_url = "http://prod.ecocompass.live"
        # Use the same user details as you would in Postman for consistency
        self.test_user = {
            "username": "prhtgh1diqiue7 jiob",  # Make sure this username adheres to your API's format requirements
            "email": "h30@example.com",
            "password": "password123"
        }
        self.access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcxMzE4NTU1OSwianRpIjoiMzEzMWRlN2UtM2E0Yi00NDQ1LTkyNTEtYmE0MjBlOTQ2MWE5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6eyJlbWFpbCI6ImhpNkBleGFtcGxlLmNvbSIsInVzZXJJRCI6NjV9LCJuYmYiOjE3MTMxODU1NTksImNzcmYiOiI1OGFlYjMyNi0zMDJjLTRlZWEtOTQxNC05MThkNmMxZjllZjIiLCJleHAiOjE3MTMxODkxNTl9.ssYPrzfIkIwYVcpI8nN5ZgYTp_5aVkRP5BN5ja70lf4" 

    def test_signup_and_log9in(self):
        # Signup
        signup_url = f"{self.base_url}/api/auth/signup"
        signup_response = requests.post(signup_url, json=self.test_user)
        self.assertEqual(signup_response.status_code, 201, "Signup failed: {}".format(signup_response.json()))
        self.assertIn("User signed up", signup_response.json()['message'], "Signup message not as expected")

        # Login
        login_url = f"{self.base_url}/api/auth/login"
        login_data = {
            "email": self.test_user["email"],
            "password": self.test_user["password"]
        }
        
        login_response = requests.post(login_url, json=login_data)
        self.access_token = login_response.json()['access_token']  # Save the access token
        self.assertEqual(login_response.status_code, 200, "Login failed: {}".format(login_response.json()))
        self.assertIn("Login successful", login_response.json()['message'], "Login message not as expected")
        self.assertTrue('access_token' in login_response.json(), "Access token not found in login response")
        print(self.access_token)

    def test_user_profile(self):
        print(self.access_token)
        """Test retrieving the user profile using the JWT token obtained from login."""
        if self.access_token:
            profile_url = f"{self.base_url}/api/user/profile"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            profile_response = requests.get(profile_url, headers=headers)
            self.assertEqual(profile_response.status_code, 200, "Failed to access user profile.")
            profile_data = profile_response.json()
            self.assertIn("first_name", profile_data, "First name not found in profile data")
            self.assertIn("email", profile_data, "Email not found in profile data")
        else:
            self.fail("Access token not obtained from login.")

    def test_user_preferences(self):
        """Test retrieving the user preferences using the JWT token obtained from login."""
        if self.access_token:
            preferences_url = f"{self.base_url}/api/user/preferences"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            preferences_response = requests.get(preferences_url, headers=headers)
            self.assertEqual(preferences_response.status_code, 200, "Failed to access user preferences.")
            preferences_data = preferences_response.json()
            self.assertTrue('payload' in preferences_data, "Preferences data not found in the response")
        else:
            self.fail("Access token not obtained from login.")
         
         
    def test_saved_locations_add(self):
        """Test adding or updating a user's saved location."""
        if self.access_token:
            locations_url = f"{self.base_url}/api/user/savedlocations"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            location_data = {
                "latitude": "35.6895",
                "longitude": "139.6917",
                "location_name": "Tokyo Tower"
            }
            response = requests.post(locations_url, headers=headers, json=location_data)
            self.assertEqual(response.status_code, 200, "Failed to add or update saved locations.")
            self.assertIn("User saved locations updated or added", response.json()['message'], "Incorrect response message for saved locations")   
           
    def test_delete_saved_location(self):
        """Test deleting a user's saved location."""
        if self.access_token:
            delete_url = f"{self.base_url}/api/user/savedlocations"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            location_data = {
                "location_name": "Tokyo Tower"  # Specify the location name that exists and is to be deleted
            }
            response = requests.delete(delete_url, headers=headers, json=location_data)
            self.assertEqual(response.status_code, 200, "Failed to delete saved location.")
            self.assertIn("Location deleted successfully", response.json()['message'], "Incorrect response message for deleting location")
        else:
            self.fail("Access token not obtained from login.")
            
                      
    def test_user_trips_get(self):
        """Test retrieving user trips using the JWT token obtained from login."""
        trips_url = f"{self.base_url}/api/user/trips"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        trips_response = requests.get(trips_url, headers=headers)
        if trips_response.status_code == 404:
            self.assertIn("No trips found", trips_response.json()['message'], "No trips found message not as expected")
        else:
            self.assertEqual(trips_response.status_code, 200, "Failed to access user trips.")
            trips_data = trips_response.json()
            self.assertTrue('saved_locations' in trips_data, "Trips data not found in response")


    def test_user_routes_add_and_get(self):
        """Test adding and retrieving user routes using the JWT token."""
        routes_url = f"{self.base_url}/api/user/routes"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        # Add a route
        route_data = {
            "route": "Route Details",
            "route_name": "Home to Work"
        }
        add_response = requests.post(routes_url, headers=headers, json=route_data)
        self.assertEqual(add_response.status_code, 200, "Failed to add route.")

        # Get routes
        get_response = requests.get(routes_url, headers=headers)
        self.assertEqual(get_response.status_code, 200, "Failed to retrieve routes.")
        routes_data = get_response.json()
        self.assertIn("payload", routes_data, "Routes data not found in response")

    def test_user_goals_operations(self):
        """Test adding, retrieving, and deleting user goals using the JWT token."""
        goals_url = f"{self.base_url}/api/user/goals"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        # Add a goal
        goal_data = {
            "type": "Walking",
            "target": 10000,
            "created_at": int(datetime.datetime.now().timestamp()),
            "expiry": int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp())
        }
        add_goal_response = requests.post(goals_url, headers=headers, json=[goal_data])
        self.assertEqual(add_goal_response.status_code, 200, "Failed to add goal.")

       

if __name__ == '__main__':
    unittest.main()
