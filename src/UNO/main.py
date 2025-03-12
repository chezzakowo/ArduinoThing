import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import serial
import unicodedata

# Set up Spotify API with proper scope
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="",
    client_secret="",
    redirect_uri="http://localhost:8888/callback",
    scope="user-read-playback-state user-read-currently-playing"
))

# Set up serial communication with Arduino
arduino = serial.Serial('COM4', 9600, timeout=1)

# Function to get current song info
def get_current_song():
    current_playback = sp.current_playback()
    if current_playback:
        is_playing = current_playback['is_playing']
        if is_playing:
            song_name = current_playback['item']['name']
            song_duration_ms = current_playback['item']['duration_ms']
            progress_ms = current_playback['progress_ms']
            return song_name, song_duration_ms, progress_ms, is_playing
        else:  # Music is paused
            song_name = current_playback['item']['name']
            progress_ms = current_playback['progress_ms']
            song_duration_ms = current_playback['item']['duration_ms']
            return song_name, song_duration_ms, progress_ms, is_playing
    return None, 0, 0, False

# Function to convert special characters in song names to non-special characters
def remove_special_characters(text):
    # Normalize the text and remove diacritics (accents)
    normalized_text = unicodedata.normalize('NFD', text)
    return ''.join([c for c in normalized_text if unicodedata.category(c) != 'Mn'])

# Function to scroll the song name on the LCD
def scroll_text(arduino, text):
    max_length = 16  # assuming LCD is 16x2
    text = remove_special_characters(text)  # Convert special characters to non-special ones
    
    # If text is shorter than max length, display it fully
    if len(text) <= max_length:
        arduino.write(f"lcd 1 {text}\n".encode())
        return

    # Scroll back and forth
    for i in range(len(text) - max_length + 1):
        arduino.write(f"lcd 1 {text[i:i+max_length]}\n".encode())
        time.sleep(0.3)
    
    for i in range(len(text) - max_length + 1, 0, -1):
        arduino.write(f"lcd 1 {text[i:i+max_length]}\n".encode())
        time.sleep(0.3)

# Function to display progress bar on the LCD (Line 2 format: Time Played [-----] Time Remaining)
def display_progress_bar(arduino, progress_ms, song_duration_ms, is_playing, song_name):
    progress = int((progress_ms / song_duration_ms) * 5)
    current_time = time.strftime('%M:%S', time.gmtime(progress_ms / 1000))
    end_time = time.strftime('%M:%S', time.gmtime(song_duration_ms / 1000))
    progress_bar = "      " + "[" + "#" * progress + " " * (5 - progress) + "]"
    
    if is_playing:
        arduino.write("lcd 1                  \n".encode())
        song_name_normalized = remove_special_characters(song_name)  # Normalize song name for LCD
        arduino.write(f"lcd 1 {song_name_normalized}\n".encode())  # Display normalized name
        print(f"Đang phát bài: {song_name_normalized}")  # Print normalized song name in console
        arduino.write(f"lcd 2 {current_time} - {end_time}\n".encode())
        print(f"{current_time} - {end_time}")
    else:
        paused_time = time.strftime('%M:%S', time.gmtime(progress_ms / 1000))
        arduino.write("lcd 1                  \n".encode())
        arduino.write(f"lcd 1 Dang tam dung!\n".encode())
        arduino.write(f"lcd 2 {paused_time} - {end_time}\n".encode())

# Main loop to continuously update the LCD
previous_song = ""
while True:
    song_name, song_duration_ms, progress_ms, is_playing = get_current_song()

    if song_name:
        # Check if the song has changed
        if song_name != previous_song:
            previous_song = song_name
            # Display scrolling text for the song name on the first line
            print(f"Song: {song_name}")  # Print the raw song name
            scroll_text(arduino, song_name)
        
        # Display the progress bar and remaining time on the second line
        display_progress_bar(arduino, progress_ms, song_duration_ms, is_playing, song_name)
        
    else:
        # If no song is playing, display "nothing play" on the first line
        arduino.write(f"lcd 1 Dang khong phat nhac!\n".encode())
        arduino.write(f"lcd 2 \n".encode())  # Clear second line if no song is playing
        print("Đang không phát nhạc!")
    
    time.sleep(1)
