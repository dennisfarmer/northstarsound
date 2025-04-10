import pandas as pd
import numpy as np
import os
import subprocess
import sqlite3
import re
import requests
import signal
import argparse
import urllib3
from tqdm import tqdm


from dotenv import dotenv_values
from urllib.parse import quote
env = dotenv_values(".env")
playlist_db = env["PLAYLIST_DB"]
audio_storage = env["AUDIO_STORAGE"]
verbose = env["VERBOSE"] == "True"

keyboard_interrupt = False
#def signal_handler(signal, frame):
    #global keyboard_interrupt
    #keyboard_interrupt = True

#signal.signal(signal.SIGINT, signal_handler)
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
    parser = argparse.ArgumentParser(description="Download audio files from YouTube.")
    parser.add_argument("start_idx", type=int, nargs="?", default=0, help="The starting index of tracks to process.")
    parser.add_argument("end_idx", type=int, nargs="?", default=-1, help="The ending index of tracks to process. Specify 0 to process only tracks[start_idx] (optional).")
    args = parser.parse_args()
    #example_id = "7AzlLxHn24DxjgQX73F9fU"

    downloader = YoutubeAudioDownloader()
    tracks = downloader.retrieve_all_tracks()

    start_idx, end_idx = convert_idx_args(args.start_idx, args.end_idx, len(tracks))
    for track_id, track_name, artist_name in tqdm(tracks[start_idx:end_idx], desc="Downloading audio files"):
        if keyboard_interrupt:
            downloader.close()
            exit()
        try:
            downloader.process_track(track_id, track_name, artist_name)
        except urllib3.exceptions.ProtocolError as e1:
            downloader.commit(force=True)
            try:
                downloader.process_track(track_id, track_name, artist_name)
            except urllib3.exceptions.ProtocolError as e2:
                downloader.close()
                raise e2
            continue










    #example_id = "3VyjsVV24RmBIbWJAeUJNu"



    #tracks = audio_downloader.read_database()
    #for track_id, track_name, artist_name in tracks:
        #if keyboard_interrupt:
            #break
        #audio_downloader.process_track(track_id, track_name, artist_name)