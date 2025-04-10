
from dotenv import dotenv_values
import sqlite3
from sklearn.decomposition import KernelPCA
from sklearn.metrics.pairwise import euclidean_distances
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.decomposition import KernelPCA
import plotly.express as px
import plotly.graph_objects as go
from typing import Any

env = dotenv_values(".env")
verbose = env["VERBOSE"] == "True"
playlist_db = env["PLAYLIST_DB"]



def content_based_filtering(playlist_tracks, k) -> list[dict]:
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()

    all_embeddings = {row[0]: np.array(row[1:]) for row in 
                      cursor.execute("select * from audio_embeddings;")
                      }

    # "most" means all tracks except for the ones playlist_tracks
    # don't want to recommend tracks already in the playlist
    most_ids = []
    most_embeddings = []
    playlist_video_ids = [track["video_id"] for track in playlist_tracks]
    for video_id, embedding in all_embeddings.items():
        if video_id not in playlist_video_ids:
            most_ids.append(video_id)
            most_embeddings.append(embedding)

    # Extract embeddings of playlist tracks
    playlist_embeddings = np.array([track["embedding"] for track in playlist_tracks])


    proportiontocut = 0.25
    kpca = KernelPCA(n_components=3, kernel='rbf', gamma=0.02)
    #kpca = KernelPCA(n_components=3, kernel='rbf', gamma=0.005)
    #kpca = KernelPCA(n_components=3, kernel='rbf', gamma=0.0015)
    #kpca = KernelPCA(n_components=3, kernel='rbf', gamma=0.001)
    #kpca = KernelPCA(n_components=3, kernel='linear')
    kpca.fit(list(all_embeddings.values()))

    transformed_playlist_embeddings = kpca.transform(playlist_embeddings)
    mean_transformed_playlist_embedding = stats.trim_mean(transformed_playlist_embeddings, proportiontocut=proportiontocut, axis=0)

    # find which tracks are removed when computing trimmed mean
    # so that we can not draw lines to them in the visualization
    #kept_tpes = stats.trimboth(transformed_playlist_embeddings, proportiontocut=proportiontocut, axis=0)
    #removed_tpes = [embedding for embedding in transformed_playlist_embeddings if embedding not in kept_tpes]
    #removed_video_ids = [video_id for video_id, embedding in zip(playlist_video_ids, playlist_embeddings) if kpca.transform([embedding]) not in kept_tpes]
    #print(removed_video_ids)

    transformed_most_embeddings = kpca.transform(most_embeddings)
    distances = euclidean_distances([mean_transformed_playlist_embedding], transformed_most_embeddings)[0]
    closest_indices = np.argsort(distances, kind="quicksort")[:k]
    closest_embeddings = {most_ids[i]: most_embeddings[i] for i in closest_indices}


    closest_tracks = []
    for video_id, embedding in closest_embeddings.items():
        #print(track_id)
        #raise ValueError()
        track_id = cursor.execute("SELECT track_id FROM audio_files WHERE video_id = ?", (video_id,)).fetchone()[0]
        name, artist, album_id = cursor.execute("SELECT name, artist, album_id FROM tracks WHERE id = ?",
                             (track_id,)).fetchone()
        album = cursor.execute("SELECT name FROM albums WHERE id = ?", (album_id,)).fetchone()[0]
        closest_tracks.append({
            "track_id": track_id,
            "name": name,
            "artist": artist,
            "album": album,
            "video_id": video_id,
            "embedding": embedding
        })

    conn.close()
    removed_video_ids = None
    return closest_tracks, mean_transformed_playlist_embedding, removed_video_ids, kpca

