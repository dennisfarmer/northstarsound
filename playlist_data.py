
#!/usr/bin/env python3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import sqlite3
import time
import requests
from audio_data import get_video_id, download_audio
from embedding_data import compute_audio_embedding

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
client_id = env["SPOTIPY_CLIENT_ID"]
client_secret = env["SPOTIPY_CLIENT_SECRET"]

completed_user_ids_csv = env["COMPLETED_USER_IDS_CSV"]
playlist_db = env["PLAYLIST_DB"]

def playlist_url_to_id(playlist_url: str) -> str:
    match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
    if match:
        playlist_id = match.group(1)
    else:
        raise ValueError("Invalid playlist URL")
    return playlist_id

def process_playlist(tracks, playlist_id) -> dict:
    if verbose: print(f"\tprocessing playlist {playlist_id}...")
    tracks_json = {}
    for track in tracks:
        try:
            track_id = track['track']['id']
        except TypeError as e:
            if verbose: print(f"\t\tTrack has been removed from Spotify, skipping...")
            continue
        track_name = track['track']['name']
        track_artists = [{'name': artist['name'], 'id': artist['id']} for artist in track['track']['artists']]
        track_album = track['track']['album']['name']
        track_album_id = track['track']['album']['id']
        tracks_json[track_id] = {
            'name': track_name,
            'album': track_album,
            'album_id': track_album_id,
            'artist': track_artists[0]['name'],
            'popularity': track['track']['popularity']
        }
    return tracks_json

#def write_playlist_to_db(self, tracks_json, cursor):
    #for track_id, track in tracks_json.items():
        #cursor.execute('''
        #INSERT OR IGNORE INTO tracks (id, name, album_id, artist, popularity)
        #VALUES (?, ?, ?, ?, ?)
        #''', (track_id, track['name'], track['album_id'], track['artist'], track['popularity']))

        #cursor.execute('''
        #INSERT OR IGNORE INTO albums (id, name)
        #VALUES (?, ?)
        #''', (track['album_id'], track['album']))

        #cursor.execute('''
        #INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id)
        #VALUES (?, ?)
        #''', (playlist_id, track_id))

        #self.commit()

#def write_track_to_db(track_id, track, conn):
def write_embedding_to_db(video_id, embedding, conn):
    placeholders = ", ".join(["?"] * 51)
    query = f"INSERT OR REPLACE INTO audio_embeddings VALUES ({placeholders})"
    conn.execute(query, (video_id, *embedding.tolist()))  # Convert numpy array to list
    conn.commit()

def get_playlist_tracks(playlist_id):
    spp = SpotifyPlaylistProcessor(client_id, client_secret)
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()

    try:
        if verbose: print("calling spotify API...")
        tracks = spp.sp.playlist_tracks(playlist_id)
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 400:
            print(f"invalid playlist_id: {playlist_id}")
        raise e
    tracks_json = process_playlist(tracks['items'], playlist_id)
    for track_id, track in tracks_json.items():
        video_id = cursor.execute('''
        select video_id from audio_files where track_id = ?
                       ''', (track_id,)).fetchone()
        if video_id is None:
            if verbose: print("searching via Youtube...")
            video_id = get_video_id(track['name'], track['artist'])
            if verbose: print("downloading audio via yt-dlp...")
            audio_path = download_audio(video_id, "./data/audio/")
            embedding = compute_audio_embedding((video_id, audio_path))
        else:
            video_id = video_id[0]
            embedding = cursor.execute('''
            select * from audio_embeddings where video_id = ?
                                    ''', (video_id,)).fetchone()
            if embedding is None:
                print("downloading audio via yt-dlp...")
                audio_path = download_audio(video_id, "./data/audio/")
                embedding = compute_audio_embedding((video_id, audio_path))
            else:
                embedding = embedding[1:]

        tracks_json[track_id]['video_id'] = video_id
        tracks_json[track_id]['embedding'] = embedding

    playlist_tracks = [
        {
            "video_id": track['video_id'],
            "track_id": track_id,
            "title": track['name'],
            "artist": track['artist'],
            "album": track['album'],
            "album_id": track['album_id'],
            "popularity": track['popularity'],
            "embedding": track['embedding']
        } for track_id, track in tracks_json.items()
    ]
    return playlist_tracks




