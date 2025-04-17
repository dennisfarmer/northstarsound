
from dotenv import dotenv_values
import sqlite3
from sklearn.decomposition import KernelPCA
from sklearn.metrics.pairwise import euclidean_distances, cosine_similarity
import pandas as pd
import numpy as np
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go
from typing import Any
import math
import requests

from track_data import lookup_audio_embedding, \
    lookup_video_id, search_yt_for_video_id, \
    add_missing_video_ids, YoutubeSearchError

env = dotenv_values(".env")
verbose = env["VERBOSE"] == "True"
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

def map_sizes(category: str) -> float:
    if category == "playlist":
        return 4.0
    elif category == "hybrid_recommended":
        return 4.0
    elif category == "recommended":
        return 4.0
    elif category == "average":
        return 6.0
    elif category == "other":
        return 0.05
    else:
        return 0.05

color_discrete_map={
            "average": "rgba(127, 0, 255, 1)",
            "playlist": "rgba(0, 128, 255, 1)",
            "hybrid_recommended": "rgba(144, 238, 144, 1)",
            "recommended": "rgba(255, 0, 0, 1)",
            "other": "rgba(0, 255, 255, 0.05)"
            }

def clean_playlist_track_embeddings(playlist_tracks):
    return [track for track in playlist_tracks if track["embedding"] is not None]

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

