from src.db import *
from src import Track, Playlist, User
from src.env import client_id, client_secret, user_ids_csv, completed_user_ids_csv
#from utils.spotify import construct_user
from src.spotify import SpotifyAPI
import sys
import contextlib
from tqdm import tqdm
from time import sleep

#import signal
#keyboard_interrupt = False
#def signal_handler(signal, frame):
    #global keyboard_interrupt
    #keyboard_interrupt = True

#signal.signal(signal.SIGINT, signal_handler)

def get_incomplete_user_ids():
    with open(user_ids_csv, 'r') as f:
        user_ids = set(f.read().splitlines())
    with open(completed_user_ids_csv, "r") as f:
        completed_user_ids = set(f.read().splitlines())
    return list(user_ids - completed_user_ids)



@contextlib.contextmanager
def tqdm_stdout():
    class StandardOutWrapper(object):
        def __init__(self, file):
            self.file = file
        def write(self, x):
            try:
                if len(x.rstrip()) > 0:
                    tqdm.write(x, file=self.file)
            except AttributeError:
                # 'StandardOutWrapper' object has no attribute 'flush'
                pass
    save_stdout = sys.stdout
    sys.stdout = StandardOutWrapper(sys.stdout)
    yield
    sys.stdout = save_stdout

def test(user):
    print(f"dfjsklfjdsk {user}")
    sleep(3)



#def run(start_idx=None, end_idx=None):
def process_users(user_ids):
    #with open(user_ids_csv, 'r') as f:
        #user_ids = f.read().splitlines()
    #with open(completed_user_ids_csv, "r") as f:
        #completed_user_ids = f.read().splitlines()

    #start_idx, end_idx = convert_idx_args(start_idx, end_idx, len(user_ids))
    sp = SpotifyAPI(client_id, client_secret)

    for user_id in tqdm(user_ids, file=sys.stdout, desc="Processing users", leave=False):
        with tqdm_stdout():
            #if user_id in completed_user_ids:
                #print(f"user {user_id} already processed, skipping...")
                #continue
            print(f"processing user {user_id}...")
            user = sp.construct_user(user_id)
            write_user_to_db(user)
            #user = {"user_id": user_id}
            #test(user)
            print("ctrl+c to stop")
        try:
            sleep(2)
        except KeyboardInterrupt:
            print("\nexited gracefully")
            sys.exit(0)



if __name__ == "__main__":
    run()