class SpotifyPlaylistProcessor:
    def __init__(self, client_id, client_secret, db_name=playlist_db):
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id,
                                                                        client_secret=client_secret))
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.commit_counter = 0
        self._create_tables()
        self.completed_user_ids = []
        self.refresh_completed_user_ids()

    def _create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            owner_id TEXT,
            owner_name TEXT,
            total_tracks INTEGER
        );
        ''')
        self.commit(force=True)

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS albums (
            id TEXT PRIMARY KEY,
            name TEXT
        );
        ''')
        self.commit(force=True)

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            name TEXT,
            album_id TEXT,
            artist TEXT,
            popularity INTEGER,
            FOREIGN KEY (album_id) REFERENCES albums(id)
        );
        ''')
        self.commit(force=True)

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            playlist_id TEXT,
            track_id TEXT,
            PRIMARY KEY (playlist_id, track_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(id),
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        );
        ''')

        self.commit(force=True)

    #def _retry_on_429(self, func, *args, **kwargs):
        #while True:
            #try:
                #return func(*args, **kwargs)
            #except spotipy.exceptions.SpotifyException as e:
                ## this code is redundant
                #if e.http_status == 429:
                    #if verbose: print("WARNING:root:Your application has reached a rate/request limit. Retry will occur after:", e.headers['Retry-After'])
                    #time.sleep(int(e.headers['Retry-After']) + 1)
                    #try:
                        #return func(*args, **kwargs)
                    #except spotipy.exceptions.SpotifyException as e:
                        #raise e
                #else:
                    #raise e
            #except requests.exceptions.ReadTimeout as e:
                #if verbose: print("ReadTimeout: Check internet connection or Spotify API status. Also, computer might be locked.")
                #raise e
    
    def refresh_completed_user_ids(self):
        if not os.path.exists(completed_user_ids_csv):
            with open(completed_user_ids_csv, 'w') as f:
                pass
        with open(completed_user_ids_csv, 'r') as f:
            self.completed_user_ids = f.read().splitlines()
    


    def write_playlist_to_db(self, playlist_id, tracks_json):
        for track_id, track in tracks_json.items():
            self.cursor.execute('''
            INSERT OR IGNORE INTO tracks (id, name, album_id, artist, popularity)
            VALUES (?, ?, ?, ?, ?)
            ''', (track_id, track['name'], track['album_id'], track['artist'], track['popularity']))

            self.cursor.execute('''
            INSERT OR IGNORE INTO albums (id, name)
            VALUES (?, ?)
            ''', (track['album_id'], track['album']))

            self.cursor.execute('''
            INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id)
            VALUES (?, ?)
            ''', (playlist_id, track_id))

            self.commit()

    def process_user(self, user_id):
        if user_id in self.completed_user_ids:
            if verbose: print(f"user {user_id} already processed, skipping...")
            return
        if verbose: print(f"processing user {user_id}...")
        playlists = self.sp.user_playlists(user_id)
        playlist_json = {}
        for playlist in playlists['items']:
            playlist_id = playlist['id']
            #tracks = self._retry_on_429(self.sp.playlist_tracks, playlist_id)
            tracks = self.sp.playlist_tracks(playlist_id)
            playlist_json[playlist_id] = [playlist, tracks['items']]
        if verbose: print(f"found {len(playlist_json)} playlists:")
        for playlist_id, (playlist, tracks) in playlist_json.items():
            tracks_json = process_playlist(tracks, playlist_id)
            self.write_playlist_to_db(playlist_id, tracks_json)

            self.cursor.execute('''
            INSERT OR IGNORE INTO playlists (id, name, description, owner_id, owner_name, total_tracks)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (playlist_id, playlist['name'], playlist['description'], playlist['owner']['id'], playlist['owner']['display_name'], playlist['tracks']['total']))
            self.commit(force=True)
        with open(completed_user_ids_csv, 'a') as file:
            file.write(f"{user_id}\n")
        self.completed_user_ids.append(user_id)
        if verbose: print(f"user {user_id} processed successfully")

    def commit(self, force = False):
        if force:
            self.conn.commit()
            self.commit_counter = 0
        else:
            self.commit_counter += 1
            if self.commit_counter >= 10:
                self.conn.commit()
                self.commit_counter = 0

    def close(self):
        #self.cursor.execute('''delete from tracks where artist is null;''')
        self.commit(force=True)
        self.cursor.close()
        self.conn.close()

def convert_idx_args(start_idx: int, end_idx: int|None, max_idx: int) -> tuple[int, int]:
    if start_idx is None:
        start_idx = 0
    if end_idx is None or end_idx == 0:
        end_idx = start_idx + 1
    elif end_idx == -1:
        end_idx = max_idx
    elif end_idx > max_idx:
        raise ValueError("Invalid end_index: end_index must be less than or equal to the number of user IDs.")

    if start_idx < 0 or start_idx >= max_idx:
        raise ValueError("Invalid start_index: start_index must be non-negative and less than the number of user IDs.")

    if end_idx <= start_idx:
        raise ValueError("Invalid indices: end_index must be greater than start_index.")
    return start_idx, end_idx



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Spotify user playlists.")
    parser.add_argument("start_idx", type=int, nargs="?", default=0, help="The starting index of user IDs to process.")
    parser.add_argument("end_idx", type=int, nargs="?", default=None, help="The ending index of user IDs to process. Specify -1 to process all user IDs (optional).")
    args = parser.parse_args()

    processor = SpotifyPlaylistProcessor(env["SPOTIPY_CLIENT_ID"], env["SPOTIPY_CLIENT_SECRET"])

    with open(env["USER_IDS_CSV"], 'r') as f:
        user_ids = f.read().splitlines()

    start_idx, end_idx = convert_idx_args(args.start_idx, args.end_idx, len(user_ids))


    for user_id in tqdm(user_ids[start_idx:end_idx], desc="Processing users"):
        if keyboard_interrupt:
            break
        processor.process_user(user_id)

    processor.close()