def visualize_content_based_recommendations(playlist_tracks, recommendations, mrpe, removed_video_ids, kpca, hybrid_track_ids: set = None) -> go.Figure:
    if hybrid_track_ids is None:
        hybrid_track_ids = set()
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()

    playlist_video_ids = {track["video_id"] for track in playlist_tracks}
    recommendations_video_ids = {track["video_id"] for track in recommendations}
    all_embeddings = {row[0]: np.array(row[1:]) for row in 
                      cursor.execute("select * from audio_embeddings;")
                      }
    #all_video_ids = set(all_embeddings.keys())
    #other_video_ids = all_video_ids.difference(playlist_video_ids.union(recommendations_video_ids))

    data = [{"pc1": mrpe[0], "pc2": mrpe[1], "pc3": mrpe[2], "track_name": "Playlist Average", "artist": "", "category": "average"}]
    for video_id, embedding in all_embeddings.items():
        transformed_embedding = kpca.transform([embedding])[0]
        if video_id in playlist_video_ids:
            category = "playlist"
        elif video_id in recommendations_video_ids:
            category = "recommended"
        else:
            category = "other"

        track_info = cursor.execute(
            "SELECT id, name, artist FROM tracks WHERE id = (SELECT track_id FROM audio_files WHERE video_id = ? limit 1)",
            (video_id,)
        ).fetchone()

        if track_info:
            track_id, track_name, artist = track_info
            if track_id in hybrid_track_ids:
                category = "hybrid_recommended"
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
    df["size"] = df["category"].apply(map_sizes)
    df["artist"] = df["artist"].apply(lambda x: f"by {x}" if x != "" else "")


    fig = px.scatter_3d(
        df, 
        x='pc1', 
        y='pc2', 
        z='pc3',
        color='category',
        size="size", 
        color_discrete_map=color_discrete_map,
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
        title="Content-based Filtering Recommendations Visualization",
        labels={"pc1": "Principal Component 1", "pc2": "Principal Component 2", "pc3": "Principal Component 3"}
        )

    fig.update_layout(
        hoverlabel_align = 'left',
        #showlegend=False,
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

    conn.close()
    return fig


def default():
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

#def collaborative_filtering(playlist_tracks, k):
#select pt.track_id, p.owner_id, count(*)
#from playlist_tracks pt
#join playlists p on pt.playlist_id = p.id
#group by pt.track_id, p.owner_id
#having count(*) > 1;

def compute_track_factors(latent_features=10, epochs=10, learning_rate=0.01):
    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()

    query = """
        SELECT pt.track_id, p.owner_id
        FROM playlist_tracks pt
        JOIN playlists p ON pt.playlist_id = p.id
    """
    interactions = cursor.execute(query)

    user_to_index = {}
    track_to_index = {}
    user_count = 0
    track_count = 0

    for track_id, owner_id in interactions:
        if owner_id not in user_to_index:
            user_to_index[owner_id] = user_count
            user_count += 1
        if track_id not in track_to_index:
            track_to_index[track_id] = track_count
            track_count += 1

    num_users = len(user_to_index)
    num_tracks = len(track_to_index)

    user_factors = np.random.normal(scale=1.0 / latent_features, size=(num_users, latent_features))
    track_factors = np.random.normal(scale=1.0 / latent_features, size=(num_tracks, latent_features))

    interactions = cursor.execute(query)
    for epoch in range(epochs):
        for track_id, owner_id in interactions:
            user_idx = user_to_index[owner_id]
            track_idx = track_to_index[track_id]

            prediction = np.dot(user_factors[user_idx], track_factors[track_idx])
            error = 1 - prediction  # Implicit feedback: 1 for observed interactions

            user_factors[user_idx] += learning_rate * error * track_factors[track_idx]
            track_factors[track_idx] += learning_rate * error * user_factors[user_idx]

        interactions = cursor.execute(query)  # Reset cursor for next epoch

    conn.close()
    return user_factors, track_factors, user_to_index, track_to_index

#def visualize_collaborative_recommendations(playlist_tracks, recommendations, user_factors, track_factors, user_to_index, track_to_index, hybrid_track_ids: set = None) -> go.Figure:
def visualize_collaborative_relationships(playlist_tracks, recommendations, user_factors, track_factors, user_to_index, track_to_index, hybrid_track_ids=None) -> go.Figure:
    """
    Visualizes the relationships between playlist tracks and recommended tracks using latent factors.

    Args:
        playlist_tracks (list): List of tracks in the playlist.
        recommendations (list): List of recommended tracks.
        user_factors (np.ndarray): User latent factors matrix.
        track_factors (np.ndarray): Track latent factors matrix.
        user_to_index (dict): Mapping of user IDs to indices.
        track_to_index (dict): Mapping of track IDs to indices.

    Returns:
        go.Figure: Plotly figure object visualizing the relationships.
    """
    if not playlist_tracks or not recommendations:
        return None
    if hybrid_track_ids is None:
        hybrid_track_ids = set()

    # Extract track IDs for playlist and recommendations
    playlist_track_ids = [track["track_id"] for track in playlist_tracks]
    recommended_track_ids = [track["track_id"] for track in recommendations]

    # Filter out tracks not in the latent factor mappings
    playlist_track_indices = [track_to_index[tid] for tid in playlist_track_ids if tid in track_to_index]
    recommended_track_indices = [track_to_index[tid] for tid in recommended_track_ids if tid in track_to_index]

    # Prepare data for visualization
    data = []
    for playlist_idx in playlist_track_indices:
        for rec_idx in recommended_track_indices:
            # Compute similarity (dot product) between latent factors
            similarity = np.dot(track_factors[playlist_idx], track_factors[rec_idx])

            playlist_track = next((track for track in playlist_tracks if track_to_index.get(track["track_id"]) == playlist_idx), None)
            recommended_track = next((track for track in recommendations if track_to_index.get(track["track_id"]) == rec_idx), None)

            if playlist_track and recommended_track:
                data.append({
                    "playlist_track": f"{playlist_track['name']} by {playlist_track['artist']}",
                    "recommended_track": f"{recommended_track['name']} by {recommended_track['artist']}{' 👨‍💻' if recommended_track["track_id"] in hybrid_track_ids else ' ️👨'}",
                    "similarity": similarity
                })

    # Create a DataFrame for visualization
    df = pd.DataFrame(data)
    df = df.sort_values(by="similarity", ascending=False, kind="quicksort")
    def normalize(x: pd.Series) -> pd.Series:
        return (x - x.min()) / (x.max() - x.min())

    # crop off the lower half of the similarity scores so the plot is less cluttered
    df["similarity_normalized"] = normalize(
        (df["similarity"] - df["similarity"].quantile(0.50)).apply(lambda x: max(x, 0))
        )

    # Create a Plotly figure using a Sankey diagram
    # https://plotly.com/python-api-reference/generated/plotly.graph_objects.sankey.link.html
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=list(df["playlist_track"].unique()) + list(df["recommended_track"].unique()),
            color="blue"
        ),
        link=dict(
            source=[list(df["playlist_track"].unique()).index(row["playlist_track"]) for _, row in df.iterrows()],
            target=[len(df["playlist_track"].unique()) + list(df["recommended_track"].unique()).index(row["recommended_track"]) for _, row in df.iterrows()],
            value=df["similarity_normalized"],
            hovertemplate="%{source.label} -> %{target.label}<br>Similarity: %{value:.2f}<extra></extra>",
            #colorscales=[go.sankey.link.Colorscale(colorscale="viridis")]*df.shape[0],
            #color=df["similarity_normalized"],
            hovercolor="blue"
        )
    )])

    # Update layout for better visualization
    fig.update_layout(
        title_text="Collaborative Filtering Relationships",
        font_size=10
    )

    return fig

