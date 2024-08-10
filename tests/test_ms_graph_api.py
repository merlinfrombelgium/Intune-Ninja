import os
import unittest
from unittest.mock import patch, MagicMock
from utils.ms_graph_api import MSGraphAPI  # Updated import path

class TestMSGraphAPI(unittest.TestCase):

    def setUp(self):
        self.api = MSGraphAPI()  # Create a single instance for all tests

    @patch('utils.ms_graph_api.requests.post')  # Updated path for mocking
    def test_get_access_token(self, mock_post):
        # Mock the response from the token endpoint
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "mock_access_token"}
        mock_post.return_value = mock_response

        token = self.api.get_access_token()  # Use the instance created in setUp

        self.assertEqual(token, "mock_access_token")
        mock_post.assert_called_once()

    @patch('utils.ms_graph_api.requests.get')  # Updated path for mocking
    def test_call_api_get(self, mock_post):
        # Mock the response for a GET request
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": "mock_data"}
        mock_post.return_value = mock_response

        self.api.token = "mock_access_token"  # Set a mock token
        response = self.api.call_api('me')  # Use the instance created in setUp

        self.assertEqual(response, {"value": "mock_data"})
        mock_post.assert_called_once_with(
            f"https://graph.microsoft.com/v1.0/me",
            headers={
                "Authorization": "Bearer mock_access_token",
                "Content-Type": "application/json"
            }
        )

    @patch('utils.ms_graph_api.requests.post')  # Updated path for mocking
    def test_call_api_post(self, mock_get):
        # Mock the response for a POST request
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}
        mock_get.return_value = mock_response

        self.api.token = "mock_access_token"  # Set a mock token
        response = self.api.call_api('me', method='POST', data={"key": "value"})  # Use the instance created in setUp

        self.assertEqual(response, {"result": "success"})
        mock_get.assert_called_once_with(
            f"https://graph.microsoft.com/v1.0/me",
            headers={
                "Authorization": "Bearer mock_access_token",
                "Content-Type": "application/json"
            },
            json={"key": "value"}
        )

if __name__ == '__main__':
    unittest.main()