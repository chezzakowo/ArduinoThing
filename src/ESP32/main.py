import network
import urequests
import time
import socket
import ubinascii
import json
import _thread
import unicodedata
from machine import I2C, Pin
from esp8266_i2c_lcd import I2cLcd

# User config
SSID = ""  
PASSWORD = ""  
CLIENT_ID = ""  
CLIENT_SECRET = ""  

# API - DO NOT CHANGE IF YOU DON'T KNOW WHAT YOU'RE DOING
TOKEN_URL = "https://accounts.spotify.com/api/token"

# Screen pins, do not touch if you don't know what you're doing
I2C_SCL_PIN = 22  # SCL pin
I2C_SDA_PIN = 21  # SDA pin
I2C_ADDR = 0x27   # LCD address

i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

access_token = None
refresh_token = None
local_redirect_uri = None
auth_url = None

def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Checking WiFi status...")
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
    ip = wlan.ifconfig()[0]
    print("Connected successfully! My IP address:", ip)
    return ip

def get_tokens_from_code(auth_code, redirect_uri):
    client_credentials = "{}:{}".format(CLIENT_ID, CLIENT_SECRET)
    encoded_credentials = ubinascii.b2a_base64(client_credentials.encode()).decode("utf-8").strip()
    headers = {"Authorization": "Basic " + encoded_credentials,
               "Content-Type": "application/x-www-form-urlencoded"}
    data = "grant_type=authorization_code&code=" + auth_code + "&redirect_uri=" + redirect_uri
    try:
        response = urequests.post(TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            token_info = response.json()
            return token_info["access_token"], token_info["refresh_token"]
        else:
            print("Failed to exchange code for token:", response.text)
            return None, None
    except Exception as e:
        print("Error exchanging code:", e)
        return None, None

def refresh_access_token(refresh_token_val):
    client_credentials = "{}:{}".format(CLIENT_ID, CLIENT_SECRET)
    encoded_credentials = ubinascii.b2a_base64(client_credentials.encode()).decode("utf-8").strip()
    headers = {"Authorization": "Basic " + encoded_credentials,
               "Content-Type": "application/x-www-form-urlencoded"}
    data = "grant_type=refresh_token&refresh_token=" + refresh_token_val
    try:
        response = urequests.post(TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            token_info = response.json()
            return token_info["access_token"]
        else:
            print("Failed to refresh token:", response.text)
            return None
    except Exception as e:
        print("Error refreshing token:", e)
        return None

def get_current_playback(access_token_val):
    headers = {"Authorization": "Bearer " + access_token_val}
    response = urequests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
    if response.status_code == 200:
        playback = response.json()
        if playback and "item" in playback:
            song_name = playback["item"]["name"]
            progress_ms = playback["progress_ms"]
            duration_ms = playback["item"]["duration_ms"]
            is_playing = playback["is_playing"]
            return song_name, progress_ms, duration_ms, is_playing
        else:
            print("No song is currently playing.")
            return None, 0, 0, False
    elif response.status_code == 204:
        print("No music playing.")
        return None, 0, 0, False
    elif response.status_code == 401:
        print("Unauthorized: Token expired or invalid.")
        return "TOKEN_ERROR", 0, 0, False
    else:
        print("Error retrieving playback info: {} - {}".format(response.status_code, response.text))
        return "TOKEN_ERROR", 0, 0, False

# Function to convert special characters in song name to plain characters
def remove_special_characters(text):
    # Normalize the string and remove diacritics
    normalized_text = unicodedata.normalize('NFD', text)
    return ''.join([c for c in normalized_text if unicodedata.category(c) != 'Mn'])

# Function to scroll song name on the LCD screen
def scroll_text(lcd, text):
    max_length = 16  # Assuming LCD screen has 16 characters per line
    text = remove_special_characters(text)  # Convert special characters to plain characters
    
    if len(text) <= max_length:
        lcd.move_to(0, 0)
        lcd.putstr(text)
        return
    
    for i in range(len(text) - max_length + 1):
        lcd.move_to(0, 0)
        lcd.putstr(text[i:i+max_length])
        time.sleep(0.3)
    
    for i in range(len(text) - max_length, -1, -1):
        lcd.move_to(0, 0)
        lcd.putstr(text[i:i+max_length])
        time.sleep(0.3)

def update_lcd(song, progress_ms, duration_ms, is_playing):
    lcd.clear()
    if song:
        if len(remove_special_characters(song)) > 16:
            scroll_text(lcd, song)
        else:
            lcd.move_to(0, 0)
            lcd.putstr(song[:16])
        
        lcd.move_to(0, 1)
        if is_playing:
            progress_min = progress_ms // 60000
            progress_sec = (progress_ms // 1000) % 60
            duration_min = duration_ms // 60000
            duration_sec = (duration_ms // 1000) % 60
            time_line = "{:02}:{:02}/{:02}:{:02}".format(progress_min, progress_sec, duration_min, duration_sec)
            lcd.putstr(time_line)
        else:
            lcd.putstr("Paused!")
    else:
        lcd.putstr("No music playing!")

def main():
    global access_token, refresh_token, local_redirect_uri, auth_url
    ip_address = connect_to_wifi()
    local_redirect_uri = "http://{}:80/callback".format(ip_address)
    
    while True:
        song, progress_ms, duration_ms, is_playing = get_current_playback(access_token)
        if song == "TOKEN_ERROR":
            lcd.clear()
            lcd.putstr("No key")
            lcd.move_to(0, 1)
            lcd.putstr(ip_address)
        else:
            update_lcd(song, progress_ms, duration_ms, is_playing)
        time.sleep(1)

if __name__ == "__main__":
    main()