#def visualize_collaborative_recommendations(playlist_tracks, recommendations, user_factors, track_factors, user_to_index, track_to_index, hybrid_track_ids: set = None) -> go.Figure:
    #"""
    #Visualizes the precomputed track factors, the top k recommendations, and the playlist tracks using Plotly Express.

    #Args:
        #user_factors (np.ndarray): User latent factors matrix.
        #track_factors (np.ndarray): Track latent factors matrix.
        #user_to_index (dict): Mapping of user IDs to indices.
        #track_to_index (dict): Mapping of track IDs to indices.
        #recommendations (list): List of recommended tracks.
        #k (int): Number of top recommendations.
        #playlist_tracks (list): List of tracks in the playlist.

    #Returns:
        #fig: Plotly Express figure object.
    #"""
    #if hybrid_track_ids is None:
        #hybrid_track_ids = set()
    #if recommendations is None:
        #return None
    #conn = sqlite3.connect(playlist_db)
    #cursor = conn.cursor()

    #pca = PCA(n_components=3)
    ##pca = KernelPCA(n_components=3, kernel='rbf', gamma=0.02)
    #reduced_track_factors = pca.fit_transform(track_factors)

    #data = []
    #playlist_track_ids = [track["track_id"] for track in playlist_tracks]
    #recommended_track_ids = [rec["track_id"] for rec in recommendations]

    #for track_id, idx in track_to_index.items():
        #if track_id in hybrid_track_ids:
            #category = "hybrid_recommended"
        #elif track_id in recommended_track_ids:
            #category = "recommended"
        #elif track_id in playlist_track_ids:
            #category = "playlist"
        #else:
            #category = "other"

        #track_info = cursor.execute(
            #"SELECT name, artist FROM tracks WHERE id = ?;",
            #(track_id,)
        #).fetchone()

        #if track_info:
            #track_name, artist = track_info
        #else:
            #track_name = "Unknown"
            #artist = ""
        #data.append({
            #"track_id": track_id,
            #"track_name": track_name,
            #"artist": artist,
            #"pc1": reduced_track_factors[idx, 0],
            #"pc2": reduced_track_factors[idx, 1],
            #"pc3": reduced_track_factors[idx, 2],
            #"category": category
        #})

    #df = pd.DataFrame(data)

    #df["size"] = df["category"].apply(map_sizes)
    #df["artist"] = df["artist"].apply(lambda x: f"by {x}" if x != "" else "")


    ## Create 3D scatter plot
    #fig = px.scatter_3d(
        #df,
        #x="pc1",
        #y="pc2",
        #z="pc3",
        #color="category",
        #size="size",
        #color_discrete_map=color_discrete_map,
        #hover_name="track_name",
        #hover_data={
            #"pc1": False,
            #"pc2": False,
            #"pc3": False,
            #"category": False,
            #"track_name": True,
            #"artist": True,
            #"size": False
        #},
        #title="Collaborative Filtering Recommendations Visualization",
        #labels={"pc1": "Principal Component 1", "pc2": "Principal Component 2", "pc3": "Principal Component 3"}
    #)

    #fig.update_layout(
        #hoverlabel_align = 'left',
        ##showlegend=False,
    #)
    ##print("plotly express hovertemplate:", fig.data[0].hovertemplate)
    #fig.update_traces(hovertemplate='<b>%{hovertext}</b><br><b>%{customdata[2]}<extra></extra>')

    #conn.close()
    #return fig

