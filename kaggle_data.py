#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ast
import pandas as pd

def download_data() -> None:
    import kagglehub
    datadir = os.path.join(os.path.dirname(__file__), "data/features")

    path = kagglehub.dataset_download("fcpercival/160k-spotify-songs-sorted", path='data.csv')
    try:
        os.symlink(path, os.path.join(datadir, os.path.basename(path)))
    except FileExistsError:
        pass

    path = kagglehub.dataset_download("rodolfofigueroa/spotify-12m-songs", path='tracks_features.csv')
    try:
        os.symlink(path, os.path.join(datadir, os.path.basename(path)))
    except FileExistsError:
        pass

    #path = kagglehub.dataset_download("tomigelo/spotify-audio-features", path='SpotifyAudioFeaturesNov2018.csv')
    #try:
        #os.symlink(path, os.path.join(datadir, os.path.basename(path)))
    #except FileExistsError:
        #pass

    path = kagglehub.dataset_download("tomigelo/spotify-audio-features", path='SpotifyAudioFeaturesApril2019.csv')
    try:
        os.symlink(path, os.path.join(datadir, os.path.basename(path)))
    except FileExistsError:
        pass

    print("Path to dataset files:", datadir)

def load_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # try download_data() if you don't have the data files
    datadir = os.path.join(os.path.dirname(__file__), "data/features")
    spotify_160k = pd.read_csv(os.path.join(datadir, "data.csv"))
    spotify_1m = pd.read_csv(os.path.join(datadir, "tracks_features.csv"))
    #spotify_nov2018 = pd.read_csv(os.path.join(datadir, "SpotifyAudioFeaturesNov2018.csv"))
    spotify_april2019 = pd.read_csv(os.path.join(datadir, "SpotifyAudioFeaturesApril2019.csv"))

    # data transformations for consistency
    spotify_april2019["artist_name"] = spotify_april2019["artist_name"].apply(lambda x: [x])
    spotify_april2019.rename(columns={'track_id': 'id', "artist_name": "artists", "track_name": "name"}, inplace=True)

    # not keeping release date
    columns_of_interest = ["id", "name", "artists", "duration_ms", 
                        "danceability", 
                        "energy", "key", "loudness", "mode", "speechiness", 
                        "acousticness", "instrumentalness", "liveness", 
                        "valence", "tempo"]

    spotify_160k = spotify_160k[columns_of_interest]
    spotify_1m = spotify_1m[columns_of_interest]
    spotify_april2019 = spotify_april2019[columns_of_interest]


    # Concatenate the dataframes
    combined_df = pd.concat([spotify_160k, spotify_1m, spotify_april2019], ignore_index=True)

    # Drop duplicates based on the 'id' column
    combined_df.drop_duplicates(subset='id', keep="first", inplace=True)
    def convert_to_single_artist(x):
        try:
            return ast.literal_eval(x)[0]
        except ValueError:
            return x[0]
    combined_df["artists"] = combined_df["artists"].apply(convert_to_single_artist)
    combined_df.rename(columns={"artists": "artist"}, inplace=True)

    return combined_df