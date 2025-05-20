import sqlite3
from sqlite3 import Connection, Cursor
from .env import musicdb, audio_storage_root
from . import Track, Playlist, User


def lookup_video_id(track_id: str, cursor):
    video_id = cursor.execute('''
    select video_id from audio_files where track_id = ?
                    ''', (track_id,)).fetchone()
    if video_id is None:
        return None
    else:
        return video_id[0]


def lookup_audio_embedding(video_id: str|None = None, track_id: str|None = None, cursor = None):
    if (video_id is None) and (track_id is not None):
        video_id = lookup_video_id(track_id, cursor)
    if (video_id is None) and (track_id is None):
        return None
    embedding = cursor.execute('''
    select * from audio_embeddings where video_id = ?
                            ''', (video_id,)).fetchone()
    if embedding is None:
        return None
    else:
        return embedding[1:]

def lookup_audio_path(track_id: str, cursor = None) -> str | None:
    cursor.execute("SELECT audio_path FROM audio_files WHERE track_id = ?", (track_id,))
    audio_path = cursor.fetchone()
    if audio_path:
        return audio_path[0]
    else:
        return None

def lookup_track_details(track_id: str, cursor) -> Track | None:
    cursor.execute("SELECT name, artist, album_id, popularity FROM tracks WHERE id = ?", (track_id,))
    track_details = cursor.fetchone()
    if track_details is not None:
        album_info = cursor.execute("SELECT name FROM albums WHERE id = ?", (track_details[2],)).fetchone()
        print(album_info)
        return Track(
            name = track_details[0],
            artist = track_details[1],
            album_id = track_details[2],
            album_name = album_info[0] if album_info is not None else None,
            popularity = track_details[3]
        )
    return None


def lookup_track(track_id: str, cursor: Cursor) -> Track | None:
    track = lookup_track_details(track_id, cursor)
    if track is not None:
        audio_path = lookup_audio_path(track_id, cursor)
        video_id = lookup_video_id(track_id, cursor)
        embedding = lookup_audio_embedding(video_id, cursor)
        track["audio_path"] = audio_path
        track["video_id"] = video_id
        track["embedding"] = embedding
        return track
    return None

def write_album_to_db(album_id: str, album_name: str, artist_id: str, artist_name: str, artist_genres: list[str], cursor: Cursor):
    cursor.execute('''
    INSERT OR IGNORE INTO albums (id, name, artist_id, artist_name)
    VALUES (?, ?, ?, ?)
    ''', (album_id, album_name, artist_id, artist_name))
    cursor.execute('''
    INSERT OR IGNORE INTO artists (id, name)
    VALUES (?, ?)
    ''', (artist_id, artist_name))
    for genre in artist_genres:
        cursor.execute('''
        INSERT OR IGNORE INTO artist_genres (artist_id, genre)
        VALUES (?, ?)
        ''', (artist_id, genre))

def write_track_to_db(track: Track, cursor: Cursor):
    if (track.id is not None) and (track.name is not None) and (track.artist is not None) and (track.album_name is not None) and (track.album_id is not None) and (track.popularity is not None):
        cursor.execute('''
        INSERT OR IGNORE INTO tracks (id, name, album_id, artist, popularity)
        VALUES (?, ?, ?, ?, ?)
        ''', (track.id, track.name, track.album_id, track.artist, track.popularity))
        cursor.execute('''
        INSERT OR IGNORE INTO albums (id, name, artist_id, artist_name)
        VALUES (?, ?, ?, ?)
        ''', (track.album_id, track.album_name, None, track.artist))
    if (track.id is not None) and (track.video_id is not None) and (track.embedding is not None):
        # note: audio_path will be None if not running locally
        # this should be UPDATE OR IGNORE when running locally
        cursor.execute('''
        INSERT OR IGNORE INTO audio_files (track_id, video_id, audio_path)
        VALUES (?, ?, ?)
        ''', (track.id, track.video_id, track.audio_path))
        write_embedding_to_db(track.video_id, track.embedding, cursor)

def write_playlist_to_db(playlist: Playlist, cursor: Cursor):
    cursor.execute('''
    INSERT OR IGNORE INTO playlists (id, name, description, owner_id, owner_name, total_tracks)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (playlist.id, playlist.name, playlist.description, playlist.owner_id, playlist.owner_name, playlist.total_tracks))

    for track_id, track in playlist.tracks.items():
        write_track_to_db(track, cursor)

        cursor.execute('''
        INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id)
        VALUES (?, ?)
        ''', (playlist.id, track_id))
        cursor.commit()

def write_user_to_db(user: User, cursor: Cursor):
    # check if in completed_user_ids before calling this function
    for playlist_id, playlist in user.playlists.items():
        write_playlist_to_db(playlist, cursor)

def write_audio_to_db(track: Track, cursor: Cursor):
    if track.audio_path is None:
        print(f"track {track.id} has no video_id...")
    cursor.execute('''
    INSERT INTO audio_files (track_id, video_id, audio_path)
    VALUES (?, ?, ?)
    ON CONFLICT(track_id) DO UPDATE SET
    track_id = excluded.track_id,
    video_id = excluded.video_id,
    audio_path = excluded.audio_path;
    ''', (track.id, track.video_id, track.audio_path))

def write_embedding_to_db(video_id, embedding, cursor: Cursor):
    placeholders = ", ".join(["?"] * 51)
    query = f"INSERT OR IGNORE INTO audio_embeddings VALUES ({placeholders})"
    cursor.execute(query, (video_id, *embedding.tolist()))  # Convert numpy array to list

def get_audio_embeddings_count() -> int:
    conn, cursor = connect_to_database()
    cursor.execute("SELECT COUNT(*) FROM audio_embeddings")
    count = cursor.fetchone()[0]
    conn.close()
    return int(count)

def get_all_tracks() -> list[Track]:
    conn, cursor = connect_to_database()
    cursor.execute("SELECT id, name, artist FROM tracks")
    tracks = cursor.fetchall()
    conn.close()
    return [Track(t[0], t[1], t[2]) for t in tracks]

def connect_to_database() -> tuple[Connection, Cursor]:
    conn = sqlite3.connect(musicdb)
    cursor = conn.cursor()
    return conn, cursor

def create_tables():
    conn, cursor = connect_to_database()
    with open('utils/queries/create_tables.sql', 'r') as sql_file:
        sql_script = sql_file.read()
        cursor.executescript(sql_script)

    conn.commit()
    conn.close()
