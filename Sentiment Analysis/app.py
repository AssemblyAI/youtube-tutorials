import streamlit as st
from save_audio import save_audio
from configure import auth_key
import pandas as pd
from time import sleep
import urllib.request
import plotly.express as px
import plotly.graph_objects as go
from urllib.request import urlopen
from bs4 import BeautifulSoup
import json
import requests



## AssemblyAI endpoints and headers
transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
upload_endpoint = 'https://api.assemblyai.com/v2/upload'

headers_auth_only = {'authorization': auth_key}
headers = {
   "authorization": auth_key,
   "content-type": "application/json"
}



## App explanation
st.title('Sentiment analysis of earning calls')
st.caption('With this app you can analyse the sentiment of earnings calls by providing a YouTube link to its recording.')
st.subheader('Submit a video link or choose one of the pre-determined ones to analyse.')



# Get link from user
video_url = st.text_input(label='Earnings call link', value="https://www.youtube.com/watch?v=UA-ISgpgGsk")



# Save audio locally
save_location = save_audio(video_url)


## Upload audio to AssemblyAI
CHUNK_SIZE = 5242880

def read_file(filename):
	with open(filename, 'rb') as _file:
		while True:
			data = _file.read(CHUNK_SIZE)
			if not data:
				break
			yield data

upload_response = requests.post(
	upload_endpoint,
	headers=headers_auth_only, data=read_file(save_location)
)

audio_url = upload_response.json()['upload_url']
print('Uploaded to', audio_url)



## Start transcription job of audio file
data = {
	'audio_url': audio_url,
	'sentiment_analysis': 'True',
}

transcript_response = requests.post(transcript_endpoint, json=data, headers=headers)
print(transcript_response)

transcript_id = transcript_response.json()['id']
polling_endpoint = transcript_endpoint + "/" + transcript_id

print("Transcribing at", polling_endpoint)



## Waiting for transcription to be done
status = 'submitted'
while status != 'completed':
	print('not ready yet')
	sleep(1)
	polling_response = requests.get(polling_endpoint, headers=headers)
	transcript = polling_response.json()['text']
	status = polling_response.json()['status']
	

# Display transcript
print('creating transcript')
st.sidebar.header('Transcript of the earnings call')
st.sidebar.markdown(transcript)


print(json.dumps(polling_response.json(), indent=4, sort_keys=True))



## Sentiment analysis response	
sar = polling_response.json()['sentiment_analysis_results']

## Save to a dataframe for ease of visualization
sen_df = pd.DataFrame(sar)
print(sen_df.head())



## Get the title of this video
with urlopen(video_url) as url:
    s = url.read()
    soup = BeautifulSoup(s)
    title = soup.title.string

st.header(title)



## Visualizations
st.markdown("### Number of sentences: " + str(sen_df.shape[0]))


grouped = pd.DataFrame(sen_df['sentiment'].value_counts()).reset_index()
grouped.columns = ['sentiment','count']
print(grouped)


col1, col2 = st.columns(2)


# Display number of positive, negative and neutral sentiments
fig = px.bar(grouped, x='sentiment', y='count', color='sentiment', color_discrete_map={"NEGATIVE":"firebrick","NEUTRAL":"navajowhite","POSITIVE":"darkgreen"})

fig.update_layout(
	showlegend=False,
    autosize=False,
    width=400,
    height=500,
    margin=dict(
        l=50,
        r=50,
        b=50,
        t=50,
        pad=4
    )
)

col1.plotly_chart(fig)


## Display sentiment score
pos_perc = grouped[grouped['sentiment']=='POSITIVE']['count'].iloc[0]*100/sen_df.shape[0]
neg_perc = grouped[grouped['sentiment']=='NEGATIVE']['count'].iloc[0]*100/sen_df.shape[0]
neu_perc = grouped[grouped['sentiment']=='NEUTRAL']['count'].iloc[0]*100/sen_df.shape[0]

sentiment_score = neu_perc+pos_perc-neg_perc

fig = go.Figure()

fig.add_trace(go.Indicator(
    mode = "delta",
    value = sentiment_score,
    domain = {'row': 1, 'column': 1}))

fig.update_layout(
	template = {'data' : {'indicator': [{
        'title': {'text': "Sentiment score"},
        'mode' : "number+delta+gauge",
        'delta' : {'reference': 50}}]
                         }},
    autosize=False,
    width=400,
    height=500,
    margin=dict(
        l=20,
        r=50,
        b=50,
        pad=4
    )
)

col2.plotly_chart(fig)

## Display negative sentence locations
fig = px.scatter(sar, y='sentiment', color='sentiment', size='confidence', hover_data=['text'], color_discrete_map={"NEGATIVE":"firebrick","NEUTRAL":"navajowhite","POSITIVE":"darkgreen"})


fig.update_layout(
	showlegend=False,
    autosize=False,
    width=800,
    height=300,
    margin=dict(
        l=50,
        r=50,
        b=50,
        t=50,
        pad=4
    )
)

st.plotly_chart(fig)






