import streamlit as st
from streamlit_player import st_player
import json

st.title("Learn")

url = 'https://youtu.be/rmVRLeJRkl4'

file_highlights = 'o6faqyp448-35de-44c6-b1ff-1e6799699b5b_highlights.json'
file_chapters = 'o6faqyp448-35de-44c6-b1ff-1e6799699b5b_chapters.json'

placeholder = st.empty()
with placeholder.container():
    st_player(url, playing=False, muted=True)
    
mode = st.sidebar.selectbox("Summary Mode", ("Highlights", "Chapters"))

def get_btn_text(start_ms):
    seconds = int((start_ms / 1000) % 60)
    minutes = int((start_ms / (1000 * 60)) % 60)
    hours = int((start_ms / (1000 * 60 * 60)) % 24)
    btn_txt = ''
    if hours > 0:
        btn_txt += f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        btn_txt += f'{minutes:02d}:{seconds:02d}'
    return btn_txt


def add_btn(start_ms, key):
    start_s = start_ms / 1000
    if st.button(get_btn_text(start_ms), key):
        url_time = url + '&t=' + str(start_s) + 's'
        with placeholder.container():
            st_player(url_time, playing=True, muted=False)
        

if mode == "Highlights":
    with open(file_highlights, 'r') as f:
        data = json.load(f)
    results = data['results']
    
    cols = st.columns(3)
    n_buttons = 0
    for res_idx, res in enumerate(results):
        text = res['text']
        timestamps = res['timestamps']
        col_idx = res_idx % 3
        with cols[col_idx]:
            st.write(text)
            for t in timestamps:
                start_ms = t['start']
                add_btn(start_ms, n_buttons)
                n_buttons += 1
else:
    with open(file_chapters, 'r') as f:
        chapters = json.load(f)
    for chapter in chapters:
        start_ms = chapter['start']
        add_btn(start_ms, None)
        txt = chapter['summary']
        st.write(txt)