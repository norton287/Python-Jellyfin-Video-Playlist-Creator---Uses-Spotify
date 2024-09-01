#!/usr/bin/python3
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from fuzzywuzzy import fuzz # Fuzzy logic for grabbing the genres from the Spotify output
import time
import pickle  # For caching
import configparser # Reads the INI

# Read INI file path from environment variable
ini_file_path = os.environ.get('SPOTIFY_INI_FILE') # Put the ini in a secure directory and do an export of a var in the env or bashrc
if not ini_file_path:
    raise ValueError("SPOTIFY_INI_FILE environment variable not set")

# Read Spotify credentials from INI file
config = configparser.ConfigParser()
config.read(ini_file_path) 

client_id = config['Spotify']['client_id'] # Read from env variable
client_secret = config['Spotify']['client_secret'] # Read from env variable
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Cache setup, cache previous lookups to keep from using up your API calls and looking like a scraper to Spotify.  This saves time as well.
cache_file = "spotify.cache"
use_cache = os.path.exists(cache_file)
if use_cache:
    with open(cache_file, 'rb') as f:
        cache = pickle.load(f)
else:
    cache = {}

# Vars
media_dir = "/volumes/data/metube/downloads/completed" # Where the videos are stored at after verter.sh runs
jelly_dir = "/var/lib/jellyfin/data/playlists" # Where the Jellyfin playlist directories are stored
last_api_call_time = 0 # How many times the API has been called, keep from over using it and triggering a cool down
COOLDOWN_TIME = 5 # Set a hold back counter to keep from tripping API over use
trips = 0  # Initialize trips counter
MAX_TRIPS = 3  # Maximum allowed trips before stopping

def consolidate_genres(genres, cache):
    """Consolidates genres, updates the cache and genres array."""

    mixed_songs = genres.get('Mixed Songs', [])
    for genre, files in list(genres.items()):
        if genre != 'Mixed Songs' and len(files) < 15:
            # Clear the genre from the genres array and move to mixed
            del genres[genre]
            mixed_songs.extend(files)  

            # Remove genre and update cache
            for file in files:
                if file in cache:
                    del cache[file]
                cache[file] = 'Mixed Songs'

    # Update or create 'Mixed Songs' genre
    if mixed_songs:
        genres['Mixed Songs'] = mixed_songs

    # Update cache for 'Mixed Songs' (if it wasn't already there)
    if 'Mixed Songs' not in genres:
        for file in mixed_songs:
            cache[file] = 'Mixed Songs'

    # Save cache when script finishes
    with open(cache_file, 'wb') as f:
        pickle.dump(cache, f)

# Main Spotify API query function, we're caching the genres to a hash file to store locally later if you rerun the script to save from looking up old videos
def get_genre_from_spotify(track_name):
    global trips, last_api_call_time

    if trips >= MAX_TRIPS:
        print("Spotify API call limit reached!")
        return None  # Return None if limit reached

    # Cooldown timer
    current_time = time.time()
    time_since_last_call = current_time - last_api_call_time
    if time_since_last_call < COOLDOWN_TIME:
        time.sleep(COOLDOWN_TIME - time_since_last_call)
    last_api_call_time = time.time()

    # Check cache for genre for Video file (looks at full path and file name) and returns the genres stored in table if they exist
    if use_cache and track_name in cache:
        print(f"Cache Returned the Genres {cache[track_name]} for {track_name}")
        return cache[track_name]

    try:
        results = sp.search(q=track_name, type='track', limit=5)
        if results['tracks']['items']:
            best_match = max(results['tracks']['items'], 
                key=lambda item: fuzz.partial_ratio(track_name.lower(), item['name'].lower()))

            # Get the artist URI from the best match
            artist_uri = best_match['artists'][0]['uri']

            # Use the artist URI to get the artist's information
            artist = sp.artist(artist_uri)

            # If genres are found in the artist information, store and return the first one
            if 'genres' in artist and artist['genres']:
                first_genre = artist['genres'][0]
                print(f"Spotify Returned the Genre {first_genre} for {track_name}")
                cache[track_name] = first_genre
                trips = 0
                return first_genre
            else:
                print(f"Returned None for {track_name}")
                return None # Return None if no genres available
        else:
            print("Spotify Search Failed!")
            return None
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 429:
            retry_after = int(e.headers.get('Retry-After', 1))
            print(f"Rate limit hit, retrying after {retry_after} seconds...")
            trips += 1
            time.sleep(retry_after)
            return get_genre_from_spotify(track_name)
        else:
            print(f"Spotify API error for: {track_name}. Error: {e}")
            return None

