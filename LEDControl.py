import openai
import json
import logging
import board
import neopixel
import time
import keyboard
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading


logging.basicConfig(level=logging.INFO)


LED_PIN = board.D18  
NUM_LEDS = 300  
ORDER = neopixel.GRB  

pixels = neopixel.NeoPixel(LED_PIN, NUM_LEDS, brightness=0.5, auto_write=False, pixel_order=ORDER)

scope = "user-library-read user-read-playback-state user-modify-playback-state"
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=scope)


def get_gpt_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use GPT-4 model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates JSON commands to control LED lights. Ensure that all your responses are formatted as valid JSON. The JSON should contain a 'pattern' key with an array of objects, each containing 'r', 'g', 'b', and 'duration' keys. Each duration should be at least 3000 ms. Ensure that the colors are accurate and use RGB values."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip() 
    except Exception as e:
        logging.error(f"Error getting GPT response: {e}")
        return "Error getting GPT response."
    
def gamma_correction(r, g, b):
    r = int((r/255.0) ** 1.9 * 255.0)
    g = int((g/255.0) ** 1.9 * 255.0)
    b = int((b/255.0) ** 1.9 * 255.0)
    return (r, g, b)

def gamma_decode(r, g, b):
    r = int((r/255.0) ** (1/1.9) * 255.0)
    g = int((g/255.0) ** (1/1.9) * 255.0)
    b = int((b/255.0) ** (1/1.9) * 255.0)
    return (r, g, b)

def control_led(command):
    try:
        led_command = json.loads(command)
        if "pattern" in led_command:
            apply_led_pattern(led_command["pattern"])
            return "LED pattern set."
        else:
            return "Invalid command format."
    except json.JSONDecodeError:
        logging.error("Invalid JSON command.")
        return "Invalid JSON command."
    
def fade_between_colors(color1, color2, duration, steps=300, brightness = 1.0):
    step_duration = duration / steps
    for step in range(steps):
        if keyboard.is_pressed('space'):
            return  
        intermediate_color = (
            int((color1[0] + (color2[0] - color1[0]) * step / steps) * brightness),
            int((color1[1] + (color2[1] - color1[1]) * step / steps) * brightness),
            int((color1[2] + (color2[2] - color1[2]) * step / steps) * brightness)
        )
        intermediate_color = gamma_correction(*intermediate_color)
        for i in range(NUM_LEDS):
            pixels[i] = intermediate_color
        pixels.show()
        time.sleep(step_duration / 1000)
    
def apply_led_pattern(pattern):
    try:
        while True:
            for i in range(len(pattern)):
                if keyboard.is_pressed('space'):
                    return  # Exit the function if space is pressed
                current_color = gamma_correction(pattern[i]["r"], pattern[i]["g"], pattern[i]["b"])
                next_color = gamma_correction(pattern[(i + 1) % len(pattern)]["r"], pattern[(i + 1) % len(pattern)]["g"], pattern[(i + 1) % len(pattern)]["b"])
                duration = pattern[i]["duration"]
                fade_between_colors(current_color, next_color, duration)
    except Exception as e:
        logging.error(f"Error applying LED pattern: {e}")

def get_spotify_analysis(track_uri):
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    analysis = sp.audio_analysis(track_uri)
    return analysis

def generate_led_pattern_from_analysis(analysis, start_color, end_color):
    segments = analysis['segments']
    pattern = []
    base_brightness = 1.0

    for segment in segments:
        duration = segment['duration'] * 1000  # convert to milliseconds
        loudness = segment['loudness_max']
        brightness = max(0, min(1, (loudness + 60) / 60))  # scale loudness to a 0-1 range
        color1 = (int(start_color[0] * brightness), int(start_color[1] * brightness), int(start_color[2] * brightness))
        color2 = (int(end_color[0] * brightness), int(end_color[1] * brightness), int(end_color[2] * brightness))
        pattern.append({"r": color1[0], "g": color1[1], "b": color1[2], "duration": duration})
        pattern.append({"r": color2[0], "g": color2[1], "b": color2[2], "duration": duration})

    return {"mode": "pattern", "pattern": pattern}

def find_segment_for_beat(segments, beat_start):
    for segment in segments:
        if segment['start'] <= beat_start < segment['start'] + segment['duration']:
            return segment
    return segments[-1]

def sync_leds_with_spotify(start_color, end_color):
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    current_track = sp.current_playback()
    if current_track and current_track['is_playing']:
        track_uri = current_track['item']['uri']
        analysis = get_spotify_analysis(track_uri)
        beats = analysis['beats']
        segments = analysis['segments']
        beat_index = 0
        while current_track and current_track['is_playing']:
            current_position = current_track['progress_ms'] / 1000.0
            while beat_index < len(beats) and beats[beat_index]['start'] <= current_position:
                beat = beats[beat_index]
                segment = find_segment_for_beat(segments, beat['start'])
                duration = beat['duration'] * 1000  # convert to milliseconds
                tempo = analysis['track']['tempo']
                intensity = max(0, min(1, (segment['loudness_max'] + 60) / 60)) * tempo  # Combine loudness and tempo to determine intensity
                if intensity > 125:  # Adjust this threshold to match your definition of "intense"
                    fade_between_colors(start_color, end_color, duration, steps=50)
                else:
                    brightness = max(0, min(1, (segment['loudness_max'] + 60) / 60))  # scale loudness to a 0-1 range
                    color = gamma_correction(int(end_color[0]), int(end_color[1]), int(end_color[2]))
                    for i in range(NUM_LEDS):
                        pixels[i] = color
                    pixels.show()
                    time.sleep(duration/1000)
                beat_index += 1
            current_track = sp.current_playback()
            if current_track and not current_track['is_playing']:
                sync_leds_with_spotify(start_color, end_color)
    else:
        sync_leds_with_spotify(start_color, end_color)


def main():
    user_input = input("Describe the LED pattern you want: ")
    if "sync with spotify" in user_input.lower():
        start_color = tuple(map(int, input("Enter the start color (R, G, B): ").split(',')))
        end_color = tuple(map(int, input("Enter the end color (R, G, B): ").split(',')))
        threading.Thread(target=sync_leds_with_spotify, args=(start_color, end_color)).start()
    else:
        gpt_response = get_gpt_response(user_input)
        print(f"GPT-4 Response: {gpt_response}")
        led_response = control_led(gpt_response)
        print(f"LED Response: {led_response}")

if __name__ == '__main__':
    main()
