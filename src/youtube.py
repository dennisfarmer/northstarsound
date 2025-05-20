import requests
from urllib.parse import quote
from src.env import *
import re
import os
import subprocess

from src import Track, Playlist, User


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

search_blacklist = [
    "https://www.youtube.com/results?search_query=Aoi+Shiori+-Galileo+Galilei-+%28From+%2522Ao+Hana%2522%29+by+Ralpi+Composer+official+audio"
]

def hash_yt_video_id(video_id: str) -> str:
    hash_value = sum(ord(char) for char in video_id) % 100 + 1
    return f"{hash_value:03}"

    
def search_yt_for_video_id(track: Track, search_blacklist: list = None) -> str:
    if verbose: print("searching via Youtube...")
    search_query = f"{track.name} by {track.artist} official audio".replace("+", "%2B").replace(" ", "+").replace('"', "%22")
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
        print(track.name, track.artist)
        raise YoutubeSearchError(search_query=search_url)
        #raise Exception('video ID of the form "videoId":"MI_XU1iKRRc" not found in youtube request response')


def add_missing_video_ids(tracks: list[Track], max_calls: int|None = 5) -> list[dict]:
    if max_calls is None:
        max_calls = len(tracks)
    num_calls = 0
    new_tracks = []
    for track in tracks:
        if track.video_id is None and (num_calls < max_calls):
            num_calls += 1
            try:
                video_id = search_yt_for_video_id(track)
                #video_id = "sq8GBPUb3rk"
            except requests.exceptions.ConnectionError:
                video_id = None
            track.video_id = video_id
        new_tracks.append(track)
    return new_tracks

def download_audio(video_id: str, use_tmp=True, force=False) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    if os.path.exists(audio_storage_root) and not use_tmp:
        output_dir = os.path.join(audio_storage_root, hash_yt_video_id(video_id))
    else:
        os.makedirs(audio_tmp_storage, exist_ok=True)
        output_dir = audio_tmp_storage

    output_path = os.path.join(output_dir, f"{video_id}.mp3")
    if os.path.exists(output_path):
        if force:
            os.remove(output_path)
        else:
            if verbose: print(f"File already exists: {output_path} - no redownload")
            return output_path

    print(url)
    if running_on_macbook:
        yt = [yt_dlp_macbook, '--extract-audio', '--audio-format', 'mp3', '--quiet', '--no-warnings', '--progress', '--output', output_path, url]
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
    elif running_on_streamlit:
        return None


