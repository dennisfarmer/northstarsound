
#!/usr/bin/env python3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import sqlite3
import requests
from embedding_api.handler import compute_audio_embedding

from dotenv import dotenv_values
import os
import argparse
from tqdm import tqdm
import re
import pandas as pd
import numpy as np
import os
import subprocess
import sqlite3
import re
import requests
import argparse
from tqdm import tqdm
import urllib3
from urllib.parse import quote
#from threading import Thread

#import signal
keyboard_interrupt = False
#def signal_handler(signal, frame):
    #global keyboard_interrupt
    #keyboard_interrupt = True

#signal.signal(signal.SIGINT, signal_handler)

env = dotenv_values(".env")
verbose = env["VERBOSE"] == "True"
client_id = env["SPOTIPY_CLIENT_ID"]
client_secret = env["SPOTIPY_CLIENT_SECRET"]
audio_storage = env["AUDIO_STORAGE"]
completed_user_ids_csv = env["COMPLETED_USER_IDS_CSV"]
playlist_db = env["PLAYLIST_DB"]


def compute_audio_embedding(video_id: str):
    pass




def hash_video_id(video_id: str) -> str:
    hash_value = sum(ord(char) for char in video_id) % 100 + 1
    return f"{hash_value:03}"

def get_video_id(track_name: str, artist_name: str, search_blacklist: list = None) -> str:
    search_query = f"{track_name} by {artist_name} official audio".replace("+", "%2B").replace(" ", "+").replace('"', "%22")
    search_query = quote(search_query, safe="+")

    search_url = "https://www.youtube.com/results?search_query=" + search_query

    if search_blacklist is not None and search_url in search_blacklist:
        print(f"Audio skipped: blacklist contains {search_url}")
        return None

    request = requests.get(search_url)
    if request.status_code != 200:
        if verbose: print(request.status_code)
        if verbose: print(request.headers)
        raise Exception("HTTP request failed: " + request.reason)
    html_content = request.text

    match = re.search(r'"videoId":"(.*?)"', html_content)
    if match:
        video_id = match.group(1)
        return video_id
    else:
        print("todo: implement YouTube Data API call as alternative (rate limited)")
        print(track_name, artist_name)
        print(search_url)
        raise Exception('video ID of the form "videoId":"MI_XU1iKRRc" not found in youtube request response')

def download_audio(video_id: str, storage_base: str = None, download_path = None, hash_id = False) -> str:
    if download_path is None:
        download_path = ""
    if storage_base is None:
        storage_base = ""
    url = f"https://www.youtube.com/watch?v={video_id}"
    if hash_id:
        subdir = os.path.join(storage_base, hash_video_id(video_id))
    else:
        subdir = storage_base

    os.makedirs(subdir, exist_ok=True)
    output_path = os.path.join(subdir, f"{video_id}.mp3")
    if os.path.exists(output_path):
        if verbose: print(f"File already exists: {output_path}")
        return output_path

    print(url)
    yt = ['./yt-dlp', '--extract-audio', '--audio-format', 'mp3', '--quiet', '--no-warnings', '--progress', '--output', output_path, url]
    output = subprocess.run(yt, capture_output=False, text=True)
    #TODO: handle errors
    #if "Sign in to confirm your age" in output.stderr:
        #print("Age verification required. Skipping.")
        #return None
    #if "not a bot" in output.stderr:
        # "Sign in to confirm you\u2019re not a bot"
        #print("Age verification required. Skipping.")
        #return None
    #if "Requested format is not available" in output.stderr:
        #print("Requested format not available. Skipping.")
        #return None

    return output_path