# Doing a couple of things people on Youtube are weird and name things weird so clean the names just a hair before starting.  This could be enhanced with a dictionary of common filename elements to look for and remove later to further clean up the names to make for better API queries and returns
def create_playlists(media_dir):
    genres = {}
    all_files = []

    for root, _, files in os.walk(media_dir):
        for file in files:
            if file.endswith(('.mp3', '.m4a', '.mp4', '.mov', '.webp')):
                file_path = os.path.join(root, file)
                all_files.append(file_path)

                video_title = os.path.splitext(file)[0]
                # Strip date suffix before checking cache
                last_hyphen_index = video_title.rfind(" - ")
                if last_hyphen_index != -1 and last_hyphen_index < len(video_title) - 10:
                    video_title2 = video_title[:last_hyphen_index]
                # Extract the desired part
                video_title3 = ""
                second_last_hyphen_index = video_title2.rfind(" - ")
                if second_last_hyphen_index != -1:
                    desired_part = video_title2[second_last_hyphen_index + 3:]
                    video_title3 = desired_part
                if video_title3 is not None and video_title3 != "":
                    print(f"Grabbing Genre For Title {video_title3}")
                else:
                    print("Track Name Was Empty")
                genre = get_genre_from_spotify(video_title3)

                if genre:
                    for g in genre:
                        genres.setdefault(g, []).append(file_path)  
                else:
                    if video_title3 is not None and video_title3 != "":
                        print(f"No Genre Found for Track {video_title3}")
                    else:
                        print("Track Name Was Empty")
                    genres.setdefault('Unknown', []).append(file_path)

    consolidate_genres(genres, cache) # Function call goes here

    # Create playlist files
    for genre, files in genres.items():
        upper_genre = genre.title()

        # XML structure (consider using a templating library like Jinja2 for flexibility)
        item = ET.Element('Item')
        ET.SubElement(item, 'ContentRating').text = 'TV-PG-LV'
        ET.SubElement(item, 'Added').text = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        ET.SubElement(item, 'LockData').text = 'false'
        ET.SubElement(item, 'CustomRating').text = 'TV-PG-LV'
        ET.SubElement(item, 'LocalTitle').text = upper_genre
        ET.SubElement(item, 'PremiereDate').text = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        ET.SubElement(item, 'Rating').text = '10'
        ET.SubElement(item, 'ProductionYear').text = '2024'
        ET.SubElement(item, 'RunningTime').text = '12'  # Replace with actual running time
        ET.SubElement(item, 'OwnerUserId').text = '9ae46b00b80d43acb17867c206ba44e7'
        playlist_items = ET.SubElement(item, 'PlaylistItems')

        for file_path in files:
            if file_path:
                playlist_item = ET.SubElement(playlist_items, 'PlaylistItem')
                ET.SubElement(playlist_item, 'Path').text = file_path

        # Add Shares and PlaylistMediaType outside the loop
        ET.SubElement(item, 'Shares')
        ET.SubElement(item, 'PlaylistMediaType').text = 'Video'

        # Write the XML file
        tree = ET.ElementTree(item)
        play_dir = os.path.join(jelly_dir,upper_genre)  # Use jelly_dir here
        os.makedirs(play_dir, exist_ok=True)

        # Write playlist to file inside the genre directory (using jelly_dir)
        playlist_efile = os.path.join(play_dir, "playlist.xml")
        tree = ET.ElementTree(item)
        tree.write(playlist_efile, encoding='utf-8', xml_declaration=True)

        # Change ownership to 'jellyfin' user and group
        try:
            result = subprocess.run(["chown", "-R", "jellyfin:jellyfin", jelly_dir], capture_output=True, text=True)  # Recursive ownership change
            if result.returncode != 0:
                raise Exception(f"Couldn't set rights for Jellyfin on Playlist Directory {result.stderr}")  # Corrected variable name
        except Exception as e:
            print(f"Error setting Jellyfin rights: {e}")

    # Create master playlist
    item = ET.Element('Item')
    ET.SubElement(item, 'ContentRating').text = 'TV-PG-LV'
    ET.SubElement(item, 'Added').text = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    ET.SubElement(item, 'LockData').text = 'false'
    ET.SubElement(item, 'CustomRating').text = 'TV-PG-LV'
    ET.SubElement(item, 'LocalTitle').text = "All"
    ET.SubElement(item, 'PremiereDate').text = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    ET.SubElement(item, 'Rating').text = '10'
    ET.SubElement(item, 'ProductionYear').text = datetime.now().strftime("%Y")
    ET.SubElement(item, 'RunningTime').text = '12'  # Replace with actual running time
    ET.SubElement(item, 'OwnerUserId').text = '9ae46b00b80d43acb17867c206ba44e7' # Replace with your UserID
    playlist_items = ET.SubElement(item, 'PlaylistItems')

    for genre, files in genres.items():  # Iterate over the genres dictionary
        for file_path in files:
            if file_path:
                playlist_item = ET.SubElement(playlist_items, 'PlaylistItem')
                temp_path = os.path.join(media_dir, file_path)
                ET.SubElement(playlist_item, 'Path').text = temp_path

    # Add Shares and PlaylistMediaType outside the loop
    ET.SubElement(item, 'Shares')
    ET.SubElement(item, 'PlaylistMediaType').text = 'Video'
    play_dir = os.path.join(jelly_dir, "All")  # Use jelly_dir here
    os.makedirs(play_dir, exist_ok=True)

    # Write playlist to file inside the genre directory (using jelly_dir)
    playlist_dfile = os.path.join(play_dir, "playlist.xml")
    tree = ET.ElementTree(item)

    # Use indent to format the XML output
    ET.indent(tree, space="\t", level=0)  # Use tabs for indentation

    tree.write(playlist_dfile, encoding='utf-8', xml_declaration=True)

    # Change ownership to 'jellyfin' user and group
    try:
        result = subprocess.run(["chown", "-R", "jellyfin:jellyfin", jelly_dir], capture_output=True, text=True)  # Recursive ownership change
        if result.returncode != 0:
            raise Exception(f"Couldn't set rights for Jellfin on Playlist Directory {result.stderrr}")
    except Exception as e:
        print(f"Error setting Jellyfin rights: {e}")

# Get paths
media_dir = "/volumes/data/metube/downloads/completed"

# Run the main function
create_playlists(media_dir)

# Restart Jellyfin to read the new playlists
try:
    result = subprocess.run(["systemctl", "restart", "jellyfin"], capture_output=True, text=True)  # Capture output for debugging
    if result.returncode != 0:  # Check if command was successful
        raise Exception(f"Jellyfin restart failed: {result.stderr}")
except Exception as e:
    print(f"Error restarting Jellyfin: {e}")

# Save cache when script finishes
with open(cache_file, 'wb') as f:
    pickle.dump(cache, f)
