from utils.ms_graph_api import MSGraphAPI
import json
import os
from openai import OpenAI

def call_graph_api(api_url):
    ms_graph_api = MSGraphAPI()
    try:
        api_response = ms_graph_api.call_api(api_url)
        return json.dumps(api_response, indent=2)
    except Exception as e:
        return f"Error calling API: {str(e)}"

def get_graph_api_url(message, system_prompt):
    client = OpenAI(api_key=os.getenv('LLM_API_KEY'))
    messages = [
        {"role": "system", "content": system_prompt["content"]},
        {"role": "user", "content": message}
    ]

    try:
        response = client.chat.completions.create(
            model=os.getenv('LLM_MODEL'),
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "GraphAPIURL",
                    "description": "A URL for the Microsoft Graph API.",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "base_url": {"type": "string"},
                            "endpoint": {"type": "string"},
                            "parameters": {
                                "type": ["array", "null"],
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["base_url", "endpoint", "parameters"]
                    }
                }
            }
        )

        content = response.choices[0].message.content
        content_dict = json.loads(content)

        if content_dict['parameters']:
            parameters = [param.lstrip('?') for param in content_dict['parameters']]
            url = f"{content_dict['base_url']}{content_dict['endpoint']}?{'&'.join(parameters)}"
        else:
            url = f"{content_dict['base_url']}{content_dict['endpoint']}"

        return url
    except Exception as e:
        print(e)
        return None

# Remove the generate_and_interpret_url function as it's not being used