class YoutubeAudioDownloader:
    def __init__(self, db_path=playlist_db, storage_base=audio_storage):
        self.db_path = db_path
        self.storage_base = storage_base
        os.makedirs(self.storage_base, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.commit_counter = 0
        self.already_processed_counter = 0
        self.search_blacklist = [
            "https://www.youtube.com/results?search_query=Aoi+Shiori+-Galileo+Galilei-+%28From+%2522Ao+Hana%2522%29+by+Ralpi+Composer+official+audio"

        ]
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS audio_files (
            track_id TEXT PRIMARY KEY,
            video_id TEXT,
            audio_path TEXT,
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        );
        ''')
        self.commit(force=True)




    def process_track(self, track_id: str, track_name: str = None, artist_name: str = None):
        if track_name is None or artist_name is None:
            track_name, artist_name = self.retrieve_track_info(track_id)
            if track_name is None or artist_name is None:
                raise Exception(f"Track info not found for track_id {track_id}")
        existing_audio_path = self.retrieve_track_audio(track_id)
        if existing_audio_path is not None:
            if os.path.exists(existing_audio_path):
                self.already_processed_counter += 1
                return
        if self.already_processed_counter > 0:
            print(f"Already processed {self.already_processed_counter} audio files.")
            self.already_processed_counter = 0
        video_id = get_video_id(track_name, artist_name, self.search_blacklist)
        if video_id is None:
            if verbose: print(f"Video ID not found for track_id {track_id}")
            self.cursor.execute('''
            INSERT OR IGNORE INTO audio_files (track_id, video_id, audio_path)
            VALUES (?, ?, ?)
            ''', (track_id, None, None))
            self.commit()
            return
        audio_path = self.download_audio(video_id)
        self.cursor.execute('''
        INSERT OR IGNORE INTO audio_files (track_id, video_id, audio_path)
        VALUES (?, ?, ?)
        ''', (track_id, video_id, audio_path))
        self.commit()
    
    def retrieve_all_tracks(self) -> list[tuple[str, str, str]]:
        self.cursor.execute("SELECT id, name, artist FROM tracks")
        tracks = self.cursor.fetchall()
        return tracks

    def retrieve_track_info(self, track_id: str) -> tuple[str, str] | tuple[None, None]:
        self.cursor.execute("SELECT name, artist FROM tracks WHERE id = ?", (track_id,))
        track_info = self.cursor.fetchone()
        if track_info:
            return track_info[0], track_info[1]
        else:
            # delete from tracks where artist is null
            self.cursor.execute("SELECT name from tracks where artist is null and id = ?", (track_id,))
            track_name = self.cursor.fetchone()
            if track_name:
                return track_name[0], None
            else:
                return None, None

    def retrieve_track_audio(self, track_id: str) -> str | None:
        self.cursor.execute("SELECT audio_path FROM audio_files WHERE track_id = ?", (track_id,))
        audio_path = self.cursor.fetchone()
        if audio_path:
            return audio_path[0]
        else:
            return None

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
        self.commit(force=True)
        self.cursor.close()
        self.conn.close()
        if verbose: print("Database connection closed.")




def playlist_url_to_id(playlist_url: str) -> str:
    match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
    if match:
        playlist_id = match.group(1)
    else:
        raise ValueError("Invalid playlist URL")
    return playlist_id

def playlist_to_json(tracks, playlist_id) -> dict:
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

def write_track_to_db(track_id: str = None, name: str = None, artist: str = None, album: str = None, album_id: str = None, popularity: float = None, video_id: str = None, audio_path: str = None, embedding: list[float] = None, cursor = None):
    new_conn = False
    if cursor is None:
        conn = sqlite3.connect(dotenv_values(".env")["PLAYLIST_DB"])
        cursor = conn.cursor()
        new_conn = True
    if (track_id is not None) and (name is not None) and (artist is not None) and (album is not None) and (album_id is not None) and (popularity is not None):
        cursor.execute('''
        INSERT OR IGNORE INTO tracks (id, name, album_id, artist, popularity)
        VALUES (?, ?, ?, ?, ?)
        ''', (track_id, name, album_id, artist, popularity))
        cursor.execute('''
        INSERT OR IGNORE INTO albums (id, name)
        VALUES (?, ?)
        ''', (album_id, album))
    if (track_id is not None) and (video_id is not None) and (audio_path is not None):
        cursor.execute('''
        INSERT OR IGNORE INTO audio_files (track_id, video_id, audio_path)
        VALUES (?, ?, ?)
        ''', (track_id, video_id, audio_path))
    if (video_id is not None) and (embedding is not None):
        write_embedding_to_db(video_id, embedding, cursor)
    if new_conn: 
        cursor.commit()
        conn.close()

def write_embedding_to_db(video_id, embedding, cursor = None):
    new_conn = False
    if cursor is None:
        conn = sqlite3.connect(dotenv_values(".env")["PLAYLIST_DB"])
        cursor = conn.cursor()
        new_conn = True
    placeholders = ", ".join(["?"] * 51)
    query = f"INSERT OR IGNORE INTO audio_embeddings VALUES ({placeholders})"
    cursor.execute(query, (video_id, *embedding.tolist()))  # Convert numpy array to list
    if new_conn: 
        cursor.commit()
        conn.close()

def get_playlist_tracks(playlist_id):
    spp = SpotifyPlaylistProcessor(client_id, client_secret)
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()
    audio_tmp_storage = dotenv_values(".env")["AUDIO_TMP_STORAGE"]
    os.makedirs(audio_tmp_storage, exist_ok=True)

    try:
        if verbose: print("calling spotify API...")
        tracks = spp.sp.playlist_tracks(playlist_id)
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 400:
            print(f"invalid playlist_id: {playlist_id}")
        raise e
    tracks_json = playlist_to_json(tracks['items'], playlist_id)
    for track_id, track in tracks_json.items():
        video_id = cursor.execute('''
        select video_id from audio_files where track_id = ?
                       ''', (track_id,)).fetchone()
        if video_id is None:
            if verbose: print("searching via Youtube...")
            video_id = get_video_id(track['name'], track['artist'])
            if verbose: print("downloading audio via yt-dlp...")
            audio_path = download_audio(video_id, audio_tmp_storage)
            embedding = compute_audio_embedding(video_id, audio_path)
            write_track_to_db(track_id=track_id,
                               name=track['name'],
                               artist=track['artist'],
                               album=track['album'],
                               album_id=track['album_id'],
                               popularity=track['popularity'],
                               video_id=video_id,
                               audio_path=audio_path,
                               embedding=embedding,
                               cursor=cursor)
            cursor.commit()
        else:
            video_id = video_id[0]
            embedding = cursor.execute('''
            select * from audio_embeddings where video_id = ?
                                    ''', (video_id,)).fetchone()
            if embedding is None:
                print("downloading audio via yt-dlp...")
                audio_path = download_audio(video_id, audio_tmp_storage)
                embedding = compute_audio_embedding(video_id, audio_path)
                write_track_to_db(track_id=track_id,
                                  name=None,
                                  artist=None,
                                  album=None,
                                  album_id=None,
                                  popularity=None,
                                  video_id=video_id,
                                  audio_path=audio_path,
                                  embedding=embedding,
                                  cursor=cursor)
                cursor.commit()
            else:
                embedding = embedding[1:]

        tracks_json[track_id]['video_id'] = video_id
        tracks_json[track_id]['embedding'] = embedding

    playlist_tracks = [
        {
            "video_id": track['video_id'],
            "track_id": track_id,
            "name": track['name'],
            "artist": track['artist'],
            "album": track['album'],
            "album_id": track['album_id'],
            "popularity": track['popularity'],
            "embedding": track['embedding']
        } for track_id, track in tracks_json.items()
    ]
    spp.close()
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
    
    def write_playlist_to_db(self, playlist_id, playlist, tracks_json):
        self.cursor.execute('''
        INSERT OR IGNORE INTO playlists (id, name, description, owner_id, owner_name, total_tracks)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (playlist_id, playlist['name'], playlist['description'], playlist['owner']['id'], playlist['owner']['display_name'], playlist['tracks']['total']))

        for track_id, track in tracks_json.items():
            write_track_to_db(track_id=track_id,
                               name=track['name'],
                               artist=track['artist'],
                               album=track['album'],
                               album_id=track['album_id'],
                               popularity=track['popularity'],
                               video_id=None,
                               audio_path=None,
                               embedding=None,
                               cursor=self.cursor)

            self.cursor.execute('''
            INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id)
            VALUES (?, ?)
            ''', (playlist_id, track_id))

            self.commit()

    def write_user_to_db(self, user_id):
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
            tracks_json = playlist_to_json(tracks, playlist_id)
            self.write_playlist_to_db(playlist_id, playlist, tracks_json)
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
        processor.write_user_to_db(user_id)

    processor.close()
    #parser = argparse.ArgumentParser(description="Download audio files from YouTube.")
    #parser.add_argument("start_idx", type=int, nargs="?", default=0, help="The starting index of tracks to process.")
    #parser.add_argument("end_idx", type=int, nargs="?", default=-1, help="The ending index of tracks to process. Specify 0 to process only tracks[start_idx] (optional).")
    #args = parser.parse_args()
    ##example_id = "7AzlLxHn24DxjgQX73F9fU"

    #downloader = YoutubeAudioDownloader()
    #tracks = downloader.retrieve_all_tracks()

    #start_idx, end_idx = convert_idx_args(args.start_idx, args.end_idx, len(tracks))
    #for track_id, track_name, artist_name in tqdm(tracks[start_idx:end_idx], desc="Downloading audio files"):
        #if keyboard_interrupt:
            #downloader.close()
            #exit()
        #try:
            #downloader.process_track(track_id, track_name, artist_name)
        #except urllib3.exceptions.ProtocolError as e1:
            #downloader.commit(force=True)
            #try:
                #downloader.process_track(track_id, track_name, artist_name)
            #except urllib3.exceptions.ProtocolError as e2:
                #downloader.close()
                #raise e2
            #continue







