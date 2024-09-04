import os
from dotenv import load_dotenv
import requests

class MSGraphAPI:
    def __init__(self):
        load_dotenv()  # Load environment variables from .env file
        self.client_id = os.getenv('MS_GRAPH_CLIENT_ID')
        self.client_secret = os.getenv('MS_GRAPH_CLIENT_SECRET')
        self.tenant_id = os.getenv('MS_GRAPH_TENANT_ID')
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.token = self.get_access_token()

    def get_access_token(self):
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json().get("access_token")

    def call_api(self, endpoint, method='GET', data=None):
        url = f"{endpoint}" if endpoint.startswith(self.base_url) else f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError("Unsupported HTTP method")

        response.raise_for_status()  # Raise an error for bad responses
        return response.json()

# Example usage:
# graph_api = MSGraphAPI()
# response = graph_api.call_api('me')
# print(json.dumps(response, indent=2))