def collaborative_filtering(playlist_tracks, k, user_factors, track_factors, user_to_index, track_to_index):
    """
    playlist_tracks (list): List of tracks in the playlist.

    k (int): Number of top recommendations to return.

        NOTE: it is possible that the number of recommendations returned 
        is less than k, in cases where some tracks are not found 
        in the database (not sure why this happens)

    user_factors (np.ndarray): User latent factors matrix.

    track_factors (np.ndarray): Track latent factors matrix.

    user_to_index (dict): Mapping of user IDs to indices.

    track_to_index (dict): Mapping of track IDs to indices.

    Returns:
        recommendations (list): List of recommended tracks.
        scores (list): List of scores for each recommendation.
    """
    if not playlist_tracks:
        return None, None

    playlist_track_ids = [track["track_id"] for track in playlist_tracks]
    playlist_track_indices = [track_to_index[tid] for tid in playlist_track_ids if tid in track_to_index]

    if not playlist_track_indices:
        return None, None

    scores = np.zeros(track_factors.shape[0])
    for idx in playlist_track_indices:
        scores += np.dot(track_factors, track_factors[idx])

    for idx in playlist_track_indices:
        scores[idx] = -np.inf

    top_k_indices = np.argsort(scores)[-k:][::-1]
    recommended_track_ids = [list(track_to_index.keys())[i] for i in top_k_indices]
    recommended_scores = [scores[i] for i in top_k_indices]

    conn = sqlite3.connect(playlist_db)
    cursor = conn.cursor()

    recommendations = []
    scores = []
    for track_id, score in zip(recommended_track_ids, recommended_scores):
        try:
            name, artist, album_id = cursor.execute(
                "SELECT name, artist, album_id FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
        except:
            print("Track not found in database:", track_id)
            continue
        try:
            album = cursor.execute(
                "SELECT name FROM albums WHERE id = ?", (album_id,)
            ).fetchone()[0]
        except:
            album = ""
        video_id = lookup_video_id(track_id, cursor)
        if video_id is None:
            embedding = None
        else:
            embedding = lookup_audio_embedding(video_id, cursor)
        recommendations.append({
            "track_id": track_id,
            "name": name,
            "artist": artist,
            "album": album,
            "video_id": video_id,
            "embedding": embedding
        })
        scores.append(score)

    conn.close()
    return recommendations, recommended_scores


#def cosine_similarity_visualization(recommendations, scores):
    #"""
    #Plots cosine similarity vectors for each track using Plotly.

    #Args:
        #track_scores (list): A list of tuples where each tuple contains a track name and its cosine similarity score.
    #"""
    #data = []
    #for track, cosine_similarity_score in zip(recommendations, scores):
        #label = f'{track["name"]} by {track["artist"]}'
        #angle = math.acos(cosine_similarity_score)
        #x1, y1 = math.cos(0), math.sin(0)  # First vector
        #x2, y2 = math.cos(angle), math.sin(angle)  # Second vector

        #data.append({"label": label, "vector": "Vector 1", "x": x1, "y": y1})
        #data.append({"label": label, "vector": "Vector 2", "x": x2, "y": y2})

    #df = pd.DataFrame(data)
    #fig = px.scatter(
        #df,
        #x="x",
        #y="y",
        #color="vector",
        #facet_col="label",
        #title="Cosine Similarity Vectors",
        #labels={"x": "X", "y": "Y", "vector": "Vector"},
        #render_mode="svg"
    #)

    #fig.update_traces(marker=dict(size=10), mode="markers+lines")
    #fig.update_layout(showlegend=True)
    #return fig

def hybrid_filtering(playlist_tracks, k, k_hybrid_search_space = k_hybrid_search_space, alpha: float = 1.0):
    """
    The way I implemented hybrid filtering is by generating the top `k_hybrid_search_space` (1000)
    recommendations using collaborative filtering and content-based filtering,
    and then joining the two lists of recommendations on the track_id.
    The top k recommendations are then selected from the intersection of the two filtering methods.
    These are called the "hybrid recommendations".
    The remaining recommendations are selected from the collaborative and content-based recommendations.
    """

    #if len(playlist_tracks) == 0:
        #k_content = 0
        #k_collaborative = k
        #raise NoValidTracksError()

    playlist_tracks_content = clean_playlist_track_embeddings(playlist_tracks)

    # note that we use k_hybrid_search_space and not k_collaborative
    user_factors, track_factors, user_to_index, track_to_index = compute_track_factors()
    recommendations_collaborative, scores = collaborative_filtering(playlist_tracks, k_hybrid_search_space, user_factors, track_factors, user_to_index, track_to_index)
    if recommendations_collaborative is None:
        return None, None

    # note that we use k_hybrid_search_space and not k_content
    recommendations_content, mtpe, removed_video_ids, kpca = content_based_filtering(playlist_tracks_content, k_hybrid_search_space)
    
    # Find the hybrid recommendations: tracks that exist in
    # both the content-based and the collaborative recommendations
    # These are the best recommendations and will be shown first
    content_ids = [track["track_id"] for track in recommendations_content]
    collaborative_ids = [track["track_id"] for track in recommendations_collaborative]
    def get_ordered_hybrid_tracks(col_ids, con_ids):
        """
        Orders the intersection of the ids based on alternating
        priority between content-based recommendations and
        collaborative recommendations, to maintain 
        the relative ordering of both lists

        Ensures that hybrid recommendations are ordered based
        on relevence to the input playlist, determined by their
        original position/ordering in the top k_hybrid_search_space 
        (K_hss=1,000 by default) recommendations from each method.

        This way, when we use alpha to place more importance on either
        the hybrid tracks or the con/col tracks, the hybrid tracks
        are still ordered based on their relevance to the input playlist
        """
        # todo: introduce hyperparameter to place more emphasis
        # on either the content-based or collaborative recommendations
        hybrid_track_ids = list(set(col_ids).intersection(con_ids))
        delta_values = [con_ids.index(hybrid_id) + col_ids.index(hybrid_id) for hybrid_id in hybrid_track_ids]
        ordered_hybrid_tracks = [hybrid_track_ids[i] for i in np.argsort(delta_values)]
        return ordered_hybrid_tracks
    #hybrid_track_ids = set(collaborative_ids).intersection(content_ids)
    hybrid_track_ids = get_ordered_hybrid_tracks(content_ids, collaborative_ids)
    recommendations_hybrid = []

    # remove overlapping tracks from collaborative and content-based recommendations
    # and add them to the hybrid recommendations
    for hybrid_id in hybrid_track_ids:
        if hybrid_id in collaborative_ids:
            idx, track = [(idx, track) for idx, track in enumerate(recommendations_collaborative) if track["track_id"] == hybrid_id][0]
            recommendations_collaborative.pop(idx)
            recommendations_hybrid.append(track)
            if hybrid_id in content_ids:
                idx, track = [(idx, track) for idx, track in enumerate(recommendations_content) if track["track_id"] == hybrid_id][0]
                recommendations_content.pop(idx)
        else:
            idx, track = [(idx, track) for idx, track in enumerate(recommendations_content) if track["track_id"] == hybrid_id][0]
            recommendations_content.pop(idx)
            recommendations_hybrid.append(track)
    
    # todo: introduce hyperparameter alpha to control the 
    # number of hybrid recommendations vs cont/collab recommendations
    k = k - len(recommendations_hybrid)
    if k <= 0:
        k_collaborative = 0
        k_content = 0
    elif k % 2 == 0:
        k_collaborative = k // 2
        k_content = k // 2
    else:
        k_collaborative = math.ceil(k / 2)
        k_content = math.floor(k / 2)

    recommendations_collaborative = recommendations_collaborative[:k_collaborative]
    recommendations_content = recommendations_content[:k_content]
    fig_collaborative = visualize_collaborative_relationships(
        playlist_tracks, 
        recommendations_collaborative + recommendations_hybrid, 
        user_factors, 
        track_factors, 
        user_to_index, 
        track_to_index, 
        hybrid_track_ids
        ) 
    fig_content = visualize_content_based_recommendations(
        playlist_tracks_content, 
        recommendations_content if len(recommendations_content) > 0 else recommendations_hybrid, 
        mtpe, 
        removed_video_ids, 
        kpca, 
        hybrid_track_ids
        ) 

    return {
        "recommendations": {
            "hybrid": add_missing_video_ids(recommendations_hybrid),
            "collaborative": add_missing_video_ids(recommendations_collaborative),
            "content": add_missing_video_ids(recommendations_content), 
            },
        "figs": {
            "hybrid": None,
            "collaborative": fig_collaborative,
            "content": fig_content,
            },
        }



class NoValidTracksError(Exception):
    """Exception raised when no tracks with valid embeddings are found in the playlist."""
    def __init__(self, message="No tracks in the playlist with audio embeddings."):
        self.message = message
        super().__init__(self.message)

class EmptyPlaylistError(Exception):
    """Exception raised when no tracks are found in the playlist."""
    def __init__(self, message="No tracks in the playlist."):
        self.message = message
        super().__init__(self.message)



def get_music_recommendations(playlist_tracks, k, model_selection) -> tuple[dict[list], dict[go.Figure]]:
    if len(playlist_tracks) == 0:
        raise EmptyPlaylistError()
    if model_selection == "content":
        playlist_tracks = clean_playlist_track_embeddings(playlist_tracks)
        if len(playlist_tracks) == 0:
            raise NoValidTracksError()
        recommendations, mtpe, removed_video_ids, kpca = content_based_filtering(playlist_tracks, k)
        fig = visualize_content_based_recommendations(playlist_tracks, recommendations, mtpe, removed_video_ids, kpca)
        return {"content": add_missing_video_ids(recommendations)}, {"content": fig}
    elif model_selection == "hybrid":
        results = hybrid_filtering(playlist_tracks, k)
        return results["recommendations"], results["figs"]
    elif model_selection == "collaborative":
        user_factors, track_factors, user_to_index, track_to_index = compute_track_factors()
        recommendations, scores = collaborative_filtering(playlist_tracks, k, user_factors, track_factors, user_to_index, track_to_index)
        fig = visualize_collaborative_relationships(playlist_tracks, recommendations, user_factors, track_factors, user_to_index, track_to_index)
        return {"collaborative": add_missing_video_ids(recommendations)}, {"collaborative": fig}
    else:
        raise ValueError("Invalid model selection. Choose 'content', 'collaborative', or 'hybrid'.")