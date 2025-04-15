#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import essentia
import essentia.standard as es
import numpy as np
import os
import subprocess

#import logging

#logger = logging.getLogger(__name__)
#logger.propagate = False # don't propagate messages to root logger

def compute_audio_embedding(video_id, audio_path):
    MUSICNN_SR = 16000
    try:
        audio = es.MonoLoader(filename=audio_path, sampleRate=MUSICNN_SR)()
        musicnn_emb = es.TensorflowPredictMusiCNN(graphFilename='msd-musicnn-1.pb', output='model/dense_1/BiasAdd')(audio)
    except:
        return video_id, None
    try:
        mean_emb = np.mean(musicnn_emb, axis=0)
        mean_emb = mean_emb[np.newaxis, :]
    except Exception as e:
        print(video_id, e)
        return video_id, None
    return video_id, mean_emb[0]

def download_audio(video_id: str, subdir: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"

    yt_dlp = os.path.join(os.path.dirname(__file__), 'yt-dlp_linux')
    ffmpeg = os.path.join(os.path.dirname(__file__), 'ffmpeg')

    os.makedirs(subdir, exist_ok=True)
    webm_path = os.path.join(subdir, f"{video_id}.webm")
    mp3_path = os.path.join(subdir, f"{video_id}.mp3")
    print(url)
    #yt = [yt_dlp, '--extract-audio', '--audio-format', 'mp3', '--quiet', 
          #'--no-warnings', '--progress', '--ffmpeg-location', ffmpeg, '--output', audio_path, url]
    yt = [yt_dlp, '--extract-audio', '--audio-format', 'mp3',
          '--progress', '--ffmpeg-location', ffmpeg, '--output', webm_path, url]

    # fails at conversion step; something about expecting string/bytes but getting None (??)
    yt_output = subprocess.run(yt, capture_output=True, text=True)

    # workaround: manually convert to mp3
    ff_output = subprocess.run([ffmpeg, "-i", webm_path, "-vn", "-ab", "128k", "-ar", "44100", "-y", mp3_path], capture_output=True, text=True)

    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"The audio file wasn't actually downloaded/converted from Youtube properly (Youtube might think you're a bot / need to verify age / etc., or you might be using an incompatable ffmpeg binary - see Makefile for download source) -- {yt_output}, {ff_output}")
    try:
        os.remove(webm_path)
    except:
        pass
    return mp3_path

def lambda_handler(event, context):
    """
    AWS Lambda function handler to compute audio embeddings.
    """
    tmp_dir = "/tmp/audio_files"
    os.makedirs(tmp_dir, exist_ok=True)
    #return {
        #'statusCode': 200,
        #'body': {k: v for k, v in event.items()}
    #}
    try:
        video_id = event['video_id']
        if video_id == "test":
            test_file_path = os.path.join(os.path.dirname(__file__), 'test.mp3')
            video_id, embedding = compute_audio_embedding(video_id, test_file_path)
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
        else:
            try:
                audio_path = download_audio(video_id, tmp_dir)
            except FileNotFoundError:
                # try one more time to potentially get around obviously false bot accusations
                audio_path = download_audio(video_id, tmp_dir)

            video_id, embedding = compute_audio_embedding(video_id, audio_path)
    except KeyError:
        return {
            'statusCode': 400,
            'body': "Missing 'video_id' in query parameters."
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
    if (video_id != "test") and os.path.exists(audio_path):
        os.remove(audio_path)
    if embedding is not None:
        return {
            'statusCode': 200,
            'body': {
                'video_id': video_id,
                'embedding': embedding.tolist()
            }
        }
    else:
        return {
            'statusCode': 404,
            'body': f"Failed to compute embedding for video ID: {video_id}."
        }
