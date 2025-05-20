from add_music import SpotifyPlaylistProcessor, get_playlist_tracks, playlist_url_to_id, get_audio_embeddings_count, search_yt_for_video_id
from recommender import get_music_recommendations, NoValidTracksError, EmptyPlaylistError
import sqlite3
import spotipy
import os
import argparse
from tqdm import tqdm
import signal
import re
import streamlit as st
import numpy as np
import requests
import pickle
import platform
from dotenv import dotenv_values
from src import Playlist
#from threading import Thread


if platform.system() == "Darwin":
    env = dotenv_values(".env")
elif platform.system() == "Linux":
    env = os.environ
else:
    raise Exception("Unsupported operating system. Cannot load environment variables.")

verbose = env["VERBOSE"] == "True"
read_only = env["READ_ONLY"] == "True"

completed_user_ids_csv = env["COMPLETED_USER_IDS_CSV"]
playlist_db = env["PLAYLIST_DB"]
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

model_format_func = lambda x: {
                "content": "🤖🔊 :red[Content-based Filtering]",
                "hybrid": "👨‍💻 :rainbow[Hybrid Filtering]",
                "collaborative": "👨️👨‍🦱 :violet[Collaborative Filtering]"}[x]

def display_tracks(tracks, label=None, height=500, emoji=None):
    with st.container(height=height, border=True):
        with st.expander(
            label=model_format_func(label),
            icon=":material/play_circle:"
            ):
            st.write(f"**{len(tracks)} tracks**")
        for track in tracks:
            track_url = f"https://open.spotify.com/track/{track['track_id']}"
            with st.expander(
                label=f"{track['name']} by {track['artist']}",
                icon=emoji if emoji is not None else ":material/play_circle:"
                ):

                if track["video_id"] is not None:
                    st.video(f"https://www.youtube.com/watch?v={track['video_id']}")
                else:
                    st.write("No Youtube video url available")
                st.link_button(
                    label=f"Listen on Spotify",
                    url=track_url,
                    icon=":material/volume_up:",type="tertiary")