def kernel_pca_visualization(playlist_tracks, recommendations, mrpe, removed_video_ids, kpca):
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()

    playlist_video_ids = {track["video_id"] for track in playlist_tracks}
    recommendations_video_ids = {track["video_id"] for track in recommendations}
    all_embeddings = {row[0]: np.array(row[1:]) for row in 
                      cursor.execute("select * from audio_embeddings;")
                      }
    #all_video_ids = set(all_embeddings.keys())
    #outside_video_ids = all_video_ids.difference(playlist_video_ids.union(recommendations_video_ids))

    data = [{"pc1": mrpe[0], "pc2": mrpe[1], "pc3": mrpe[2], "track_name": "Playlist Average", "artist": "", "category": "average"}]
    for video_id, embedding in all_embeddings.items():
        transformed_embedding = kpca.transform([embedding])[0]
        if video_id in playlist_video_ids:
            category = "playlist"
        elif video_id in recommendations_video_ids:
            category = "recommended"
        else:
            category = "outside"

        track_info = cursor.execute(
            "SELECT name, artist FROM tracks WHERE id = (SELECT track_id FROM audio_files WHERE video_id = ? limit 1)",
            (video_id,)
        ).fetchone()

        if track_info:
            track_name, artist = track_info
            data.append({
                "pc1": transformed_embedding[0],
                "pc2": transformed_embedding[1],
                "pc3": transformed_embedding[2],
                "track_name": track_name,
                "artist": artist,
                "category": category,
                "video_id": video_id,
            })

    df = pd.DataFrame(data)
    #df.to_pickle("all_data.pkl")
    def map_sizes(category):
        if category == "playlist":
            return 4
        elif category == "recommended":
            return 4
        elif category == "average":
            return 6
        else:
            return 0.05
    df["size"] = df["category"].apply(map_sizes)
    df["artist"] = df["artist"].apply(lambda x: f"by {x}" if x != "" else "")

    color_discrete_map={
                "average": "rgba(127, 0, 255, 1)",
                "playlist": "rgba(0, 128, 255, 1)",
                "recommended": "rgba(255, 0, 0, 1)",
                "outside": "rgba(0, 255, 255, 0.05)"
                }

    fig = px.scatter_3d(df, x='pc1', y='pc2', z='pc3',
                color='category', size="size", color_discrete_map=color_discrete_map,
                hover_name='track_name', 
                hover_data={
                    'pc1': False,
                    'pc2': False,
                    'pc3': False,
                    'category': False,
                    'track_name': True,
                    'artist': True,
                    'video_id': False,
                    'size': False
                },
                title="Kernel Principal Component Analysis Visualization",
                labels={'pc1': 'PC1', 'pc2': 'PC2', 'pc3': 'PC3'},
                )

    fig.update_layout(
        hoverlabel_align = 'left',
    )
    #print("plotly express hovertemplate:", fig.data[0].hovertemplate)
    fig.update_traces(hovertemplate='<b>%{hovertext}</b><br><b>%{customdata[2]}<extra></extra>')

    mrpe = df[df["category"] == "average"][["pc1", "pc2", "pc3"]].values[0]
    #(df["video_id"].apply(lambda t: t not in removed_video_ids))

    lines = [
        {"start": mrpe, "end": p} 
        for p in df[df["category"] == "playlist"][["pc1", "pc2", "pc3"]].values
    ]


    ## Add lines as Scatter3d traces
    for line in lines:
        fig.add_trace(
            go.Scatter3d(
                x=[line['start'][0], line['end'][0]],
                y=[line['start'][1], line['end'][1]],
                z=[line['start'][2], line['end'][2]],
                mode='lines',
                line=dict(color='rgba(0,128,255,1)', width=3),
                showlegend=False,
                hoverinfo='none',
            )
        )

    #fig.show()
    fig.update_layout(showlegend=False)
    return fig


def collaborative_filtering(playlist_tracks, k):
    return [
        {
            "track_id": "2RYjjYGzW3WK7X32aiSU3e",
            "name": "The Last Oasis",
            "artist": "King Gizzard & The Lizard Wizard",
            "album": "Gumboot Soup",
            "video_id": "XF_eiMLG9Ho",
            "embedding": [-1.69638335704803,-2.82143902778625,-2.0857310295105,-1.52929270267487,-1.61172008514404,-2.91124653816223,-4.33067274093628,-3.81208062171936,-3.32426810264587,-3.17405962944031,-3.97215294837952,-4.73636913299561,-2.83360266685486,-4.71635770797729,-4.55160427093506,-3.64405417442322,-2.75238299369812,-4.07062244415283,-3.02868223190308,-4.96187114715576,-3.74318695068359,-4.74432611465454,-3.91016054153442,-3.392174243927,-4.50672912597656,-5.46211624145508,-4.12211894989014,-5.18513917922974,-3.34830188751221,-4.57035493850708,-2.27707242965698,-5.19782733917236,-4.99924945831299,-3.55213069915771,-5.60144281387329,-5.70136451721191,-6.1521463394165,-5.14581251144409,-4.88148736953735,-5.60770511627197,-3.91060948371887,-4.24356126785278,-6.06388664245605,-3.9913592338562,-5.26676225662231,-5.14900207519531,-3.67801117897034,-5.10985469818115,-5.44211578369141,-5.74754667282104]
        }
    ]

def hybrid_filtering(playlist_tracks, k):
    return collaborative_filtering(playlist_tracks, k)








def get_music_recommendations(playlist_tracks, k, model_selection) -> tuple[dict, Any]:
    if model_selection == "content":
        recommendations, mtpe, removed_video_ids, kpca = content_based_filtering(playlist_tracks, k)
        fig = kernel_pca_visualization(playlist_tracks, recommendations, mtpe, removed_video_ids, kpca)
        return recommendations, fig
    elif model_selection == "hybrid":
        recommendations = hybrid_filtering(playlist_tracks, k)
        return recommendations, None
    elif model_selection == "collaborative":
        recommendations = collaborative_filtering(playlist_tracks, k)
        return recommendations, None
    else:
        raise ValueError("Invalid model selection. Choose 'content', 'collaborative', or 'hybrid'.")