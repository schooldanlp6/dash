import subprocess
import json
import requests
from vosk import Model, KaldiRecognizer, SetLogLevel
from time import sleep
import pyttsx3
import os

# Constants for speech commands
reactioname = 'hey dash'  # Command to activate voice assistant
reactionnamecancel = 'stop'  # Command to deactivate
quitvoice = 'ending'  # Command to quit the program

# Path to the Vosk model
smpl_rte = 16000  # Sample rate for the audio input
danmodel6_path = "vosk-model-small-en-us-0.15"  # Path to the Vosk model
SetLogLevel(0)  # Disable Vosk's internal logging for cleaner output

# Initialize Vosk model
danmodel6 = Model(danmodel6_path)
voicerec = KaldiRecognizer(danmodel6, smpl_rte)

# Initialize pyttsx3 for text-to-speech (only if TTS is enabled)
TTS_ENABLED = False  # Set this to False to disable TTS

if TTS_ENABLED:
    engine = pyttsx3.init()  # Only initialize TTS engine if TTS is enabled

# API URL for Ollama
Ollama_API_URL = "http://localhost:11434/api/generate"

# Function to send text to Ollama API and get a response
def query_ollama(prompt):
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama",  # Make sure the model is correctly referenced here
        "prompt": prompt,
    }

    full_response = ""  # To store the aggregated response
    try:
        response = requests.post(Ollama_API_URL, json=data, headers=headers, stream=True)
        if response.status_code != 200:
            return "Error connecting to Ollama."

        for chunk in response.iter_lines():
            if chunk:
                try:
                    chunk_data = json.loads(chunk)
                    full_response += chunk_data.get("response", "")
                    if chunk_data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

        return full_response.strip()

    except requests.exceptions.RequestException as e:
        return f"Error querying Ollama: {e}"
    except json.JSONDecodeError as e:
        return "Error parsing the response from Ollama."

# Start the subprocess for capturing audio input from the default microphone
def start_microphone_process():
    return subprocess.Popen(
        ["ffmpeg", "-f", "pulse", "-i", "default", "-ar", str(smpl_rte), "-ac", "1", "-f", "s16le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

# Function to mute or unmute the microphone (only when TTS is enabled)
def mute_microphone(mute=True):
    if TTS_ENABLED:  # Only mute/unmute if TTS is enabled
        if mute:
            os.system("pactl set-source-mute @DEFAULT_SOURCE@ 1")  # Mute microphone
        else:
            os.system("pactl set-source-mute @DEFAULT_SOURCE@ 0")  # Unmute microphone

# Main loop for voice assistant
process = start_microphone_process()
print("Listening for 'Hey Dash'. To stop, press CTRL+C.")

isinheydashmode = False  # Initially not in listening mode
while True:
    input_data = process.stdout.read(6000)  # Read 6000 bytes at a time

    if len(input_data) == 0:
        continue  # Skip empty packets

    if voicerec.AcceptWaveform(input_data):
        textout = json.loads(voicerec.Result())
        recognized_text = textout['text']
        print(f"Recognized: {recognized_text}")

        # Detect the 'Hey Dash' command to start listening mode
        if recognized_text == reactioname and not isinheydashmode:
            print("Detected 'Hey Dash'. Entering listening mode.")
            isinheydashmode = True

        # Command to stop listening mode
        elif recognized_text == reactionnamecancel:
            print("Detected 'Stop'. Exiting listening mode.")
            isinheydashmode = False
        # Command to quit the program
        elif recognized_text == quitvoice:
            print("Detected 'Ending'. Exiting the program.")
            break

        # If in listening mode, handle the TTS and unmute logic
        if isinheydashmode:
            # Only mute the microphone before TTS starts if TTS is enabled
            if TTS_ENABLED and recognized_text.strip():
                print("Muting microphone before TTS.")
                mute_microphone(mute=True)

            # Query Ollama API if there's valid input
            if recognized_text.strip():  # Avoid sending empty input to Ollama
                ai_response = query_ollama(recognized_text)
                print(f"Ollama Response: {ai_response}")

                # Only speak the response if TTS is enabled
                if TTS_ENABLED:
                    print("Speaking response using TTS.")
                    engine.say(ai_response)
                    engine.runAndWait()

            else:
                print("No valid input detected. Skipping TTS.")

            # Unmute microphone immediately after TTS finishes
            if TTS_ENABLED:
                print("Unmuting microphone after TTS.")
                mute_microphone(mute=False)
