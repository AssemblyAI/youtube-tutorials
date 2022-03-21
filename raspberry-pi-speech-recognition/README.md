# Raspberry Pi Speech Recognition

## Raspberry Pi Setup

```console
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install python3
```

## Install VS Code

```console
$ sudo apt install code
$ code .
```

Then:
- Install Python Extension
- Preferences: Configure Runtime Arguments --> Set "disable-hardware-acceleration": true

## Install PyAudio

```console
$ sudo apt install libportaudio0 libportaudio2 libportaudiocpp0 portaudio19-dev flac
$ python3 -m venv venv
$ . venv bin activate
$ pip install pyaudio requests websockets
```

## Configure USB micophone

```console
$ lsusb
$ arecord -l
$ cat /proc/asound/cards
$ cat /proc/asound/modules
```

Set the default card in:
```console
$ sudo nano /usr/share/alsa/alsa.conf
```

E.g. for card 2:
```console
defaults.ctl.card 2
defaults.pcm.card 2
```

Save the file and reboot:
```console
$ sudo reboot
```

## Test sound recording

```console
$ arecord -d 5 -r 48000 test.wav
$ aplay test.wav
```

## Test PyAudio code

```python
import pyaudio
p = pyaudio.PyAudio()

for i in range(p.get_device_count()):
    print(p.get_device_info_by_index(i).get('name'))
```

## Real-Time Speech Recognition

Run [sr.py](sr.py):

```console
$ python sr.py
```
