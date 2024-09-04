from openai import OpenAI
import os, sys
import streamlit as st

class Assistant:
    def __init__(self, client):
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        self.client = client
        self.assistant_name = "Intune Copilot"
        self.assistant_instructions = open(os.sep.join(["prompts", "assistant_instructions.md"]), "r").read().strip()
        self.assistant_model = st.secrets['LLM_MODEL']
        self.assistant_vector_store_name = "Intune Copilot"
        self.uploads_path = os.sep.join(["files", "graph_api_docs"])

    def create_assistant(self):
        self.client.beta.assistants.create(
            name=self.assistant_name,
            instructions=self.assistant_instructions,
            model=self.assistant_model,
            tools=[{"type": "file_search"}],
        )

    def create_vector_store(self):
        self.client.beta.vector_stores.create(
            name=self.assistant_vector_store_name,
        )

    def retrieve_assistant(self):
        assistants_list = self.client.beta.assistants.list()
        self.assistant = [assistant for assistant in assistants_list if assistant.name == self.assistant_name][0]
        if self.assistant is None:
            #print("Intune Copilot not found in list of assistants, creating new one")
            self.assistant = self.create_assistant()
        #else:
            #print("Intune Copilot assistant found. (id: " + self.assistant.id + ")")
        if self.assistant.tool_resources.file_search.vector_store_ids is None:
            print("Intune Copilot vector store not found, creating new one")
            self.assistant = self.create_vector_store()
        else:
            self.assistant_vector_store_id = self.assistant.tool_resources.file_search.vector_store_ids[0]
        
        return self.assistant

    def upload_files(self):
        import yaml

        # Load supported file types from the YAML file
        with open(os.path.join(os.curdir, "utils", "file_types.yml"), 'r') as file:
            file_types = yaml.safe_load(file)

        supported_extensions = list(file_types.keys())

        files_to_upload = [os.path.join(self.uploads_path, f) for f in os.listdir(self.uploads_path) if f.endswith(tuple(supported_extensions))]
        file_streams = [open(file_path, "rb") for file_path in files_to_upload]
        file_batch = self.client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=self.assistant_vector_store_id,
            files=file_streams
        )

        print("File upload status: " + file_batch.status)
        print("File upload counts: " + str(file_batch.file_counts))

# Example usage:
# assistant = Assistant(client)
# assistant.upload_files()