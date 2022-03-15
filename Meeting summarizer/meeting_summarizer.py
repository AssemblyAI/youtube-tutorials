import streamlit as st
import requests
import pandas as pd
from get_results import *

if 'start_point' not in st.session_state:
    st.session_state['start_point'] = 0

def update_start(start_t):
    st.session_state['start_point'] = int(start_t/1000)

uploaded_file = st.file_uploader('Please upload a file')

if uploaded_file is not None:
    st.audio(uploaded_file, start_time=st.session_state['start_point'])
    polling_endpoint = upload_to_AssemblyAI(uploaded_file)

    status='submitted'
    while status != 'completed':
        polling_response = requests.get(polling_endpoint, headers=headers)
        status = polling_response.json()['status']

        if status == 'completed':

            #display categories
            st.subheader('Main themes')
            with st.expander('Themes'):
                categories = polling_response.json()['iab_categories_result']['summary']
                for cat in categories:
                    st.markdown("* " + cat)


            #display chapter summaries
            st.subheader('Summary notes of this meeting')
            chapters = polling_response.json()['chapters']
            chapters_df = pd.DataFrame(chapters)
            chapters_df['start_str'] = chapters_df['start'].apply(convertMillis)
            chapters_df['end_str'] = chapters_df['end'].apply(convertMillis)

            for index, row in chapters_df.iterrows():
                with st.expander(row['gist']):
                    st.write(row['summary'])
                    st.button(row['start_str'], on_click=update_start, args=(row['start'],))
