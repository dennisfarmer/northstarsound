import os
import platform
from dotenv import dotenv_values

environment = "macbook" if platform.system() == "Darwin" else ("streamlit" if platform.system() == "Linux" else None)
running_on_macbook = environment == "macbook"
running_on_streamlit = environment == "streamlit"

if environment is None:
    raise Exception("Unsupported operating system. Cannot load environment variables.")
elif running_on_macbook:
    env = dotenv_values(".env")
elif running_on_streamlit:
    env = os.environ

client_id = env["SPOTIPY_CLIENT_ID"]
client_secret = env["SPOTIPY_CLIENT_SECRET"]
ngrok_authtoken = env["NGROK_AUTHTOKEN"]

user_ids_csv = env["USER_IDS_CSV"]
completed_user_ids_csv = env["COMPLETED_USER_IDS_CSV"]
musicdb = env["MUSIC_DB"]
audio_storage_root = env["AUDIO_STORAGE_ROOT"]
audio_tmp_storage = env["AUDIO_TMP_STORAGE"]
yt_dlp_macbook = env["YT_DLP_MACBOOK"]
yt_dlp_linux = env["YT_DLP_LINUX"]
verbose = env["VERBOSE"] == "True"
read_only = env["READ_ONLY"] == "True"

try:
    k_min = int(env["K_MIN"])
except:
    k_min = 1
try:
    k_max = int(env["K_MAX"])
except:
    k_max = 10
try:
    k_hybrid_search_space = int(env["K_HYBRID_SEARCH_SPACE"])
except:
    k_hybrid_search_space = 1000