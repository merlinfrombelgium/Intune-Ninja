import os
import streamlit as st
import requests
from requests.exceptions import HTTPError

def get_user_secret(key):
    if 'user_secrets' not in st.session_state:
        st.session_state.user_secrets = {}
        st.write("Initializing user_secrets...")
        for secret_key in ['MS_GRAPH_CLIENT_ID', 'MS_GRAPH_CLIENT_SECRET', 'MS_GRAPH_TENANT_ID']:
            if secret_key in st.secrets:
                st.session_state.user_secrets[secret_key] = st.secrets[secret_key]
                st.write(f"Loaded {secret_key} from st.secrets")
            else:
                st.warning(f"Secret {secret_key} not found in st.secrets")
    
    value = st.session_state.user_secrets.get(key)
    if value is None:
        st.warning(f"Secret {key} not found in user_secrets")
    else:
        st.write(f"Retrieved {key} from user_secrets")
    return value

class MSGraphAPI:
    def __init__(self):
        st.write("Initializing MSGraphAPI...")
        self.client_id = get_user_secret('MS_GRAPH_CLIENT_ID')
        self.client_secret = get_user_secret('MS_GRAPH_CLIENT_SECRET')
        self.tenant_id = get_user_secret('MS_GRAPH_TENANT_ID')
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            st.error("One or more required secrets are missing. Please check your configuration.")
            return

        self.base_url = "https://graph.microsoft.com/v1.0"
        st.write("Attempting to get access token...")
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
        try:
            st.write(f"Sending request to {url}")
            response = requests.post(url, headers=headers, data=body)
            st.write(f"Response status code: {response.status_code}")
            response.raise_for_status()
            token = response.json().get("access_token")
            st.write("Successfully obtained access token")
            return token
        except HTTPError as e:
            st.error(f"HTTP Error: {e}")
            if e.response.status_code == 400:
                st.error("Error 400: Bad Request. Please check your MS_GRAPH_TENANT_ID and MS_GRAPH_CLIENT_ID in the user secrets.")
            elif e.response.status_code == 401:
                st.error("Error 401: Unauthorized. Please check your MS_GRAPH_CLIENT_SECRET in the user secrets.")
            raise ValueError(f"HTTP Error: {e}")
        except Exception as e:
            st.error(f"Error initializing Microsoft Graph client: {str(e)}. Please check your Microsoft Graph credentials.")
            raise ValueError(f"Error initializing Microsoft Graph client: {str(e)}. Please check your Microsoft Graph credentials.")

    def call_api(self, endpoint, method='GET', data=None):
        url = f"{endpoint}" if endpoint.startswith(self.base_url) else f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        try:
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

            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            if e.response.status_code == 400:
                raise ValueError("Error 400: Bad Request. Please check your request parameters and try again.\n\nFull Error: " + str(e))
            raise ValueError(f"HTTP Error: {e}")
        except Exception as e:
            raise ValueError(f"Error calling Microsoft Graph API: {str(e)}")

# Example usage:
# try:
#     graph_api = MSGraphAPI()
#     response = graph_api.call_api('me')
#     print(json.dumps(response, indent=2))
# except ValueError as e:
#     st.error(str(e))