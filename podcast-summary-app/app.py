import streamlit as st
import glob
import json
from podcasts import pipeline
from threading import Thread

st.title("Podcast Summaries")

json_files = glob.glob('*.json')


episode_id = st.sidebar.text_input("Episode ID")
button = st.sidebar.button("Download Episode summary")
if button and episode_id:
    st.sidebar.write("Get auto chapters...")
    #pipeline(episode_id)
    t = Thread(target=pipeline, args=(episode_id,))
    t.start()


def get_clean_summary(chapters):
    txt = ''
    for chapter in chapters:
        start_ms = chapter['start']
        seconds = int((start_ms / 1000) % 60)
        minutes = int((start_ms / (1000 * 60)) % 60)
        hours = int((start_ms / (1000 * 60 * 60)) % 24)
        if hours > 0:
            txt += f'start: {hours:02d}:{minutes:02d}:{seconds:02d}'
        else:
            txt += f'start: {minutes:02d}:{seconds:02d}'
        txt += '\n\n'
        txt += chapter['summary']
        txt += '\n\n'
    return txt


for file in json_files:
    with open(file, 'r') as f:
        data = json.load(f)

    chapter = data['chapters']
    episode_title = data['episode_title']
    thumbnail = data['thumbnail']
    podcast_title = data['podcast_title']
    audio = data['audio_url']

    with st.expander(f"{podcast_title} - {episode_title}"):
        st.image(thumbnail, width=200)
        st.markdown(f'#### {episode_title}')
        st.write(get_clean_summary(chapter))