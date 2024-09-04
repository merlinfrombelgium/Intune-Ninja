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

### Quickstart
The quickest way to set up your environment is by using GitHub Codespaces. Simply click on the green "Code" button in the repository and select "Open with Codespaces" to launch a ready-to-use development environment without any additional setup.

![alt text](res/img/codespaces.png)

<details>
<summary>Manual setup</summary>

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

</details>

## Configuration

 Make a copy of the `.env.example` file in the root directory, rename it to `.env` and add your API key for OpenAI and client ID, secret and tenant ID for Microsoft Graph API.

```text
   # Microsoft Graph API Credentials
   MS_GRAPH_CLIENT_ID=<your_client_id_here>
   MS_GRAPH_CLIENT_SECRET=<your_client_secret_here>
   MS_GRAPH_TENANT_ID=<your_tenant_id_here>

   # LLM settings
   LLM_API_KEY=<your_openai_api_key_here> # Only supports OpenAI for now
   LLM_MODEL=<your_model_here> # Suggest to use gpt-4o-mini

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
