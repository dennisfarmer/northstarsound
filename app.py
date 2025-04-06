from flask import Flask, render_template, request, redirect, url_for
from playlist_data import SpotifyPlaylistProcessor, get_playlist_tracks
import sqlite3
from dotenv import dotenv_values
import os
import argparse
from tqdm import tqdm
import signal
import re
#from threading import Thread

keyboard_interrupt = False
#def signal_handler(signal, frame):
    #global keyboard_interrupt
    #keyboard_interrupt = True

#signal.signal(signal.SIGINT, signal_handler)

env = dotenv_values(".env")
verbose = env["VERBOSE"] == "True"

completed_user_ids_csv = env["COMPLETED_USER_IDS_CSV"]
playlist_db = env["PLAYLIST_DB"]



app = Flask(__name__)



def get_music_recommendations(playlist_id):
    ## This function should return a list of dictionaries with keys:
    ## 'title', 'artist', 'genre', 'album_art', 'preview_url'
    #album_art = "https://f4.bcbits.com/img/a1550557789_2.jpg"
    #example_mp3 = "/Volumes/datascience/data/audio/069/_Wcf5WEwX6s.mp3"
    ##example_mp3 = "./example.mp3"
    example_url = """ \
    https://open.spotify.com/playlist/1bPcEafe3YHOssXSK8wZs8?si=0f1a2c3d4e5f6g7h8i9j0k \
    """
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()

    tracks = cursor.execute('''
        select track_id from playlist_tracks where playlist_id = ?
    ''', (playlist_id,)).fetchall()
    print(tracks)
    #if len(tracks) == 0:
        #spp = SpotifyPlaylistProcessor()
        #tracks = get_playlist_tracks(spp, playlist_id)
    playlist_tracks = [
        {
            "video_id": 123,
            "track_id": 123,
            "title": "Polygondwanaland",
            "artist": "King Gizzard",
            "album": "Polygondwanaland",
        }
    ]
    #return [
    #{
        #"album_art": album_art,
        #"title": "polygondwanaland",
        #"artist": playlist_url,
        #"genre": "psych rock",
        #"preview_url": example_mp3
    #},
    #{
        #"album_art": album_art,
        #"title": "polygondwanaland 2",
        #"artist": "king giz",
        #"genre": "electric boog",
        #"preview_url": example_mp3
    #},
    #]


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        playlist_url = request.form['playlist_url']
        match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
        if match:
            playlist_id = match.group(1)
        else:
            raise ValueError("Invalid playlist URL")
        playlist = get_playlist_tracks
        recommendations = get_music_recommendations(playlist_id)
        return render_template('results.html', playlist=playlist, recommendations=recommendations)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)