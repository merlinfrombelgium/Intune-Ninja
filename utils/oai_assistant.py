from openai import OpenAI
import os, sys
import streamlit as st
import yaml

def get_user_secret(key):
    if 'user_secrets' not in st.session_state:
        st.error("User secrets not initialized. Please refresh the page.")
        return None
    return st.session_state.user_secrets.get(key)

class Assistant:
    def __init__(self, client):
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        self.client = client
        self.assistant_name = "Intune Copilot"
        self.assistant_instructions = open(os.sep.join(["prompts", "assistant_instructions.md"]), "r").read().strip()
        self.assistant_model = get_user_secret('LLM_MODEL')
        self.assistant_vector_store_name = "Intune Copilot Vector Store"
        self.uploads_path = os.sep.join(["files", "graph_api_docs"])
        self.assistant = None
        self.assistant_vector_store_id = None

    def create_assistant(self):
        st.info("Creating new Intune Copilot assistant...")
        assistant = self.client.beta.assistants.create(
            name=self.assistant_name,
            instructions=self.assistant_instructions,
            model=self.assistant_model,
            tools=[{"type": "file_search"}]
        )
        st.success(f"Assistant created successfully. ID: {assistant.id}")
        return assistant

    def create_vector_store(self):
        st.info("Creating new vector store...")
        try:
            vector_store = self.client.beta.vector_stores.create(
                name=self.assistant_vector_store_name,
            )
            self.assistant_vector_store_id = vector_store.id
            st.success(f"Vector store created successfully. ID: {self.assistant_vector_store_id}")
            return vector_store.id
        except Exception as e:
            st.error(f"An error occurred while creating the vector store: {str(e)}")
            st.warning("Proceeding without a vector store. Some functionality may be limited.")
            return None

    def upload_files(self):
        st.info("Uploading files to vector store...")
        with open(os.path.join(os.curdir, "utils", "file_types.yml"), 'r') as file:
            file_types = yaml.safe_load(file)

        supported_extensions = list(file_types.keys())

        files_to_upload = [os.path.join(self.uploads_path, f) for f in os.listdir(self.uploads_path) if f.endswith(tuple(supported_extensions))]
        file_streams = [open(file_path, "rb") for file_path in files_to_upload]
        
        file_batch = self.client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=self.assistant_vector_store_id,
            files=file_streams
        )

        st.success(f"File upload status: {file_batch.status}")
        st.info(f"File upload counts: {str(file_batch.file_counts)}")

    def retrieve_assistant(self):
        try:
            if self.assistant is not None:
                return self.assistant

            assistants_list = self.client.beta.assistants.list()
            self.assistant = next((assistant for assistant in assistants_list if assistant.name == self.assistant_name), None)
            
            if self.assistant is None:
                st.info("Creating new Intune Copilot assistant...")
                self.assistant = self.create_assistant()
                self.assistant_vector_store_id = self.create_vector_store()
                self.upload_files()
            else:
                st.info(f"Intune Copilot assistant found. (id: {self.assistant.id})")
                
                # Check if the assistant has a file_search tool
                has_file_search = any(
                    (isinstance(tool, dict) and tool.get('type') == 'file_search') or
                    (hasattr(tool, 'type') and tool.type == 'file_search')
                    for tool in self.assistant.tools
                )
                if not has_file_search:
                    st.warning("Assistant doesn't have a file_search tool. Updating tools...")
                    self.assistant = self.client.beta.assistants.update(
                        assistant_id=self.assistant.id,
                        tools=[{"type": "file_search"}]
                    )
                    st.success("File search tool added to the assistant.")
                else:
                    st.info("Assistant already has a file_search tool.")
                
                # Check if we have a vector store ID stored
                if not hasattr(self, 'assistant_vector_store_id'):
                    self.assistant_vector_store_id = self.create_vector_store()
                    self.upload_files()
                else:
                    st.info(f"Using existing vector store. ID: {self.assistant_vector_store_id}")
            
            return self.assistant

        except Exception as e:
            st.error(f"An error occurred while retrieving the assistant: {str(e)}")
            raise