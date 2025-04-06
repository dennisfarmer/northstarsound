import pandas as pd
import numpy as np
import os
import subprocess
import sqlite3
import re
import requests
import signal
import argparse
from tqdm import tqdm
import json
from playlist_data import convert_idx_args

from dotenv import dotenv_values
from urllib.parse import quote
env = dotenv_values(".env")
playlist_db = env["PLAYLIST_DB"]
profile = env["EXTRACTOR_PROFILE"]
verbose = env["VERBOSE"] == "True"

#keyboard_interrupt = False
#def signal_handler(signal, frame):
    #global keyboard_interrupt
    #keyboard_interrupt = True

#signal.signal(signal.SIGINT, signal_handler)

class FeatureExtractor:
    def __init__(self, db_path, profile=profile):
        """
        Initialize the FeatureExtractor with the database path.
        Args:
            db_path (str): Path to the SQLite database.
        """
        self.db_path = db_path
        self.profile = profile
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.commit_counter = 0
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS audio_features (
            track_id TEXT PRIMARY KEY,
            video_id TEXT,
            audio_path TEXT,
            FOREIGN KEY (track_id) REFERENCES tracks(id),
            FOREIGN KEY (video_id) REFERENCES audio_files(video_id)
        );
        ''')
        self.commit(force=True)

    def retrieve_all_audios(self):
        """
        Fetch audio file paths from the SQLite database.
        Returns:
            list: A list of audio file paths.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT track_id, video_id, audio_path FROM audio_files")
        audios = self.cursor.fetchall()
        conn.close()
        return audios

    def extract_features(self, video_id, audio_path):
        """
        Extract audio features using the external script.
        Args:
            video_id (str): Video ID.
            audio_path (str): Path to the audio file.
        """
        input_mp3 = audio_path
        output_json = f"features_{video_id}.json"
        subprocess.run(['./bin/audio/streaming_extractor_music', input_mp3, output_json, self.profile], check=True)
        with open(output_json, 'r') as f:
            features_dict = json.load(f)
        os.remove(output_json)

        features = (features_dict["rhythm"]["danceability"], features_dict["rhythm"]["onset_rate"])
        return features
    
    def save_features_to_db(self, video_id, features):
        """
        Save extracted audio features to the database.
        Args:
            video_id (str): Video ID.
            features (tuple): Tuple of audio features.
        """
        
        self.cursor.execute('''
        INSERT OR IGNORE INTO audio_features (video_id, danceability, onset_rate)
        VALUES (?, ?, ?)
        ''', (video_id, *features))
        self.commit()

    def process_audio_files(self):
        """
        Process all audio files from the database and extract features.
        """
        audio_paths = self.get_audio_paths_from_db()
        for video_id, audio_path in audio_paths:
            features = self.extract_features(video_id, audio_path)
            self.save_features_to_db(video_id, features)

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

if __name__ == "__main__":
    pass