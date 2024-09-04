# Copilot for Intune

## Overview
Copilot for Intune is an AI-powered tool that provides insights on Intune data using Microsoft Graph API. It allows users to interact with the AI to retrieve information and perform actions related to Intune.

## Features
- Chat with AI to get insights on Intune data.
- Call Microsoft Graph API to fetch data.
- Interpret the data and provide suggestions.
- User-friendly interface built with Streamlit.

## Requirements
- Python 3.x
- Required packages:
  - `dotenv`
  - `openai`
  - `streamlit`

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Make a copy of the `.env.example` file in the root directory, rename it to `.env` and add your API key for OpenAI and client ID, secret and tenant ID for Microsoft Graph API.
   ```
   # Microsoft Graph API Credentials
   MS_GRAPH_CLIENT_ID=your_client_id_here
   MS_GRAPH_CLIENT_SECRET=your_client_secret_here
   MS_GRAPH_TENANT_ID=your_tenant_id_here

   # Other API keys (if needed)
   OPENAI_API_KEY=your_openai_api_key_here

   # Environment settings
   DEBUG=True
   ```

## Usage
Run the application:
```bash
streamlit run main.py
```


Open your browser and navigate to `http://localhost:8501` to access the application.

## Contributing
Feel free to submit issues or pull requests. Contributions are welcome!

## License
This project is licensed under the MIT License.