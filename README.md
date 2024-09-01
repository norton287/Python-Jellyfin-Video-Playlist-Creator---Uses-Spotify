# Jellyfin Playlist Creator with Spotify Genre Integration

## This Python script automates the creation of genre-based playlists for your Jellyfin media library. It leverages the Spotify API to intelligently identify the genre of your music files (MP3, M4A, MP4, MOV, WebM) and organizes them into separate playlists within Jellyfin.

## Key Features:

- Spotify Genre Detection: Utilizes the Spotify API to accurately determine the genre of your music tracks.
- Automatic Playlist Creation: Generates individual playlists for each identified genre, ensuring well-organized content.
- Jellyfin Integration: Seamlessly integrates with your Jellyfin server, placing the playlists directly into your library.
- Cache Optimization: Employs caching to minimize Spotify API calls, improving efficiency and respecting rate limits.
- Customizable: Easily adaptable to your specific media directory and Jellyfin playlist directory paths.
- User-Friendly: Provides clear console output to track progress and identify any potential issues.

## Prerequisites:

- Python 3.x: Ensure you have Python 3 installed on your system.
- Jellyfin Server: A running Jellyfin server is required for playlist integration.
- Spotify Developer Account: Obtain Spotify API credentials (Client ID and Client Secret) by creating a Spotify Developer application.

## Installation:

- Clone/Download: Clone this repository or download the jlist.py script.

## Install Dependencies: Use pip to install the necessary libraries:

```
pip install spotipy fuzzywuzzy xml.etree.ElementTree configparser
```

## Script Placement: Move the jlist.py script to the /usr/bin directory:

```
sudo mv jlist.py /usr/bin/
```

## Executable Permissions: Make the script executable:

```
sudo chmod +x /usr/bin/jlist.py
```

## Spotify Credentials:

Create a spotify.ini file in a secure location (e.g., your home directory) with the following content:

```
[Spotify]
client_id = YOUR_SPOTIFY_CLIENT_ID
client_secret = YOUR_SPOTIFY_CLIENT_SECRET
```

Replace YOUR_SPOTIFY_CLIENT_ID and YOUR_SPOTIFY_CLIENT_SECRET with your actual Spotify API credentials.   

Set the SPOTIFY_INI_FILE environment variable to the full path of your spotify.ini file. You can add this line to your shell's configuration file (e.g., ~/.bashrc or ~/.zshrc):

```
export SPOTIFY_INI_FILE=/path/to/your/spotify.ini
```

## Configuration:

- Media Directory: Open jlist.py in a text editor and modify the media_dir variable to point to the directory containing your media files.
- Jellyfin Playlist Directory: Update the jelly_dir variable to match the location of your Jellyfin playlist directory.

## Running the Script:

- Open a Terminal: Launch a terminal or command prompt.

- Execute: Run the script using the following command:

```
jlist.py
```

- Observe Output: The script will provide console output indicating its progress, including Spotify API queries and playlist creation.

- Jellyfin Refresh: If your Jellyfin server doesn't automatically detect the new playlists, you might need to manually refresh its library.

## Important Notes:

- Spotify API Limits: The script includes rate limiting to avoid exceeding Spotify's API usage restrictions. However, be mindful of potential limitations if you have a vast media library.
- Genre Accuracy: While Spotify's genre detection is generally reliable, there might be occasional misclassifications.  Also, the script checks the genre hash library and if there are less than 15 songs in a specific genre it will move them to catch all genre playlist to keep it from generating over 600 playlists if you have a large music video library.  I mean some songs in the spotify catalog come up under about 5 to 7 genres.  Seriously Christian Death Metal?  Please....
- File Naming: The script attempts to clean up file names for better Spotify matching. Consider further refining this process if you encounter issues.
- Error Handling: The script includes basic error handling, but unexpected errors might occur. Review the console output for any troubleshooting information.
- Further Customization: Feel free to explore and modify the script to suit your specific needs and preferences.

## Disclaimer: This script interacts with the Spotify API and relies on its functionality. Any changes or disruptions to the Spotify API might affect the script's behavior.

## Feel free to suggest updates or edits with a PR!
