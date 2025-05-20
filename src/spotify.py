import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
from .env import *
from .db import connect_to_database, write_track_to_db
from . import Track, Playlist, User, Album, ArtistInfo, Artist


#def convert_spotify_playlist(sp_tracks, playlist_id) -> dict[Track]:
    #if verbose: print(f"\tconverting playlist {playlist_id}...")
    #tracks_json = {}
    #for track in sp_tracks:
        #try:
            #track_id = track['track']['id']
        #except TypeError as e:
            #if verbose: print(f"\t\tTrack has been removed from Spotify, skipping...")
            #continue
        #track_artists = [{'name': artist['name'], 'id': artist['id']} for artist in track['track']['artists']]
        #tracks_json[track_id] = Track(
            #track_id=track_id,
            #name=track['track']['name'],
            #album=track['track']['album']['name'],
            #album_id=track['track']['album']['id'],
            #artist=track_artists[0]['name'],
            #popularity=track['track']['popularity'],
        #)
    #return tracks_json



class SpotifyAPI:
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id,
                                                                        client_secret=client_secret))
        self.conn, self.cursor = connect_to_database()
        #self.conn = sqlite3.connect(db_name)
        #self.cursor = self.conn.cursor()
        self.commit_counter = 0
        #self._create_tables()
        self.completed_user_ids = []
        #self.refresh_completed_user_ids()


    def __del__(self):
        self.cursor.close()
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
    
    #def refresh_completed_user_ids(self):
        #if not os.path.exists(completed_user_ids_csv):
            #with open(completed_user_ids_csv, 'w') as f:
                #pass
        #with open(completed_user_ids_csv, 'r') as f:
            #self.completed_user_ids = f.read().splitlines()
    

    #def commit(self, force = False):
        #if force:
            #self.conn.commit()
            #self.commit_counter = 0
        #else:
            #self.commit_counter += 1
            #if self.commit_counter >= 10:
                #self.conn.commit()
                #self.commit_counter = 0

    #def close(self):
        ##self.cursor.execute('''delete from tracks where artist is null;''')
        #self.commit(force=True)
        #self.cursor.close()
        #self.conn.close()

    def construct_track_from_spotify(self, track_id: str) -> Track:
        sp_track = self.sp.track(track_id)
        return Track.from_spotify(track_id, sp_track)

    def construct_album_from_spotify(self, album_id: str) -> Album:
        sp_album = self.sp.album(album_id)
        return Album(sp_album_details=sp_album)

    def construct_artist_from_spotify(self, artist_id: str) -> Artist:
        sp_artist = self.sp.artist(artist_id)
        artist = Artist(sp_artist_details=sp_artist)
        artist.set_genres(sp_artist['genres'])
        offset = 0
        while True:
            sp_artist_albums = self.sp.artist_albums(artist_id, include_groups='album,single', limit=50, offset=offset)
            for sp_album in sp_artist_albums['items']:
                album_id = sp_album['id']
                album = self.construct_album_from_spotify(album_id)
                artist.add_album(album)
            if len(sp_artist_albums['items']) == 50:
                offset += 50
            else:
                break
        return artist
        




    def construct_playlist(self, playlist_id, sp_playlist_details=None, include_details=True):
        if include_details:
            if sp_playlist_details is None:
                sp_playlist_details = self.sp.playlist(playlist_id)
        else:
            sp_playlist_details = None

        sp_playlist_tracks = self.sp.playlist_tracks(playlist_id)
        return Playlist(playlist_id, sp_playlist_tracks, sp_playlist_details)


    def obtain_user_playlists(self, user_id: str) -> dict[str, Playlist]:
        sp_playlists = self.sp.user_playlists(user_id)
        playlists = {}
        for sp_playlist_details in sp_playlists['items']:
            playlist_id = sp_playlist_details['id']
            playlists[playlist_id] = self.construct_playlist(playlist_id, sp_playlist_details)
        return playlists
    
    def construct_user(self, user_id):
        return User(user_id, self.obtain_user_playlists(user_id))





    #def write_user_to_db(self, user_id):
        #if user_id in self.completed_user_ids:
            #if verbose: print(f"user {user_id} already processed, skipping...")
            #return
        #if verbose: print(f"processing user {user_id}...")
        #playlist_ids = self.obtain_user_playlist_ids(user_id)

        #playlists = self.sp.user_playlists(user_id)
        #playlist_json = {}
        #for playlist in playlists['items']:
            #playlist_id = playlist['id']

        #playlist_json = {}
        #for playlist_id in playlist_ids:
            ##tracks = self._retry_on_429(self.sp.playlist_tracks, playlist_id)
            #sp_playlist_tracks = self.sp.playlist_tracks(playlist_id)
            #playlist_json[playlist_id] = [playlist, sp_playlist_tracks['items']]
        #if verbose: print(f"found {len(playlist_json)} playlists:")
        #for playlist_id, (sp_playlist_details, sp_playlist_tracks) in playlist_json.items():
            ##tracks_json = convert_spotify_playlist(tracks, playlist_id)
            ## -----------
            ## changed to:
            #tracks_json = Playlist(playlist_id, sp_playlist_tracks, sp_playlist_details)
            ## -----------

            #self.write_playlist_to_db(playlist_id, playlist, tracks_json)
            #self.commit(force=True)
        #with open(completed_user_ids_csv, 'a') as file:
            #file.write(f"{user_id}\n")
        #self.completed_user_ids.append(user_id)
        #if verbose: print(f"user {user_id} processed successfully")

