import re
import string
import pyaudio
import websocket
import json
import threading
import time 
import tweepy
from urllib.parse import urlencode
from datetime import datetime
from configure import (
   auth_key,
   consumer_key,
   consumer_secret,
   access_token,
   access_token_secret
)

# --- Configuration ---

CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "format_turns": True,  # request formatted final turns
}

API_ENDPOINT_BASE_URL = "wss://streaming.assemblyai.com/v3/ws"
API_ENDPOINT = f"{API_ENDPOINT_BASE_URL}?{urlencode(CONNECTION_PARAMS)}"

# Audio Configuration
FRAMES_PER_BUFFER = 800  # 50ms at 16kHz
SAMPLE_RATE = CONNECTION_PARAMS["sample_rate"]
CHANNELS = 1
FORMAT = pyaudio.paInt16

audio = None
stream = None
ws_app = None
audio_thread = None
stop_event = threading.Event()


# For tweeting logic
TWEET_COMMANDS = {"tweet", "tweet that"}
MAX_TWEET_CHARS = 280

previous_final_text = ""
previous_lock = threading.Lock()
last_tweeted_text = ""
tweet_lock = threading.Lock()

# X client
x_client = None

# ===================== Helpers =====================
def make_x_client():
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        wait_on_rate_limit=True,
    )
    return client


def tweet_text(client: tweepy.Client, text: str):
    txt = (text or "").strip()
    if not txt:
        print("Refusing to tweet empty text.")
        return

    if len(txt) > MAX_TWEET_CHARS:
        txt = txt[: MAX_TWEET_CHARS - 1] + "…"

    try:
        print(f"Posting tweet: {repr(txt)}")
        resp = client.create_tweet(text=txt)
        tweet_id = getattr(resp, "data", {}).get("id", None)
        if tweet_id:
            print(f"Tweeted (id={tweet_id}): {txt}")
        else:
            print(f"Tweeted: {txt}")
    except Exception as e:
        print("Tweet failed:", repr(e))


def try_command_and_extract_payload(text: str):
    """
    Returns (is_command, payload_after_command_or_None).

    Matches:
      - 'tweet' / 'tweet that' (+ optional punctuation)
      - 'tweet that <payload>' (tweets <payload> directly)
    """
    if not text:
        return (False, None)

    s = text.strip()

    # Pure command with optional punctuation, case-insensitive
    if re.fullmatch(r'(?i)\s*tweet(\s+that)?\s*[\.\!\?\'"\u2019\u201D]*\s*', s):
        return (True, None)

    # Command + payload (payload ends before trailing punctuation)
    m = re.match(r'(?i)^\s*tweet(\s+that)?\s+(.+?)\s*[\.\!\?\'"\u2019\u201D]*\s*$', s)
    if m:
        payload = m.group(2).strip()
        if payload and payload.strip(string.punctuation + " "):
            return (True, payload)

    return (False, None)


# ===================== WebSocket Handlers =====================
def on_open(ws):
    """Called when the WebSocket connection is established."""
    print("WebSocket connection opened.")
    print(f"Connected to: {API_ENDPOINT}")

    def stream_audio():
        global stream
        print("Starting audio streaming...")
        while not stop_event.is_set():
            try:
                audio_data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)

                # send raw PCM 16-bit mono as binary frame
                ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                print(f"Error streaming audio: {e}")
                break
        print("Audio streaming stopped.")

    global audio_thread
    audio_thread = threading.Thread(target=stream_audio, daemon=True)
    audio_thread.start()


