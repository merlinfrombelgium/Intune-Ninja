import sys
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from utils.llm import chat, assistant, get_embedding, print_history
import json

# Add the parent directory to the system path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestLLMFunctions(unittest.TestCase):

    def setUp(self):
        # Call chat to initialize history
        with patch('builtins.input', side_effect=['Hello', 'exit']):
            chat()  # Call the chat function to set up history

    @patch('builtins.open', new_callable=mock_open, read_data='{"role": "system", "content": "This is a system prompt."}')
    @patch('utils.llm.OpenAI')
    def test_chat(self, mock_openai, mock_file):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content='Hello!'))])
        ]

        with patch('builtins.input', side_effect=['Hello', 'exit']):
            chat()  # Call the chat function

        mock_client.chat.completions.create.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{"role": "system", "content": "You are a helpful assistant."}')
    @patch('utils.llm.OpenAI')
    def test_assistant(self, mock_openai, mock_file):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the response to include the system prompt in the messages
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='Response'))]
        )

        # Call the assistant function with a specific instruction
        response = assistant("What is the weather?", "You are a helpful assistant.")
        
        # Assert that the response is as expected
        self.assertEqual(response, 'Response')
        
        # Assert that the chat completion was called once
        mock_client.chat.completions.create.assert_called_once_with(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the weather?"}
            ],
            temperature=0.7,
        )

    @patch('builtins.open', new_callable=mock_open, read_data='{"role": "system", "content": "This is a system prompt."}')
    @patch('utils.llm.OpenAI')
    def test_get_embedding(self, mock_openai, mock_file):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value = MagicMock(data=[MagicMock(embedding=[0.1, 0.2, 0.3])])

        embedding = get_embedding("Sample text")
        
        self.assertEqual(embedding, [0.1, 0.2, 0.3])
        mock_client.embeddings.create.assert_called_once_with(input=["Sample text"], model="nomic-ai/nomic-embed-text-v1.5-GGUF")

    @patch('builtins.print')
    @patch('json.dumps')
    def test_print_history(self, mock_json, mock_print):
        # Sample history to be printed
        sample_history = [
            {"role": "system", "content": "You are an AI assistant specialized in interpreting Microsoft Graph API responses and explaining them in the context of Microsoft Intune management. Your task is to analyze the API response and provide a clear, concise explanation of what the data means and how it relates to the user's original query about Intune management."},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hello! How can I assist you with interpreting Microsoft Graph API responses related to Microsoft Intune management today? Do you have a specific question or API response you'd like me to help with?"},
            {"role": "user", "content": "tell me a rancid joke"},
            {"role": "assistant", "content": "Here's one that's a bit of a groaner:\n\nWhy did the fish go to the party?\n\nBecause he heard it was a \"reel\" good time! (get it?)\n\nNow, if you're ready to get back to serious business, I'd be happy to help you with your Microsoft Graph API response or Intune management question!"}
        ]

        # Mock the json.dumps to return the sample history
        mock_json.return_value = json.dumps(sample_history, indent=2)
        
        print_history()
        
        expected_output = (
            "\033[90m\n-------------------- History dump --------------------\n\n"
            + mock_json.return_value + "\n\n"
            + "-------------------------------------------------------\n\033[0m"
        )
        
        mock_print.assert_called_once_with(expected_output)

if __name__ == '__main__':
    unittest.main()