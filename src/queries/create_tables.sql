CREATE TABLE IF NOT EXISTS playlists (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    owner_id TEXT,
    owner_name TEXT,
    total_tracks INTEGER
);

CREATE TABLE IF NOT EXISTS albums (
    id TEXT PRIMARY KEY,
    name TEXT,
    artist_id TEXT,
    artist_name TEXT
    release_date TEXT,
);

CREATE TABLE IF NOT EXISTS artists (
    id TEXT PRIMARY KEY,
    name TEXT,
    FOREIGN KEY (id) REFERENCES albums(artist_id)
);

CREATE TABLE IF NOT EXISTS artist_genres (
    artist_id TEXT,
    genre TEXT,
    PRIMARY KEY (artist_id, genre),
    FOREIGN KEY (artist_id) REFERENCES artists(id)
);

CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    name TEXT,
    album_id TEXT,
    artist TEXT,
    popularity INTEGER,
    FOREIGN KEY (album_id) REFERENCES albums(id)
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id TEXT,
    track_id TEXT,
    PRIMARY KEY (playlist_id, track_id),
    FOREIGN KEY (playlist_id) REFERENCES playlists(id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

CREATE TABLE IF NOT EXISTS audio_files (
    track_id TEXT PRIMARY KEY,
    video_id TEXT,
    audio_path TEXT,
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

CREATE TABLE audio_embeddings (
    video_id TEXT PRIMARY KEY,
    embedding_1 REAL,
    embedding_2 REAL,
    embedding_3 REAL,
    embedding_4 REAL,
    embedding_5 REAL,
    embedding_6 REAL,
    embedding_7 REAL,
    embedding_8 REAL,
    embedding_9 REAL,
    embedding_10 REAL,
    embedding_11 REAL,
    embedding_12 REAL,
    embedding_13 REAL,
    embedding_14 REAL,
    embedding_15 REAL,
    embedding_16 REAL,
    embedding_17 REAL,
    embedding_18 REAL,
    embedding_19 REAL,
    embedding_20 REAL,
    embedding_21 REAL,
    embedding_22 REAL,
    embedding_23 REAL,
    embedding_24 REAL,
    embedding_25 REAL,
    embedding_26 REAL,
    embedding_27 REAL,
    embedding_28 REAL,
    embedding_29 REAL,
    embedding_30 REAL,
    embedding_31 REAL,
    embedding_32 REAL,
    embedding_33 REAL,
    embedding_34 REAL,
    embedding_35 REAL,
    embedding_36 REAL,
    embedding_37 REAL,
    embedding_38 REAL,
    embedding_39 REAL,
    embedding_40 REAL,
    embedding_41 REAL,
    embedding_42 REAL,
    embedding_43 REAL,
    embedding_44 REAL,
    embedding_45 REAL,
    embedding_46 REAL,
    embedding_47 REAL,
    embedding_48 REAL,
    embedding_49 REAL,
    embedding_50 REAL,
    FOREIGN KEY (video_id) REFERENCES audio_files(video_id)
);