def main():
    st.title("Spotify Playlist Recommendations")
    with st.form("playlist_form"):
        playlist_url = st.text_input("Spotify Playlist URL\n\n:material/share: Share :material/arrow_right: :material/content_copy: Copy link to playlist", label_visibility="visible", value=None,
                                     placeholder="https://open.spotify.com/playlist/1bPcEafe3YHOssXSK8wZs8")
        model_selection = st.radio(
            "Model Selection",
            options = [
                "content",
                "hybrid",
                "collaborative"
            ],
            index=0,
            format_func = model_format_func,
            captions = [
                "Each track's audio is represented as a lower-dimensional\
                    numerical vector, and the model recommends the $k$ \
                    tracks closest to the interquartile mean of the playlist's track vectors (beep boop)",
                "Model combines both approaches to recommend the $k$ most similar tracks to your playlist, incorperating both machine learning and human information.",
                "Model predicts the $k$ most likely tracks to be added to your playlist, based on playlists of other users "
            ],
            help="Select the recommender system to use for generating recommendations.",
            )
        k_options = np.arange(k_min, k_max + 1).tolist()
        k = st.select_slider(
            "$k$: Number of recommendations to generate",
            options = k_options,
            value = max(k_options),
        )
        submit_button = st.form_submit_button("Generate Recommendations", icon="🔊", type="secondary")

    if submit_button:
        if playlist_url is None:
            playlist_url = "https://open.spotify.com/playlist/1bPcEafe3YHOssXSK8wZs8"
        try:
            playlist_id = Playlist.url_to_id(playlist_url)
        except ValueError:
            st.error("Please enter a valid Spotify playlist URL.")
            return

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

        try:
            recommendations, figs = get_music_recommendations(playlist_tracks, k, model_selection)
        except EmptyPlaylistError:
            st.error("Your playlist is empty. Please add some tracks to your playlist and try again.")
            return
        except NoValidTracksError:
            st.error(f"Internal Error: Could not obtain audio representations for any of the tracks in the playlist.\n\nTechnical Details: Youtube blocks the IP address of my AWS Lambda instance. Instead of downloading the audios from the Lambda instance, I'll have to either implement downloading audios inside of Streamlit and uploading them to an S3 bucket for AWS Lambda to access, or implement compressing/cropping the audios to be less than the 4 MB Lambda upload limit and passing them to AWS Lambda directly.\n\nPlease try again with a different playlist. There's a pre-computed database of {format(get_audio_embeddings_count(), ',')} different audio representations that might contain other tracks of interest.")
            return
        

        col1, col2 = st.columns(2, vertical_alignment="top")
        with col1:
            st.header("Your Playlist")
            with st.container(height=500, border=True):
                for track in playlist_tracks:
                    track_url = f"https://open.spotify.com/track/{track['track_id']}"
                    embedding_exists = track["embedding"] is not None
                    if (not embedding_exists) and model_selection != "collaborative":
                        label=f"~~{track['name']} by {track['artist']}~~"
                        icon=":material/volume_off:"
                    else:
                        label=f"{track['name']} by {track['artist']}"
                        icon=":material/volume_up:"
                    with st.expander(
                        label=label,
                        icon=icon):

                        if track["video_id"] is not None:
                            st.video(f"https://www.youtube.com/watch?v={track['video_id']}")
                        else:
                            st.write("No Youtube video url available")
                        #else:
                            #if st.button("Play Video", key=track["track_id"]):
                                #try:
                                    #v_id = search_yt_for_video_id(track["name"], track["artist"])
                                #except requests.exceptions.ConnectionError as e:
                                    #v_id = None
                                #if v_id is not None:
                                    #st.video(f"https://www.youtube.com/watch?v={v_id}")
                        st.link_button(
                            label=f"Listen on Spotify",
                            url=track_url,
                            icon=":material/volume_up:",type="tertiary")
                        if (not embedding_exists) and model_selection != "collaborative":
                            st.error("Could not obtain track representation")

        with col2:
            st.header("Recommendations")
            model_emoji = {
                "content": "🤖",
                "hybrid": "👨‍💻",
                "collaborative": "👨️"
            }
            if recommendations is None:
                st.error("Internal Error: None of the tracks in your playlist exist in the set of tracks that the model uses for recommendations. Please try again with a different playlist.")
            elif model_selection == "hybrid":

                num_hybrid, num_collaborative, num_content = [
                    len(recommendations[t]) 
                    for t in ["hybrid", "collaborative", "content"]
                ]
                total_tracks = num_hybrid + num_collaborative + num_content

                if total_tracks > 0:
                    #total_height = 1500 if num_hybrid > 0 else 1000
                    height_hybrid = 500#int(total_height * (num_hybrid / total_tracks))
                    height_content = 500#int(total_height * (num_content / total_tracks))
                    height_collaborative = 500# total_height - height_hybrid - height_content  # Ensure total height is 500

                    if num_hybrid > 0:
                        display_tracks(recommendations["hybrid"], label="hybrid", height=height_hybrid, emoji=model_emoji["hybrid"])

                    if num_content > 0:
                        display_tracks(recommendations["content"], label="content", height=height_content, emoji=model_emoji["content"])

                    if num_collaborative > 0:
                        display_tracks(recommendations["collaborative"], label="collaborative", height=height_collaborative, emoji=model_emoji["collaborative"])

            else:
                display_tracks(recommendations[model_selection], label=model_selection, height=500, emoji=model_emoji[model_selection])
        if model_selection == "hybrid":
            # content-based visualization
            fig = figs["content"]
            if fig is not None:
                st.plotly_chart(fig, theme="streamlit")
            # collaborative visualization
            fig = figs["collaborative"]
            if fig is not None:
                st.plotly_chart(fig, theme="streamlit")
        else:
            fig = figs[model_selection]
            if fig is not None:
                st.plotly_chart(fig, theme="streamlit")#, use_container_width=True)


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