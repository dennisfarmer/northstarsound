import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

## Example data for the scatter plot
#data = {
    #'x': [1, 2, 3],
    #'y': [1, 2, 6],
    #'z': [1, 2, 6],
    #'label': ['A', 'B', 'C'],
    #'color': ['red', 'green', 'blue']
    ## 'color': ['#FF5733', '#33FF57', '#3357FF']  # Example hex colors
    ## 'color': ['rgb(255, 0, 0)', 'rgb(0, 255, 0)', 'rgb(0, 0, 255)']  # Example RGB colors
#}
#df = pd.DataFrame(data)
df = pd.read_pickle("all_data.pkl")

print(df)
def map_sizes(category):
    if category == "playlist":
        return 1
    elif category == "recommended":
        return 1
    elif category == "mrpe":
        return 2
    else:
        return 0.15
df["size"] = df["category"].apply(map_sizes)
df["artist"] = df["artist"].apply(lambda x: f"by {x}" if x != "" else "")

color_discrete_map={
            "mrpe": "rgba(127, 0, 255, 1)",
            "playlist": "rgba(0, 128, 255, 1)",
            "recommended": "rgba(255, 0, 0, 1)",
            #"outside": "rgba(192, 192, 192, 0.005)"
            "outside": "rgba(0, 255, 255, 0.005)"
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
                'size': False
            },
            title="Kernel PCA Visualization",
            labels={'pc1': 'PC1', 'pc2': 'PC2', 'pc3': 'PC3'},
            )

fig.update_layout(
    hoverlabel_align = 'left',
)
#print("plotly express hovertemplate:", fig.data[0].hovertemplate)
fig.update_traces(
    hovertemplate='<b>%{hovertext}</b><br><b>%{customdata[2]}<extra></extra>')

mrpe = df[df["category"] == "mrpe"][["pc1", "pc2", "pc3"]].values[0]

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
            line=dict(color='rgba(0,0,204,1)', width=0.5),
            showlegend=False,
            hoverinfo='none',
        )
    )

# Show the plot

fig.show()
# This code creates a 3D scatter plot with lines connecting points A to B and B to C.
# You can customize the line color, width, and other properties as needed.