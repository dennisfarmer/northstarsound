#!/usr/bin/env python

class Track():
    def __init__(self, track_id: str, name: str = None, artist_name: str = None, artist_id: str = None, album_name: str = None, album_id:str=None, popularity:float=None, video_id: str = None, audio_path: str = None, embedding: list[float] = None):
        self.id = track_id
        self.name = name
        self.artist = ArtistInfo(artist_name, artist_id)
        self.album_name = album_name
        self.album_id = album_id
        self.popularity = popularity
        self.video_id = video_id
        self.audio_path = audio_path
        self.embedding = embedding

    @staticmethod
    def from_spotify(track_id, sp_track, album=None):
        # ensure we pass by value (copy the reference to a new object)
        track = sp_track.copy()
        if "track" in track:
            track = track["track"]
        assert track_id == track["id"]
        if "popularity" not in track:
            track["popularity"] = None
        if album is None:
            album_name = track["album"]
            album_id = track["album"]["id"]
        else:
            album_name = album["name"]
            album_id = album["id"]
        return Track(
            track_id=track_id,
            name=track["name"],
            artist_name=track["artists"][0]["name"],
            artist_id=track["artists"][0]["id"],
            album_name=album_name,
            album_id=album_id,
            popularity=track["popularity"]
        )

    def get_track_info(self):
        pass
    def __getitem__(self, key):
        return getattr(self, key)
    def __str__(self):
        return f"{self.name} by {self.artist.name} - {self.id}"
    def __repr__(self):
        return f"Track(id={self.id}, name={self.name}, artist={self.artist}, album={self.album_name}, album_id={self.album_id}, popularity={self.popularity}, video_id={self.video_id}, audio_path={self.audio_path}, embedding={self.embedding})"


class Playlist():
    def __init__(self, playlist_id, sp_playlist_tracks, sp_playlist_details=None):
        if sp_playlist_details is not None:
            assert playlist_id == sp_playlist_details["id"]
        self.id = playlist_id
        if sp_playlist_details is not None:
            self.name = sp_playlist_details['name']
            self.description = sp_playlist_details['description']
            self.owner_id = sp_playlist_details['owner']['id']
            self.owner_name = sp_playlist_details['owner']['display_name']
            self.total_tracks = sp_playlist_details['tracks']['total']
        else:
            self.name = None
            self.description = None
            self.owner_id = None
            self.owner_name = None
            self.total_tracks = None

        self.tracks = {}
        for track in sp_playlist_tracks['items']:
            try: 
                track_id = track['track']['id']
            except TypeError:
                print("\t\tTrack has been removed from Spotify, skipping...")
                continue
            self.tracks[track_id] = Track.from_spotify(track_id, track)

    @staticmethod
    def url_to_id(sp_playlist_url: str) -> str:
        import re
        match = re.search(r'playlist/([a-zA-Z0-9]+)', sp_playlist_url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid playlist URL")

class User():
    def __init__(self, user_id: str, playlists: dict[str, Playlist]):
        self.id = user_id
        self.playlists = playlists
        #self.playlists = {}
        #for sp_playlist_details in sp_user_playlists['items']:
            #playlist_id = sp_playlist_details['id']
            #self.playlists[playlist_id] = Playlist(playlist_id, sp_playlist_details)

class Album():
    def __init__(self, album_name: str = None, album_id: str = None, artist_name: str = None, artist_id: str = None, album_type: str = None, release_date: str = None, sp_album_details: dict = None, tracks: dict[str, Track] = None):
        if sp_album_details is None:
            self.name = album_name
            self.id = album_id
            self.artist = ArtistInfo(artist_name, artist_id)
            self.release_date = release_date
            self.album_type = album_type
            self.tracks = tracks
        elif sp_album_details is not None:
            self.name = sp_album_details["name"]
            self.id = sp_album_details['id']
            self.artist = ArtistInfo(sp_album_details["artists"][0]["name"], sp_album_details["artists"][0]["id"])
            self.release_date = sp_album_details["release_date"]
            self.album_type = sp_album_details["album_type"]
            self.tracks = {}
            for track in sp_album_details['tracks']['items']:
                track_id = track['id']
                self.tracks[track_id] = Track.from_spotify(track_id, track, album={"name": self.name, "id": self.id})

    def __str__(self):
        s = f"{self.name} by {self.artist} ({self.release_date} - {self.album_type}) - {self.id}"
        for track in self.tracks.values():
            s += f"\n\t\t{track}"
        return s
    def __repr__(self):
        return f"Album(id={self.id}, name={self.name}, artist={self.artist}, release_date={self.release_date}, album_type={self.album_type}, total_tracks={self.total_tracks})"



class ArtistInfo():
    def __init__(self, artist_name: str = None, artist_id: str = None, sp_artist_details: dict = None):
        self.genres = None
        if sp_artist_details is None:
            self.name = artist_name
            self.id = artist_id
        if sp_artist_details is not None:
            self.id = sp_artist_details['id']
            self.name = sp_artist_details["name"]

    def __str__(self):
        return self.name
    def __repr__(self):
        return f"Artist(id={self.id}, name={self.name})"
    def set_genres(self, genres: list[str]):
        self.genres = genres

    
class Artist():
    def __init__(self, artist_name: str = None, artist_id: str = None, sp_artist_details: dict = None):
        self.albums = {}
        self.artist_info = ArtistInfo(artist_name, artist_id, sp_artist_details)

    def set_genres(self, genres: list[str]):
        self.artist_info.set_genres(genres)

    def add_album(self, album: Album):
        self.albums[album.id] = album

    def __str__(self):
        s = f"{self.artist_info.name} - {self.artist_info.id}"
        for album in self.albums.values():
            s += f"\n\t{album}"
        return s



from .data_pipeline import *
from .db import *
from .env import *
from .spotify import *
from .youtube import *