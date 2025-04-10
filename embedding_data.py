import essentia.standard as es
import numpy as np
MUSICNN_SR = 16000
def compute_audio_embedding(id_and_path):
    video_id = id_and_path[0]
    audio_path = id_and_path[1]
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
