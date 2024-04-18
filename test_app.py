import datetime
import unittest
import json
import random
import requests
import string
from pprint import pprint


access_token = {"current": None}


class TestUserFlow(unittest.TestCase):
    def setUp(self):
        self.base_url = "http://prod.ecocompass.live"
        # Use the same user details as you would in Postman for consistency
        u1, u2, e = "".join(random.choice(string.ascii_letters) for _ in range(random.randint(3, 6))), "".join(random.choice(string.ascii_letters) for _ in range(random.randint(3, 6))), "".join(random.choice(string.ascii_letters) for _ in range(random.randint(3, 6)))
        
        self.test_user = {
            "username": f"{u1} {u2}",  # Make sure this username adheres to your API's format requirements
            "email": f"{e}@example.com",
            "password": "password123"
        }
    
    def test_1_signup_and_login(self):
        print("Test user details")
        pprint(self.test_user)

        # Signup
        print("SignUp user")
        signup_url = f"{self.base_url}/api/auth/signup"
        signup_response = requests.post(signup_url, json=self.test_user)
        self.assertEqual(signup_response.status_code, 201, "Signup failed: {}".format(signup_response.json()))
        self.assertIn("User signed up", signup_response.json()['message'], "Signup message not as expected")

        # Login
        print("Login user")
        login_url = f"{self.base_url}/api/auth/login"
        login_data = {
            "email": self.test_user["email"],
            "password": self.test_user["password"]
        }
        
        login_response = requests.post(login_url, json=login_data)
        access_token["current"] = login_response.json()['access_token']  # Save the access token
        self.assertEqual(login_response.status_code, 200, "Login failed: {}".format(login_response.json()))
        self.assertIn("Login successful", login_response.json()['message'], "Login message not as expected")
        self.assertTrue('access_token' in login_response.json(), "Access token not found in login response")
        print(access_token["current"])

    def test_2_user_profile(self):
        """Test retrieving the user profile using the JWT token obtained from login."""
        if access_token["current"]:
            profile_url = f"{self.base_url}/api/user/profile"
            headers = {'Authorization': f'Bearer {access_token["current"]}'}
            profile_response = requests.get(profile_url, headers=headers)
            self.assertEqual(profile_response.status_code, 200, "Failed to access user profile.")
            profile_data = profile_response.json()
            self.assertIn("first_name", profile_data, "First name not found in profile data")
            self.assertIn("email", profile_data, "Email not found in profile data")
        else:
            self.fail("Access token not obtained from login.")

    def test_3_user_preferences(self):
        """Test retrieving the user preferences using the JWT token obtained from login."""
        if access_token["current"]:
            preferences_url = f"{self.base_url}/api/user/preferences"
            headers = {'Authorization': f'Bearer {access_token["current"]}'}
            preferences_response = requests.get(preferences_url, headers=headers)
            self.assertEqual(preferences_response.status_code, 200, "Failed to access user preferences.")
            preferences_data = preferences_response.json()
            self.assertTrue('payload' in preferences_data, "Preferences data not found in the response")
        else:
            self.fail("Access token not obtained from login.")
         
         
    def test_4_saved_locations_add(self):
        """Test adding or updating a user's saved location."""
        if access_token["current"]:
            locations_url = f"{self.base_url}/api/user/savedlocations"
            headers = {'Authorization': f'Bearer {access_token["current"]}'}
            location_data = {
                "latitude": "35.6895",
                "longitude": "139.6917",
                "location_name": "Tokyo Tower"
            }
            response = requests.post(locations_url, headers=headers, json=location_data)
            self.assertEqual(response.status_code, 200, "Failed to add or update saved locations.")
            self.assertIn("User saved locations updated or added", response.json()['message'], "Incorrect response message for saved locations")   
           
    def test_5_delete_saved_location(self):
        """Test deleting a user's saved location."""
        if access_token["current"]:
            delete_url = f"{self.base_url}/api/user/savedlocations"
            headers = {'Authorization': f'Bearer {access_token["current"]}'}
            location_data = {
                "location_name": "Tokyo Tower"  # Specify the location name that exists and is to be deleted
            }
            response = requests.delete(delete_url, headers=headers, json=location_data)
            self.assertEqual(response.status_code, 200, "Failed to delete saved location.")
            self.assertIn("Location deleted successfully", response.json()['message'], "Incorrect response message for deleting location")
        else:
            self.fail("Access token not obtained from login.")
            
                      
    def test_6_user_trips_get(self):
        """Test retrieving user trips using the JWT token obtained from login."""
        trips_url = f"{self.base_url}/api/user/trips"
        headers = {'Authorization': f'Bearer {access_token["current"]}'}
        trips_response = requests.get(trips_url, headers=headers)
        if trips_response.status_code == 404:
            self.assertIn("No trips found", trips_response.json()['message'], "No trips found message not as expected")
        else:
            self.assertEqual(trips_response.status_code, 200, "Failed to access user trips.")
            trips_data = trips_response.json()
            self.assertTrue('saved_locations' in trips_data, "Trips data not found in response")


    def test_7_user_routes_add_and_get(self):
        """Test adding and retrieving user routes using the JWT token."""
        routes_url = f"{self.base_url}/api/user/routes"
        headers = {'Authorization': f'Bearer {access_token["current"]}'}
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

    # def test_8_user_goals_operations(self):
    #     """Test adding, retrieving, and deleting user goals using the JWT token."""
    #     goals_url = f"{self.base_url}/api/user/goals"
    #     headers = {'Authorization': f'Bearer {access_token["current"]}'}
    #     # Add a goal
    #     goal_data = {
    #         "type": "Walking",
    #         "target": 10000,
    #         "created_at": int(datetime.datetime.now().timestamp()),
    #         "expiry": int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp())
    #     }
    #     add_goal_response = requests.post(goals_url, headers=headers, json=[goal_data])
    #     self.assertEqual(add_goal_response.status_code, 200, "Failed to add goal.")

    #     # Get goals
    #     get_goals_response = requests.get(goals_url, headers=headers)
    #     self.assertEqual(get_goals_response.status_code, 200, "Failed to retrieve goals.")
    #     goals_data = get_goals_response.json()
    #     self.assertIn("payload", goals_data, "Goals data not found in response")

    #     # Delete a goal
    #     delete_goal_response = requests.delete(goals_url, headers=headers, json={"type": "Walking"})
    #     self.assertEqual(delete_goal_response.status_code, 200, "Failed to delete goal.")


if __name__ == '__main__':
    unittest.main()