def on_message(ws, message):
    global previous_final_text, x_client, last_tweeted_text

    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return  # ignore non-JSON frames

    msg_type = data.get('type')

    if msg_type == "Begin":
        session_id = data.get('id')
        expires_at = data.get('expires_at')
        if expires_at is not None:
            print(f"\nSession began: ID={session_id}, ExpiresAt={datetime.fromtimestamp(expires_at)}")
        else:
            print(f"\nSession began: ID={session_id}")

    elif msg_type == "Turn":
        transcript = data.get('transcript', '')
        formatted = data.get('turn_is_formatted', False)

        if formatted:
            # Clear previous line then print final
            print('\r' + ' ' * 80 + '\r', end='')
            final_text = (transcript or "").strip()
            print(final_text)
            print("FINAL TEXT (repr):", repr(final_text))

            is_cmd, payload = try_command_and_extract_payload(final_text)
            if is_cmd:
                print("Command detected.")
                if payload:
                    # Same-turn payload: tweet what follows 'tweet that'
                    with tweet_lock:
                        if payload != last_tweeted_text:
                            if x_client is None:
                                print("X client not initialized; cannot tweet.")
                            else:
                                tweet_text(x_client, payload)
                                last_tweeted_text = payload
                        else:
                            print("Skipping duplicate tweet (same content).")
                else:
                    # Previous-turn behavior
                    with previous_lock:
                        to_post = previous_final_text
                    if to_post:
                        with tweet_lock:
                            if to_post != last_tweeted_text:
                                if x_client is None:
                                    print("X client not initialized; cannot tweet.")
                                else:
                                    tweet_text(x_client, to_post)
                                    last_tweeted_text = to_post
                            else:
                                print("Skipping duplicate tweet (same content).")
                    else:
                        print("Nothing to tweet yet (no previous finalized utterance).")
            else:
                # Update previous finalized utterance
                with previous_lock:
                    previous_final_text = final_text
        else:
            # Interim partials: overwrite the same console line
            print(f"\r{transcript}", end='')

    elif msg_type == "Termination":
        audio_duration = data.get('audio_duration_seconds', 0)
        session_duration = data.get('session_duration_seconds', 0)
        print(f"\nSession Terminated: Audio Duration={audio_duration}s, Session Duration={session_duration}s")

    elif msg_type == "error":
        print("AssemblyAI error:", data)


def on_error(ws, error):
    print(f"\nWebSocket Error: {error}")
    stop_event.set()


def on_close(ws, close_status_code, close_msg):
    print(f"\nWebSocket Disconnected: Status={close_status_code}, Msg={close_msg}")


    global stream, audio
    stop_event.set()

    if stream:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
        stream = None
    if audio:
        audio.terminate()
        audio = None

    if audio_thread and audio_thread.is_alive():
        audio_thread.join(timeout=1.0)


# ===================== Main =====================
def run():
    global audio, stream, ws_app, x_client

    # Initialize X client
    x_client = make_x_client()

    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    try:
        stream = audio.open(
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            channels=CHANNELS,
            format=FORMAT,
            rate=SAMPLE_RATE,
        )
        print("Microphone stream opened successfully.")
        print("Speak into your microphone. Press Ctrl+C to stop.")
        print("Say 'tweet' or 'tweet that' to post the PREVIOUS finalized utterance to X,")
        print("or say 'tweet that <text>' to post <text> directly.")
    except Exception as e:
        print(f"Error opening microphone stream: {e}")
        if audio:
            audio.terminate()
        return

    # Create WebSocketApp
    ws_app = websocket.WebSocketApp(
        API_ENDPOINT,
        header={"Authorization": auth_key},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    # Run WebSocketApp in a separate thread
    ws_thread = threading.Thread(target=ws_app.run_forever, daemon=True)
    ws_thread.start()

    try:
        while ws_thread.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nCtrl+C received. Stopping...")
        stop_event.set()

        # Ask server to terminate gracefully
        if ws_app and ws_app.sock and ws_app.sock.connected:
            try:
                terminate_message = {"type": "Terminate"}
                print(f"Sending termination message: {json.dumps(terminate_message)}")
                ws_app.send(json.dumps(terminate_message))
                time.sleep(5)
            except Exception as e:
                print(f"Error sending termination message: {e}")

        if ws_app:
            ws_app.close()

        ws_thread.join(timeout=2.0)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        stop_event.set()
        if ws_app:
            ws_app.close()
        ws_thread.join(timeout=2.0)

    finally:
        if stream and stream.is_active():
            stream.stop_stream()
        if stream:
            stream.close()
        if audio:
            audio.terminate()
        print("Cleanup complete. Exiting.")


if __name__ == "__main__":
    run()