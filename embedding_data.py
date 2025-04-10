import essentia.standard as es
import numpy as np
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
