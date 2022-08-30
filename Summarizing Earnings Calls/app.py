import streamlit as st
from utils import *
import pandas as pd
from time import sleep
import json
import requests

## Set session state
if 'start_point' not in st.session_state:
    st.session_state['start_point'] = 0

def update_start(start_t):
    st.session_state['start_point'] = int(start_t / 1000)

## App explanation
st.title('Summarization of earning calls')
st.caption('With this app you can get the summary of earnings calls by providing a YouTube link to its recording.')

## Get link from user
video_url = st.text_input(label='Earnings call link', value="https://www.youtube.com/watch?v=niA_ECTcpvM&t=126s")

## Save audio locally
video_title, save_location = save_audio(video_url)

st.header(video_title)
st.audio(save_location, start_time=st.session_state['start_point'])

polling_endpoint = upload_to_AssemblyAI(save_location)

## Waiting for transcription to be done
status = 'submitted'
while True:
	polling_response = requests.get(polling_endpoint, headers=headers)
	transcript = polling_response.json()['text']
	status = polling_response.json()['status']

	if status == 'submitted' or status == 'processing':
		print('not ready yet')
		sleep(10)

	elif status == 'completed':
		print('creating transcript')

		print(json.dumps(polling_response.json(), indent=4, sort_keys=True))

		# Display summaries
		chapters = polling_response.json()['chapters']
		chapters_df = pd.DataFrame(chapters)
		chapters_df['start_str'] = chapters_df['start'].apply(convertMillis)
		chapters_df['end_str'] = chapters_df['end'].apply(convertMillis)

		st.subheader('Summary notes from this meeting')
		for index, row in chapters_df.iterrows():
			with st.expander(row['gist']):
				st.write(row['summary'])
				st.button(row['start_str'], on_click=update_start, args=(row['start'],))

		break
	else:
		print('error')
		break