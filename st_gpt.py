import os
import time
import yaml
from yaml.loader import SafeLoader

import requests
import streamlit as st
import streamlit_authenticator as stauth

import gpt
from presets import presets
from utils import read_srt

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


if not login():
    st.stop()

if 'chat' not in st.session_state:
    st.session_state.chat = gpt.ChatGPT()


with st.sidebar:
    with st.expander("Settings"):
        max_time = int(st.number_input("Max generate time", value=120, min_value=1, max_value=600, step=1))
        preset_title = st.selectbox("Assisstant preset", (x for x in presets.keys())) or 'none'
        preset_text = presets.get(preset_title, '')
        if st.button("Reset"):
            st.session_state.chat = gpt.ChatGPT(settings=preset_text)

tab1, tab2 = st.tabs(["Chat", "Translate"])

with tab1:
    text = st.text_input("Input text:", value="", placeholder="Input")
    st.divider()
    if text:
        now_text = st.progress(0, text="")
        start_time = time.time()
        try:
            for line_text in st.session_state.chat.get_chat_stream(text, max_time=max_time, yield_time=0.5):
                used_time = (time.time() - start_time)
                now_text.progress(
                    min(used_time / max_time, 1.0),
                    text=f"[{used_time:.2f} sec] {line_text}",
                )
        except requests.exceptions.Timeout:
            st.error("[Request timeout]")
        except requests.exceptions.ConnectionError as e:
            st.error(f"[Connection error]{repr(e)}")
        except Exception as e:
            st.error(f"[Exception occur]{repr(e)}")

    markdown_result = "\n\n".join([f"#### {x['role'].capitalize()}:\n\n{x['content']}\n" for x in st.session_state.chat.content[::-1]])
    st.markdown(markdown_result)

with tab2:
    if preset_title != 'translate':
        st.session_state.chat = gpt.ChatGPT(settings=presets.get('translate', ''))
    srt_file = st.file_uploader("Upload SRT file", type=['srt'])
    srt_lines = srt_file.read().decode('gb18030').split('\n') if srt_file else []
    if not srt_lines:
        st.stop()
    srt_lines = read_srt(srt_lines)
    min_line_num, max_line_num = int(srt_lines[0][0]), int(srt_lines[-1][0])
    from_line = int(st.number_input("From line", value=min_line_num, min_value=min_line_num, max_value=max_line_num, step=1))
    to_line = int(st.number_input("To line", value=max_line_num, min_value=from_line, max_value=max_line_num, step=1))
    use_model = st.selectbox("Model", ('gpt-4', 'gpt-3.5-turbo'), index=0)
    with_context = st.checkbox('Use context')
    export_srt_text = ""
    if st.button("Start"):
        trans_lines = []
        for tmp_line in srt_lines:
            line_index = int(tmp_line[0])
            if line_index > to_line:
                break
            elif line_index >= from_line:
                trans_lines.append(tmp_line)
        now_text = st.progress(0, text="")
        all_start_time = time.time()
        all_used_time = []
        try:
            for index, translate_text_data in enumerate(trans_lines):
                translate_time = translate_text_data[1]
                translate_text = "\n".join(translate_text_data[2:])
                start_time = time.time()
                if not with_context:
                    st.session_state.chat = gpt.ChatGPT(settings=presets.get('translate', ''))
                used_time = None
                for line_text in st.session_state.chat.get_chat_stream(translate_text, max_time=max_time, yield_time=0.1, model=use_model):
                    used_time = (time.time() - start_time)
                    time_left_text = ""
                    if len(all_used_time) > 0:
                        average_time = sum(all_used_time) / len(all_used_time)
                        time_left = (len(trans_lines) - index) * average_time - used_time
                        time_left_text = f"[Total time left est.: {time_left:.2f} sec]"

                    now_text.progress(
                        min(used_time / max_time, 1.0),
                        text=f"{time_left_text}[{used_time:.2f} sec] {line_text}",
                    )
                    if len(st.session_state.chat.content) > 5:
                        st.session_state.chat.content.pop(1)
                if not used_time:
                    st.error(f"[Request error] {st.session_state.chat}")
                else:
                    all_used_time.append(used_time)
                    res = st.session_state.chat.content[-1]['content']
                    translate_text.replace('\n', '\n\n')
                    markdown_result = f"`{translate_text_data[0]} {translate_time}`\n\n<strong>{translate_text}</strong>\n\n{res}"
                    export_srt_text += f"{translate_text_data[0]}\n{translate_time}\n{res}\n\n"
                    st.markdown(markdown_result, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"[Exception occur] You can download exsisted srt on below.")
            st.exception(e)

        st.download_button(
            label="Download SRT",
            data=export_srt_text,
            # data=export_srt_text.encode("utf-8").decode("gb18030"),
            file_name="translate.srt",
            mime="text/plain",
        )
