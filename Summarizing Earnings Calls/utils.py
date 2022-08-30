import streamlit as st
from pytube import YouTube
import os
import requests
from configure import auth_key

## AssemblyAI endpoints and headers
transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
upload_endpoint = "https://api.assemblyai.com/v2/upload"

headers = {
   "authorization": auth_key,
   "content-type": "application/json"
}

@st.cache()
def save_audio(url):
    yt = YouTube(url)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download()
    base, ext = os.path.splitext(out_file)
    file_name = base + '.mp3'
    os.rename(out_file, file_name)
    print(yt.title + " has been successfully downloaded.")
    print(file_name)
    return yt.title, file_name


## Upload audio to AssemblyAI
@st.cache()
def upload_to_AssemblyAI(save_location):
	CHUNK_SIZE = 5242880

	def read_file(filename):
		with open(filename, 'rb') as _file:
			while True:
				print("chunk uploaded")
				data = _file.read(CHUNK_SIZE)
				if not data:
					break
				yield data

	upload_response = requests.post(
		upload_endpoint,
		headers=headers, data=read_file(save_location)
	)
	print(upload_response.json())

	audio_url = upload_response.json()['upload_url']
	print('Uploaded to', audio_url)


	## Start transcription job of audio file
	data = {
		'audio_url': audio_url,
		'auto_chapters': 'True',
	}

	transcript_response = requests.post(transcript_endpoint, json=data, headers=headers)
	print(transcript_response)

	transcript_id = transcript_response.json()['id']
	polling_endpoint = transcript_endpoint + "/" + transcript_id

	print("Transcribing at", polling_endpoint)
	return polling_endpoint


def convertMillis(start_ms):
	seconds = int((start_ms / 1000) % 60)
	minutes = int((start_ms / (1000 * 60)) % 60)
	hours = int((start_ms / (1000 * 60 * 60)) % 24)
	btn_txt = ''
	if hours > 0:
		btn_txt += f'{hours:02d}:{minutes:02d}:{seconds:02d}'
	else:
		btn_txt += f'{minutes:02d}:{seconds:02d}'
	return btn_txt