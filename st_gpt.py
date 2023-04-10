import os
import time
import yaml
from yaml.loader import SafeLoader

import requests
import streamlit as st
import streamlit_authenticator as stauth

import gpt
from presets import presets

def login():
    file_path = 'credentials.yaml'
    if not os.path.isfile(file_path):
        open(file_path, 'w').write("")
        print(f"Please put the credentials in '{file_path}' file")
        exit(1)
    with open(file_path) as file:
        config = yaml.load(file, Loader=SafeLoader)
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )
    name, authentication_status, username = authenticator.login('Login', 'main')
    return authentication_status

st.set_page_config(
    page_title="GPT Test Page",
)

st.session_state.chat = gpt.ChatGPT()

if not login():
    st.stop()

with st.expander("Settings"):
    max_time = int(st.number_input("Max generate time", value=120, min_value=1, max_value=600, step=1))
    preset_title = st.selectbox("Assisstant preset", (x for x in presets.keys())) or 'none'
    preset_text = presets.get(preset_title, '')
    if st.button("Reset"):
        st.session_state.chat = gpt.ChatGPT(settings=preset_text)

text = st.text_input("Input", value="", placeholder="Input", label_visibility="hidden")
if text:
    now_text = st.progress(0, text="")
    start_time = time.time()
    try:
        for line_text in st.session_state.chat.get_chat_stream(text, max_time=max_time, yield_time=0.5):
            used_time = (time.time() - start_time)
            now_text.progress(
                used_time / max_time,
                text=f"[{used_time:.2f} sec] {line_text}",
            )
    except requests.exceptions.Timeout:
        st.error("[Request timeout]")
    except requests.exceptions.ConnectionError as e:
        st.error(f"[Connection error]{repr(e)}")
    except Exception as e:
        st.error(f"[Exception occur]{repr(e)}")

markdown_result = "\n\n".join([f"*{x['role']}*\n```plain\n{x['content']}\n```" for x in st.session_state.chat.content[::-1]])
st.markdown(markdown_result)
