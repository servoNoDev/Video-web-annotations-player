from flask import Flask, render_template, send_from_directory
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import json
import os
from collections import defaultdict
from urllib.parse import parse_qs

# ------------------------------
# Configuration
# ------------------------------
FPS = 30  # Frames per second (global)
# For demonstration, we'll use a default video duration (in seconds).
# In a real app you might determine this dynamically.
DEFAULT_VIDEO_DURATION = 100

DF_PATH = "/home/mh731nk/_data/experiments_tmp/data/revision_8/over_draw_videos/01"
ASSETS_PATH   = "/home/mh731nk/_data/experiments_tmp/data/revision_8/over_draw_videos/01/videos_encoded"
ANNOTATIONS_PATH = "/home/mh731nk/_data/experiments_tmp/data/revision_8/over_draw_videos/01"
color_mapping = {
    "aline": "blue",
    "lungslidingpresent": "orange",
    "bline": "green"
}

# ===============================
# 1. Create the Flask server
# ===============================
server = Flask(__name__)
# Update 'video_dir' to point to your actual video folder.
@server.route('/videos/<filename>')
def serve_video(filename):
    video_dir = "/home/mh731nk/_data/experiments_tmp/data/revision_8/over_draw_videos/01/videos_encoded"
    return send_from_directory(video_dir, filename)


@server.route("/")
def index():
    # Load videos from CSV (if not found, use sample data)
    csv_file = f"{DF_PATH}/df_videos.csv"
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        videos = df.to_dict(orient="records")
    else:
        videos = [
            {
                "video_id": "YWI9C2CG",
                "name_cvat": "Sonoscape_2021-09_2021-10-18_001_20210928_144651_1.avi",
                "name_video": "001 20210928_144651_1.avi",
                "video_subfolder_path": "USG/task_32",
                "task_status": "completed"
            },
            {
                "video_id": "4ANV9APK",
                "name_cvat": "Sonoscape_2021-09_2021-10-18_001_20210928_144804_3.avi",
                "name_video": "001 20210928_144804_3.avi",
                "video_subfolder_path": "USG/task_33",
                "task_status": "completed"
            }
        ]
    return render_template("index.html", videos=videos)

# ===============================
# 2. Create the Dash app (mounted at /player/)
# ===============================
external_stylesheets = []
dash_app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname='/player/',
    external_stylesheets=external_stylesheets
)
dash_app.config.suppress_callback_exceptions = True

# The Dash layout uses a dcc.Location to read URL query parameters.
dash_app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.H3("Video Player with Timeline"),
    # Video element (src updated by callback)
    html.Video(
        id='video-player',
        controls=True,
        style={'width': '50%', 'border': '1px solid #ccc'}
    ),
    # Hidden slider to store currentTime (in seconds)
    html.Div(
        dcc.Slider(
            id='time-slider',
            min=0,
            max=100,  # Default value; will be updated based on video duration
            value=0,
            step=0.1
        ),
        style={'display': 'none'}
    ),
    # Interval for polling video currentTime
    dcc.Interval(
        id='poll-video-time',
        interval=300,  # every 300ms
        n_intervals=0
    ),
    # Hidden div to hold annotation JSON (as a string)
    html.Div(id='annotations-data', style={'display': 'none'}),
    # Graph for the timeline
    dcc.Graph(id='timeline-graph')
])

# Callback 1: Update video source, slider max, and annotation data based on URL query parameter.
@dash_app.callback(
    [Output('video-player', 'src'),
     Output('time-slider', 'max'),
     Output('annotations-data', 'children')],
    [Input('url', 'search')]
)
def update_video_info(search):
     # Expect query parameter ?video_id=...
    params = parse_qs(search[1:]) if search and search.startswith('?') else {}
    video_id = params.get("video_id", [None])[0]
    if not video_id:
        return "", 0, ""
    # Use the custom /videos/ route to build the URL for the video source
    video_src = f"/videos/{video_id}.mp4"
    # Set the video duration (in seconds); ideally this comes from metadata
    video_duration = 100  # adjust as needed
    # Load the corresponding annotation JSON file from annotations_json folder
    annotation_file = os.path.join(ANNOTATIONS_PATH,"annotations_json", f"{video_id}.json")

    print(annotation_file)
    annotations_data = ""
    if os.path.exists(annotation_file):
        with open(annotation_file, "r") as f:
            annotations_data = f.read()
    print(annotations_data)
    return video_src, video_duration, annotations_data

# Callback 2: Clientside callback to update the hidden slider from the video player's currentTime.
dash_app.clientside_callback(
    """
    function(n_intervals) {
        var vid = document.getElementById('video-player');
        if (!vid) {
            return dash_clientside.no_update;
        }
        return vid.currentTime;
    }
    """,
    Output('time-slider', 'value'),
    Input('poll-video-time', 'n_intervals')
)

# Callback 3: Update the timeline graph based on the slider's current value and annotation data.
@dash_app.callback(
    Output('timeline-graph', 'figure'),
    [Input('time-slider', 'value'),
     Input('annotations-data', 'children'),
     Input('url', 'search'),
     ]
)
def update_timeline(current_time, annotations_json, search):
    params = parse_qs(search[1:]) if search and search.startswith('?') else {}
    video_id = params.get("video_id", [None])[0]
    frames = float(params.get("video_frames", [None])[0])
    fps = float(params.get("video_fps", [None])[0])
    print(frames)
    print(fps)
    annotation_file = os.path.join(ANNOTATIONS_PATH,"annotations_json", f"{video_id}.json")

    print(annotation_file)
    annotations_data = ""
    if os.path.exists(annotation_file):
        with open(annotation_file, "r") as f:
            annotations_data = f.read()
    # print(annotations_data)
    # Parse annotations from JSON; if missing, use sample annotations.
    if annotations_data:
        try:
            annotations = json.loads(annotations_json)
        except Exception as e:
            annotations = []
    else:
        annotations = [
            {"start": 0, "end": 13, "label": "aline"},
            {"start": 0, "end": 302, "label": "lungslidingpresent"},
            {"start": 41, "end": 53, "label": "bline"}
        ]
    # Group intervals by label
    label_to_segments = defaultdict(list)
    for ann in annotations:
        label_to_segments[ann['label']].append((ann['start'], ann['end']))
    data_traces = []
    for label, segments in label_to_segments.items():
        x_coords = []
        y_coords = []
        for (start, end) in segments:
            x_coords += [start, end, None]   # None creates a gap
            y_coords += [label, label, None]
        
        # Use the color_mapping to get the desired color for this label.
        color = color_mapping.get(label, "black")  # fallback color if label not found
        
        data_traces.append(go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='lines',
            line=dict(width=8, color=color),
            name=label
        ))
    # Vertical red line at current video time
    vertical_line_shape = {
        "type": "line",
        "x0": current_time * fps,
        "x1": current_time * fps,
        "y0": 0,
        "y1": 1,
        "xref": "x",
        "yref": "paper",
        "line": {"color": "red", "width": 3, "dash": "dash"}
    }
    layout = go.Layout(
        title=f"Timeline (Current Time: {current_time:.1f} sec)",
        xaxis=dict(range=[0, frames], title="Time (seconds)"),
        yaxis=dict(title='Annotations', type='category'),
        shapes=[vertical_line_shape],
        height=400
    )
    return go.Figure(data=data_traces, layout=layout)

# ===============================
# 3. Run the server
# ===============================
if __name__ == "__main__":
    # Run the combined Flask/Dash server.
    server.run(debug=True, port=3000, host="0.0.0.0")
