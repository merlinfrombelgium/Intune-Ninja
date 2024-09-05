import streamlit as st

def write_debug(message):
    if 'debug_messages' not in st.session_state:
        st.session_state.debug_messages = []
    
    st.session_state.debug_messages.append(message)
    
    if 'debug_container' not in st.session_state:
        st.session_state.debug_container = st.sidebar.empty()
    
    with st.session_state.debug_container.container():
        with st.expander("Debug Info", expanded=False, icon="🔎"):
            st.text_area("", value="\n".join(st.session_state.debug_messages), height=400)

