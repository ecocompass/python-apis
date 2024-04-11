import unittest
import json
from app import app 
class TestSignupEndpoint(unittest.TestCase):

    def setUp(self):
        # Setup a test client for the Flask app
        self.app = app.test_client()
        self.app.testing = True

    def test_signup_success(self):
        # Test successful signup
        test_data = {
            "username": "xyz",
            "password": "password123",
            "email": "john.doe@example.com"
        }
        response = self.app.post('/api/auth/signup', data=json.dumps(test_data), content_type='application/json')
        self.assertEqual(response.status_code, 201)

    

class TestLoginEndpoint(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_login_success(self):
        
        test_data = {
            "email": "user@example.com",
            "password": "password123"
        }
        response = self.app.post('/api/auth/login', data=json.dumps(test_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
    @staticmethod
    def get_access_token_for_test_user():
        test_app = app.test_client()
        test_app.testing = True
        test_data = {
            "email": "john.doe@example.com",
            "password": "password123"
        }
        response = test_app.post('/api/auth/login', data=json.dumps(test_data), content_type='application/json')
        return response.json.get('access_token')

class TestProtectedEndpoints(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_protected_route(self):
        access_token = TestLoginEndpoint().get_access_token_for_test_user()
        response = self.app.get("/protected", headers={"Authorization": f"Bearer {access_token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"hello": "world"})

    def test_user_profile(self):
        access_token = TestLoginEndpoint().get_access_token_for_test_user()
        response = self.app.get("/api/user/profile", headers={"Authorization": f"Bearer {access_token}"})
        self.assertEqual(response.status_code, 200)
        # Adjust the following assertions based on the actual structure of your user profile response
        self.assertIn("first_name", response.json)
        self.assertIn("last_name", response.json)
        self.assertIn("email", response.json)
        self.assertIn("created_at", response.json)
    

if __name__ == '__main__':
    unittest.main()
