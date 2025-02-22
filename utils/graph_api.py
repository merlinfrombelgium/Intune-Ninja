import streamlit as st
import requests
import json
from requests.exceptions import HTTPError
from utils.ai_chat import get_user_secret, update_client_status
from utils.write_debug import write_debug

global client

class MSGraphAPI:
    def __init__(self):
        write_debug(":clock1: Calling MS Graph API...")
        self.client_id = get_user_secret('MS_GRAPH_CLIENT_ID')
        self.client_secret = get_user_secret('MS_GRAPH_CLIENT_SECRET')
        self.tenant_id = get_user_secret('MS_GRAPH_TENANT_ID')
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            st.error(":warning: One or more required secrets are missing. Please check your configuration.")
            return

        self.base_url = "https://graph.microsoft.com/"
        self.version = any(version for version in ['v1.0', 'beta'])
        if 'graph_token' not in st.session_state:
            write_debug(":clock130: Attempting to get access token...")
            self.token = self.get_access_token()
            st.session_state.graph_token = self.token
        else:
            write_debug(":clock130: Using existing access token...")
            self.token = st.session_state.graph_token

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
            write_debug(f":satellite: Sending request to {url}")
            response = requests.post(url, headers=headers, data=body)
            write_debug(f":satellite: Response status code: {response.status_code}")
            response.raise_for_status()
            token = response.json().get("access_token")
            write_debug(":white_check_mark: Successfully obtained access token")
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

    def call_api(self, request, method='GET', data=None):
        url = f"{request}" if request.startswith(self.base_url) else f"{self.base_url}/{request}"
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

def call_graph_api(api_url):
    ms_graph_api = MSGraphAPI()
    write_debug(f":satellite: Calling API: {api_url}")
    try:
        api_response = ms_graph_api.call_api(api_url)
    except Exception as e:
        write_debug(f":warning: Error calling API: {str(e)}")
        return f"Error calling API: {str(e)}"
    
    # Check if there's more data available
    next_link = api_response.get('@odata.nextLink')
    
    result = {
        'data': api_response.get('value', []),
        'next_link': next_link
    }
    
    write_debug(f":white_check_mark: API call successful")
    return json.dumps(result, indent=2)

def get_next_batch(next_link):
    ms_graph_api = MSGraphAPI()
    try:
        write_debug(f":satellite: Calling next batch: {next_link}")
        api_response = ms_graph_api.call_api(next_link)
        
        # Check if there's more data available
        new_next_link = api_response.get('@odata.nextLink')
        
        result = {
            'data': api_response.get('value', []),
            'next_link': new_next_link
        }
        
        write_debug(f":white_check_mark: Next batch retrieved successfully")
        return json.dumps(result, indent=2)
    except Exception as e:
        write_debug(f":warning: Error retrieving next batch: {str(e)}")
        return f"Error retrieving next batch: {str(e)}"

def get_graph_api_url(client, query, system_prompt):
    try:
        messages = [
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": f"Generate a valid Microsoft Graph API URL for the following query: {query}"}
        ]
        
        response = client.chat.completions.create(
            model=st.session_state.LLM_MODEL,
            messages=messages,
            temperature=0.2,
            reasoning_effort="low",
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        generated_url = response.choices[0].message.content.strip()
        write_debug(f"Generated URL: {generated_url}")
        
        return {"url": generated_url, "json": parse_graph_api_url(generated_url)}
    except Exception as e:
        st.error(f"Error in get_graph_api_url: {str(e)}")
        write_debug(f"Error in get_graph_api_url: {str(e)}")
        return None

def parse_graph_api_url(url):
    from urllib.parse import urlparse, parse_qs
    
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    json_representation = {
        "base_url": f"{parsed_url.scheme}://{parsed_url.netloc}",
        "version": parsed_url.path.split('/')[1],
        "endpoint": '/'.join(parsed_url.path.split('/')[2:]),
        "parameters": [f"{k}={v[0]}" for k, v in query_params.items()]
    }
    
    return json_representation

def get_access_token():
    tenant_id = st.session_state.user_secrets['Graph proxy TENANT ID']
    client_id = st.session_state.user_secrets['Graph proxy CLIENT ID']
    client_secret = st.session_state.user_secrets['Graph proxy CLIENT SECRET']

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    try:
        write_debug(f":satellite: Sending request to {url}")
        response = requests.post(url, headers=headers, data=body)
        write_debug(f":satellite: Response status code: {response.status_code}")
        response.raise_for_status()
        token = response.json().get("access_token")
        write_debug(":white_check_mark: Successfully obtained access token")
        return token
    except HTTPError as e:
        st.error(f"HTTP Error: {e}")
        if e.response.status_code == 400:
            st.error("Error 400: Bad Request. Please check your Graph proxy TENANT ID and Graph proxy CLIENT ID in the user secrets.")
        elif e.response.status_code == 401:
            st.error("Error 401: Unauthorized. Please check your Graph proxy CLIENT SECRET in the user secrets.")
        raise ValueError(f"HTTP Error: {e}")
    except Exception as e:
        st.error(f"Error initializing Microsoft Graph client: {str(e)}. Please check your Microsoft Graph credentials.")
        raise ValueError(f"Error initializing Microsoft Graph client: {str(e)}. Please check your Microsoft Graph credentials.")