#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import essentia
import essentia.standard as es
import numpy as np
import os
import subprocess

import logging

logger = logging.getLogger(__name__)
logger.propagate = False # don't propagate messages to root logger

def compute_audio_embedding(audio_path):
    MUSICNN_SR = 16000
    try:
        audio = es.MonoLoader(filename=audio_path, sampleRate=MUSICNN_SR)()
        musicnn_emb = es.TensorflowPredictMusiCNN(graphFilename='msd-musicnn-1.pb', output='model/dense_1/BiasAdd')(audio)
    except:
        return None
    try:
        mean_emb = np.mean(musicnn_emb, axis=0)
        mean_emb = mean_emb[np.newaxis, :]
    except Exception as e:
        logger.error(e)
        return None
    return mean_emb[0]


def download_audio(video_id: str, ngrok_path) -> str:
    # todo: send request to app hosted on flask_ngrok
    pass

#def download_audio(video_id: str, subdir: str, cookies_path: str) -> str:
    #url = f"https://www.youtube.com/watch?v={video_id}"

    #yt_dlp = os.path.join(os.path.dirname(__file__), 'yt-dlp_linux')
    #ffmpeg = os.path.join(os.path.dirname(__file__), 'ffmpeg')

    #os.makedirs(subdir, exist_ok=True)
    #webm_path = os.path.join(subdir, f"{video_id}.webm")
    #mp4_path = os.path.join(subdir, f"{video_id}.mp4")
    #mp3_path = os.path.join(subdir, f"{video_id}.mp3")
    #print(url)
    ##yt = [yt_dlp, '--extract-audio', '--audio-format', 'mp3', '--quiet', 
          ##'--no-warnings', '--progress', '--ffmpeg-location', ffmpeg, '--output', audio_path, url]
    #yt = [yt_dlp, '--extract-audio', '--audio-format', 'mp3',
          #'--progress', '--ffmpeg-location', ffmpeg, 
          #'--cookies-from-browser', 'chrome', '--cookies', cookies_path, 
          #'--output', webm_path, url]

    ## fails at conversion step; something about expecting string/bytes but getting None (??)
    #yt_output = subprocess.run(yt, capture_output=True, text=True)
    #logger.info(yt_output)
    #print("yt_output:")
    #print(yt_output)

    ## workaround: manually convert to mp3
    #ff_output = subprocess.run([ffmpeg, "-i", webm_path, "-vn", "-ab", "128k", "-ar", "44100", "-y", mp3_path], capture_output=True, text=True)
    #logger.info(ff_output)
    #print("ff_output:")
    #print(ff_output)

    #if not os.path.exists(mp3_path):
        #raise FileNotFoundError(f"The audio file wasn't actually downloaded/converted from Youtube properly (Youtube might think you're a bot / need to verify age / etc., or you might be using an incompatable ffmpeg binary - see Makefile for download source) -- {yt_output}, {ff_output}")

    #for f in [mp4_path, webm_path]:
        #if os.path.exists(f):
            #os.remove(f)
    #return mp3_path
    

def lambda_handler_test(video_id):
    test_file_path = os.path.join(os.path.dirname(__file__), 'test.mp3')
    embedding = compute_audio_embedding(test_file_path)
    return {
        'statusCode': 200,
        'body': {
            'video_id': video_id,
            'embedding': embedding.tolist(),
            'numpy_version': str(np.__version__),
            'essentia_version': str(essentia.__version__),
            'python_version': str(os.sys.version),
            'operating_system': str(os.uname()),
        }
    }

def lambda_handler(event, context):
    """
    AWS Lambda function handler to compute audio embeddings for given video IDs.
    This function processes an incoming event to compute audio embeddings for one or more video IDs.
    The event must contain either a 'video_id' (single video ID) or 'video_ids' (list of video IDs).
    If the value of 'video_id' or the first element of 'video_ids' is "test", a test handler 
    (`lambda_handler_test`) is executed instead of computing embeddings.
    Parameters:
        event (dict): The input event containing the following keys:
            - 'video_id' (str, optional): A single video ID to process.
            - 'video_ids' (list of str, optional): A list of video IDs to process.
        context (object): AWS Lambda context object (not used in this function).
    Returns:
        dict: A response object with the following structure:
            - 'statusCode' (int): HTTP status code indicating the result of the operation.
            - 'results' (dict, optional): A dictionary mapping video IDs to their computed embeddings 
              (only present if embeddings are successfully computed).
            - 'body' (str, optional): An error message or additional information (only present in case of errors).
    Raises:
        KeyError: If neither 'video_id' nor 'video_ids' is found in the event.
        Exception: For any other unexpected errors during processing.
    """
    #if "cookies" not in event:
        #return {
            #'statusCode': 400,
            #'body': "'cookies' not found in query parameters."
        #}
    tmp_dir = "/tmp/audio_files"
    os.makedirs(tmp_dir, exist_ok=True)
    cookies_path = os.path.join(tmp_dir, "cookies.txt")
    #with open(cookies_path, "w") as f:
        #f.write(event["cookies"])
    #return {
        #'statusCode': 200,
        #'body': {k: v for k, v in event.items()}
    #}
    try:
        if 'video_id' in event:
            video_ids = [event['video_id']]
        else:
            video_ids = event['video_ids']

        if video_ids[0] == "test":
            return lambda_handler_test(video_ids[0])
        else:
            results = {}
            body = {}
            for video_id in video_ids:
                
                try:
                    audio_path = download_audio(video_id, tmp_dir, cookies_path)
                except FileNotFoundError:
                    # try one more time to potentially get around obviously false bot accusations
                    #try:
                        #audio_path = download_audio(video_id, tmp_dir, cookies_path)
                    #except FileNotFoundError:
                    results[video_id] = None
                    body[video_id] = "failed: yt-dlp error (see logs)"
                    continue
                embedding = compute_audio_embedding(audio_path).tolist()
                results[video_id] = embedding
                body[video_id] = "success"
                if os.path.exists(audio_path):
                    os.remove(audio_path)

            if os.path.exists(cookies_path):
                os.remove(cookies_path)
            success = True
            for video_id in video_ids:
                if results[video_id] is None:
                    success = False
                    break
            return {
                'statusCode': 200 if success else 500,
                'results': results,
                'body': body
            }
    except KeyError:
        return {
            'statusCode': 400,
            'body': "'video_id' or 'video_ids' not found in query parameters."
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
