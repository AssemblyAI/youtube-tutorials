import websockets
import asyncio
import base64
import json
import pyaudio
from twython import Twython
from configure import (
   auth_key,
   consumer_key,
   consumer_secret,
   access_token,
   access_token_secret
)

FRAMES_PER_BUFFER = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()
 
# starts recording
stream = p.open(
  format=FORMAT,
  channels=CHANNELS,
  rate=RATE,
  input=True,
  frames_per_buffer=FRAMES_PER_BUFFER
)


URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

twitter = Twython(
   consumer_key,
   consumer_secret,
   access_token,
   access_token_secret
)


async def send_receive():
  
  print(f'Connecting to url ${URL}')

  async with websockets.connect(
    URL,
    extra_headers=(("Authorization", auth_key),),
    ping_interval=5,
    ping_timeout=20
  ) as _ws:

    r = await asyncio.sleep(0.1)
    print("Receiving SessionBegins ...")

    session_begins = await _ws.recv()
    print(session_begins)
    print("Sending messages ...")
    result = ''


    async def send():
      while True:
        try:
          data = stream.read(FRAMES_PER_BUFFER)
          data = base64.b64encode(data).decode("utf-8")
          json_data = json.dumps({"audio_data":str(data)})
          r = await _ws.send(json_data)

        except websockets.exceptions.ConnectionClosedError as e:
          print(e)
          assert e.code == 4008

        except Exception as e:
          print(e)
          assert False, "Not a websocket 4008 error"

        r = await asyncio.sleep(0.01)


    async def receive():
      while True:
        try:
      result_str = await _ws.recv()
      result = json.loads(result_str)['text']

      if json.loads(result_str)['message_type']=='FinalTranscript':
      print(result)
      if result == 'Tweet.' and previous_result!='':
        twitter.update_status(status=previous_result)
        print("Tweeted: %s" % previous_result)
      previous_result = result

    except websockets.exceptions.ConnectionClosedError as e:
      print(e)
      assert e.code == 4008

    except Exception as e:
      print(e)
      assert False, "Not a websocket 4008 error"
      
  send_result, receive_result = await asyncio.gather(send(), receive())


asyncio.run(send_receive())