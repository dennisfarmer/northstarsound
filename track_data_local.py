
#!/usr/bin/env python3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import sqlite3
import requests
from add_music import *
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
import platform
#from threading import Thread

#import signal
keyboard_interrupt = False
#def signal_handler(signal, frame):
    #global keyboard_interrupt
    #keyboard_interrupt = True

#signal.signal(signal.SIGINT, signal_handler)
