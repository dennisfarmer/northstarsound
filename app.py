from playlist_data import SpotifyPlaylistProcessor, get_playlist_tracks, playlist_url_to_id
from recommender import get_music_recommendations
import sqlite3
from dotenv import dotenv_values
import spotipy
import os
import argparse
from tqdm import tqdm
import signal
import re
import streamlit as st
import pickle
#from threading import Thread


env = dotenv_values(".env")
verbose = env["VERBOSE"] == "True"

completed_user_ids_csv = env["COMPLETED_USER_IDS_CSV"]
playlist_db = env["PLAYLIST_DB"]


def main():
    st.title("Spotify Playlist Recommendations")

    with st.form("playlist_form"):
        playlist_url = st.text_input("Spotify Playlist URL", label_visibility="visible", value=None,
                                     placeholder="https://open.spotify.com/playlist/1bPcEafe3YHOssXSK8wZs8")
        model_selection = st.radio(
            "Model Selection",
            options = [
                "content",
                "hybrid",
                "collaborative"
            ],
            index=0,
            format_func = lambda x: {
                "content": "🤖🔊 :red[Content-based Filtering]",
                "hybrid": "👨‍💻 :rainbow[Hybrid Filtering]",
                "collaborative": "👨️👨‍🦱 :violet[Collaborative Filtering]"}[x],
            captions = [
                "Each track's audio is represented as a lower-dimensional\
                    numerical vector, and the model recommends the $k$ \
                    tracks closest to the interquartile mean of the playlist's track vectors (beep boop)",
                "Model combines both approaches to recommend the $k$ most similar tracks to your playlist, incorperating both machine learning and human information.",
                "Model predicts the $k$ most likely tracks to be added to your playlist, based on playlists of other users "
            ],
            help="Select the recommender system to use for generating recommendations.",
            )
        k = st.select_slider(
            "$k$: Number of recommendations to generate",
            options = [1,2,3,4,5,6,7,8,9,10],
            value=10,
        )
        submit_button = st.form_submit_button("Generate Recommendations", icon="🔊", type="secondary")

    if submit_button:
        if playlist_url is None:
            playlist_url = "https://open.spotify.com/playlist/1bPcEafe3YHOssXSK8wZs8"
        try:
            playlist_id = playlist_url_to_id(playlist_url)
        except ValueError:
            st.error("Please enter a valid Spotify playlist URL.")

        try:
            playlist_tracks = get_playlist_tracks(playlist_id)
            #with open("playlist_tracks.pkl", "rb") as f:
                #playlist_tracks = pickle.load(f)
            #with open("playlist_tracks.pkl", "wb") as f:
                #pickle.dump(playlist_tracks, f)

        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 400:
                st.error("Please enter a valid Spotify playlist URL.")
            else:
                st.error(f"An error occurred: {e}")

        recommendations, fig = get_music_recommendations(playlist_tracks, k, model_selection)

        col1, col2 = st.columns(2, vertical_alignment="top")
        with col1:
            st.header("Your Playlist")
            with st.container(height=500, border=True):
                for track in playlist_tracks:
                    track_url = f"https://open.spotify.com/track/{track['track_id']}"
                    with st.expander(
                        label=f"{track['title']} by {track['artist']}",
                        icon=":material/play_circle:",):

                        st.video(f"https://www.youtube.com/watch?v={track['video_id']}")
                        st.link_button(
                            label=f"Listen on Spotify",
                            url=track_url,
                            icon=":material/volume_up:",type="tertiary")

        with col2:
            st.header("Recommendations")
            with st.container(height=500, border=True):
                for track in recommendations:
                    track_url = f"https://open.spotify.com/track/{track['track_id']}"
                    with st.expander(
                        label=f"{track['title']} by {track['artist']}",
                        icon=":material/play_circle:",):

                        st.video(f"https://www.youtube.com/watch?v={track['video_id']}")
                        st.link_button(
                            label=f"Listen on Spotify",
                            url=track_url,
                            icon=":material/volume_up:",type="tertiary")
                    #icon=":material/volume_up:",) #"🔊"
                #st.write(f"{track['title']} by {track['artist']} from {track['album']}")
        #tab1, tab2 = st.tabs(["Kernel PCA Visualization", "alt"])
        #with tab1:
            # Use the Streamlit theme.
            # This is the default. So you can also omit the theme argument.
        st.plotly_chart(fig, theme="streamlit")#, use_container_width=True)
        #with tab2:
            # Use the native Plotly theme.
        #except Exception as e:
            #st.error(f"An error occurred: {e}")
main()
#if __name__ == "__main__":
    #main()




#if __name__ == '__main__':
    #playlist_url = "https://open.spotify.com/playlist/1bPcEafe3YHOssXSK8wZs8?si=0f1a2c3d4e5f6g7h8i9j0k"
    #playlist_id = playlist_url_to_id(playlist_url)
    #try:
        #playlist = get_playlist_tracks(playlist_id)
    #except spotipy.exceptions.SpotifyException as e:
        #if e.http_status == 400:
            #raise e
    #recommendations = get_music_recommendations(playlist_id)