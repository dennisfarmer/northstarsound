
#!/usr/bin/env python3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import sqlite3
import requests

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


#from embedding_api.handler import compute_audio_embedding
def compute_audio_embedding(video_id: str|None, url: str = "http://localhost:8080/2015-03-31/functions/function/invocations") -> list[float]|None:
    """
    Note: The compute_audio_embedding function is currently a placeholder because YouTube IP bans my AWS Lambda instance.
    This prevents me from interacting with YouTube to fetch audio data (or compute embeddings) from within the Lambda environment.
    """
    if verbose: print("obtaining track embedding via AWS Lambda...")
    if video_id is None:
        return None
    return None
    #payload = {"video_id": str(video_id)}
    #headers = {"Content-Type": "application/json"}
    
    #response = requests.post(url, data=payload, headers=headers).json()
    #if response["statusCode"] == 200:
        #return response["body"]["embedding"]
    #else:
        #raise FileNotFoundError(f"Failed to compute audio embedding: {response.status_code}, {response.text}")

# curl -XPOST "http://localhost:8080/2015-03-31/functions/function/invocations" -d '{"video_id": "test"}'

def lookup_audio_embedding(video_id: str|None, cursor = None):
    if video_id is None:
        return None
    new_conn = False
    if cursor is None:
        conn = sqlite3.connect(playlist_db)
        cursor = conn.cursor()
        new_conn = True
    embedding = cursor.execute('''
    select * from audio_embeddings where video_id = ?
                            ''', (video_id,)).fetchone()
    if new_conn:
        conn.close()
    if embedding is None:
        return None
    else:
        return embedding[1:]

def lookup_video_id(track_id: str|None, cursor = None):
    if track_id is None:
        return None
    new_conn = False
    if cursor is None:
        conn = sqlite3.connect(playlist_db)
        cursor = conn.cursor()
        new_conn = True
    video_id = cursor.execute('''
    select video_id from audio_files where track_id = ?
                    ''', (track_id,)).fetchone()
    if new_conn:
        conn.close()
    if video_id is None:
        return None
    else:
        return video_id[0]

class YoutubeSearchError(requests.exceptions.ConnectionError):
    """Exception raised when a YouTube search fails to return a valid video ID."""
    def __init__(self, message="Invalid YouTube search result. No video ID found.", search_query=None):
        self.message = message
        self.search_query = search_query
        super().__init__(self.message)

    def __str__(self):
        if self.search_query:
            return f"{self.message} Search query: {self.search_query}"
        return self.message

def search_yt_for_video_id(track_name: str, artist_name: str, search_blacklist: list = None) -> str:
    if verbose: print("searching via Youtube...")
    search_query = f"{track_name} by {artist_name} official audio".replace("+", "%2B").replace(" ", "+").replace('"', "%22")
    search_query = quote(search_query, safe="+")

    search_url = "https://www.youtube.com/results?search_query=" + search_query

    if search_blacklist is not None and search_url in search_blacklist:
        print(f"Audio skipped: blacklist contains {search_url}")
        raise YoutubeSearchError(search_query=search_url)

    request = requests.get(search_url)
    if request.status_code != 200:
        if verbose: print(request.status_code)
        if verbose: print(request.headers)
        if verbose: print(request.reason)
        raise YoutubeSearchError(search_query=search_url)
    html_content = request.text

    match = re.search(r'"videoId":"(.*?)"', html_content)
    if match:
        video_id = match.group(1)
        return video_id
    else:
        print("todo: implement YouTube Data API call as alternative (rate limited)")
        print(track_name, artist_name)
        raise YoutubeSearchError(search_query=search_url)
        #raise Exception('video ID of the form "videoId":"MI_XU1iKRRc" not found in youtube request response')


def add_missing_video_ids(tracks: list[dict], max_calls: int|None = 5) -> list[dict]:
    if max_calls is None:
        max_calls = len(tracks)
    num_calls = 0
    new_tracks = []
    for track in tracks:
        if track["video_id"] is None and (num_calls < max_calls):
            num_calls += 1
            try:
                video_id = search_yt_for_video_id(track["name"], track["artist"])
                #video_id = "sq8GBPUb3rk"
            except requests.exceptions.ConnectionError:
                video_id = None
            track["video_id"] = video_id
        new_tracks.append(track)
    return new_tracks


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
    if (track_id is not None) and (video_id is not None) and (embedding is not None):
        # note: audio_path will be None if not running locally
        # this should be UPDATE OR IGNORE when running locally
        cursor.execute('''
        INSERT OR IGNORE INTO audio_files (track_id, video_id, audio_path)
        VALUES (?, ?, ?)
        ''', (track_id, video_id, audio_path))
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

def get_audio_embeddings_count() -> int:
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM audio_embeddings")
    count = cursor.fetchone()[0]
    conn.close()
    return int(count)

def get_playlist_tracks(playlist_id: str, read_only: bool = False, max_lambda_calls: int|None = 3, max_youtube_calls: int|None = 3) -> list[dict]:
    # todo: implement calling AWS Lambda to compute missing audio embeddings
    # use a single batch ("video_ids": [id1, id2, ...])
    # to minimize calls to AWS Lambda
    num_lambda_calls = 0
    num_youtube_calls = 0

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
    if max_lambda_calls is None:
        max_lambda_calls = len(tracks_json)
    if max_youtube_calls is None:
        max_youtube_calls = len(tracks_json)
    for track_id, track in tracks_json.items():
        video_id = lookup_video_id(track_id, cursor)
        if video_id is None:
            if (num_youtube_calls < max_youtube_calls):
                num_youtube_calls += 1
                try:
                    video_id = search_yt_for_video_id(track['name'], track['artist'])
                except requests.exceptions.ConnectionError:
                    video_id = None
                #audio_path = download_audio(video_id, audio_tmp_storage)
                if num_lambda_calls < max_lambda_calls:
                    num_lambda_calls += 1
                    embedding = compute_audio_embedding(video_id)
                else:
                    embedding = None
                if not read_only:
                    write_track_to_db(track_id=track_id,
                                    name=track['name'],
                                    artist=track['artist'],
                                    album=track['album'],
                                    album_id=track['album_id'],
                                    popularity=track['popularity'],
                                    video_id=video_id,
                                    audio_path=None,
                                    embedding=embedding,
                                    cursor=cursor)
        else:
            embedding = lookup_audio_embedding(video_id, cursor)
            if embedding is None and (num_lambda_calls < max_lambda_calls):
                #print("downloading audio via yt-dlp...")
                #audio_path = download_audio(video_id, audio_tmp_storage)
                num_lambda_calls += 1
                embedding = compute_audio_embedding(video_id)
                if not read_only:
                    write_track_to_db(track_id=track_id,
                                    name=None,
                                    artist=None,
                                    album=None,
                                    album_id=None,
                                    popularity=None,
                                    video_id=video_id,
                                    audio_path=None,
                                    embedding=embedding,
                                    cursor=cursor)

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
    conn.commit()
    conn.close()
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







