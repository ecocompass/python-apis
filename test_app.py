import unittest
from unittest.mock import patch, MagicMock
from app import app

class TestSignup(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    @patch('app.databaseconn')
    def test_signup_success(self, mock_databaseconn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_databaseconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        response = self.client.post('/api/auth/signup', json={'username': 'test_user', 'password': 'test_password'})
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['message'], 'User signed up')

    @patch('app.databaseconn')
    def test_signup_user_exists(self, mock_databaseconn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('test_user',)
        mock_databaseconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        response = self.client.post('/api/auth/signup', json={'username': 'test_user', 'password': 'test_password'})
        
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json['message'], 'User already exists')

    @patch('app.databaseconn')
    def test_signup_database_down(self, mock_databaseconn):
        mock_databaseconn.side_effect = Exception('Database connection error')

        response = self.client.post('/api/auth/signup', json={'username': 'test_user', 'password': 'test_password'})
        
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json['message'], 'Database Down')

    @patch('app.databaseconn')
    def test_signup_database_error(self, mock_databaseconn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception('Database error')
        mock_databaseconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        response = self.client.post('/api/auth/signup', json={'username': 'test_user', 'password': 'test_password'})
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['message'], 'Unable to sign up')

if __name__ == '__main__':
    unittest.main()
