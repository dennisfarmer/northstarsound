#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from netscape_cookies import to_netscape_string
#from selenium.webdriver.chrome.service import Service
#from webdriver_manager.chrome import ChromeDriverManager
#from webdriver_manager.core.os_manager import ChromeType

def get_driver(options):
    return webdriver.Chrome(
        #service=Service(
            #ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        #),
        options=options
    )

def get_cookies():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")

    driver = get_driver(options)
    driver.get("https://www.youtube.com/watch?v=_r-nPqWGG6c")
    cookies = driver.get_cookies()
    return to_netscape_string(cookies)

import os
import subprocess

def download_audio(video_id: str = "UZyTZVH-OO0", subdir: str = ".", cookies_path: str = "./cookies.txt") -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"

    #yt_dlp = os.path.join(os.path.dirname(__file__), 'yt-dlp_linux')
    yt_dlp = os.path.join(os.path.dirname(__file__), 'yt-dlp')
    #ffmpeg = os.path.join(os.path.dirname(__file__), "embedding_api", 'ffmpeg')

    os.makedirs(subdir, exist_ok=True)
    webm_path = os.path.join(subdir, f"{video_id}.webm")
    mp4_path = os.path.join(subdir, f"{video_id}.mp4")
    mp3_path = os.path.join(subdir, f"{video_id}.mp3")
    print(url)
    #yt = [yt_dlp, '--extract-audio', '--audio-format', 'mp3', '--quiet', 
          #'--no-warnings', '--progress', '--ffmpeg-location', ffmpeg, '--output', audio_path, url]
    yt = [yt_dlp, '--extract-audio', '--audio-format', 'mp3',
          '--progress',
          #'--ffmpeg-location', ffmpeg, 
          '--cookies-from-browser', 'chrome', 
          '--cookies', cookies_path, 
          '--output', webm_path, url]

    # fails at conversion step; something about expecting string/bytes but getting None (??)
    yt_output = subprocess.run(yt, capture_output=True, text=True)
    print("yt_output:")
    print(yt_output)

    # workaround: manually convert to mp3
    #ff_output = subprocess.run([ffmpeg, "-i", webm_path, "-vn", "-ab", "128k", "-ar", "44100", "-y", mp3_path], capture_output=True, text=True)
    #print("ff_output:")
    #print(ff_output)

    #if not os.path.exists(mp3_path):
        #raise FileNotFoundError(f"The audio file wasn't actually downloaded/converted from Youtube properly (Youtube might think you're a bot / need to verify age / etc., or you might be using an incompatable ffmpeg binary - see Makefile for download source) -- {yt_output}, {ff_output}")

    for f in [mp4_path, webm_path]:
        if os.path.exists(f):
            os.remove(f)
    return mp3_path
    

if __name__ == "__main__":
    #with open("cookies.txt", "w") as f:
        #f.write(get_cookies())
    file_path = download_audio("UZyTZVH-OO0", subdir=".", cookies_path="cookies.txt")