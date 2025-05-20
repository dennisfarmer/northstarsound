
#!/usr/bin/env python3

import os
import argparse
from tqdm import tqdm
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
#from threading import Thread

from src import Track, Playlist, User
from src.data_pipeline import process_users
from src.spotify import SpotifyAPI
from src.env import *

def compute_audio_embedding(video_id: str) -> list[float]|None:
    if running_on_streamlit:
        return None
        # curl -XPOST "http://localhost:8080/2015-03-31/functions/function/invocations" -d '{"video_id": "test"}'
        url = "http://localhost:8080/2015-03-31/functions/function/invocations"
        payload = {"video_id": str(video_id)}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, data=payload, headers=headers).json()
        if response["statusCode"] == 200:
            return response["body"]["embedding"]
        else:
            #raise FileNotFoundError(f"Failed to compute audio embedding: {response.status_code}, {response.text}")
            return None
    elif running_on_macbook:
        from embedding_api.handler \
            import compute_audio_embedding as local_compute_audio_embedding
        return local_compute_audio_embedding(video_id)





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Spotify tracks into database for music recommendation model.")
    parser.add_argument("track_ids", type=str, nargs="*", default=[], help="One or more Spotify track IDs to process.")
    parser.add_argument("playlist_ids", type=str, nargs="*", default=[], help="One or more Spotify playlist IDs to process.")
    parser.add_argument("user_ids", type=str, nargs="*", default=[], help="One or more Spotify user IDs to process.")
    parser.add_argument("album_ids", type=str, nargs="*", default=[], help="One or more Spotify album IDs to process.")
    parser.add_argument("artist_ids", type=str, nargs="*", default=[], help="One or more Spotify artist IDs to process.")
    parser.add_argument("n_users", type=int, nargs="?", default=None, help="The number of users to process from the set (user_ids.csv - completed_user_ids.csv).\nLeave blank to process all users.")
    args = parser.parse_args()

    processor = SpotifyAPI()
    #forest_language = processor.construct_album_from_spotify(album_id="2RG4VphteaM49VRa0bwtcP")
    #print(forest_language)
    album_id = "3OHvjfK922rTmAQA37KvKu"
    totrs = processor.construct_album_from_spotify(album_id=album_id)
    print(totrs)

    #shaggs = processor.construct_artist_from_spotify(artist_id = "7xOCUlLxf999J7AGN87Nd7")
    #print(shaggs)

    #for track_id in args.track_ids:
        #processor.write_track_to_db(track_id=track_id)
    #pass
    #for playlist_id in args.playlist_ids:
        #process_playlists(playlist_id)
    #process_users(args.user_ids)
    #user_ids = get_incomplete_user_ids()
    #if args.n_users is not None:
        #process_users(user_ids[:int(args.n_users)])
    #else:
        #process_users(user_ids)

        
        #start_idx, end_idx = convert_idx_args(args.start_idx, args.end_idx, len(user_ids))




