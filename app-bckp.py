import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objs as go


FPS = 30
VIDEO_DURATION = 10  # in seconds
MAX_FRAMES = FPS * VIDEO_DURATION
from collections import defaultdict

app = dash.Dash(__name__)

annotations = [
  {
    "start": 0,
    "end": 13,
    "label": "aline"
  },
  {
    "start": 0,
    "end": 302,
    "label": "lungslidingpresent"
  },
  {
    "start": 41,
    "end": 53,
    "label": "bline"
  },
  {
    "start": 117,
    "end": 153,
    "label": "aline"
  },
  {
    "start": 167,
    "end": 203,
    "label": "aline"
  },
  {
    "start": 217,
    "end": 233,
    "label": "aline"
  },
  {
    "start": 247,
    "end": 253,
    "label": "aline"
  },
  {
    "start": 277,
    "end": 302,
    "label": "aline"
  }
]

app.layout = html.Div([
    html.H3("Video + Timeline with Auto-Updating Marker"),

    # 1) Video element
    html.Video(
        id='video-player',
        src='/assets/final_output_h264.mp4',  # Place video.mp4 in "assets/" folder
        controls=True,
        style={'width': '640px', 'border': '1px solid #ccc'}
    ),

    # 2) Hidden slider that will store the "currentTime" from the video
    html.Div(
        dcc.Slider(
            id='time-slider',
            min=0,
            max=VIDEO_DURATION,   # Adjust if your video is longer
            value=0,
            step=0.1
        ),
        style={'display': 'none'}
    ),

    # 3) Interval to poll the video time in the browser
    dcc.Interval(
        id='poll-video-time',
        interval=300,  # every 0.5 second
        n_intervals=0
    ),

    # 4) Graph for the annotations + vertical line
    dcc.Graph(id='timeline-graph')
])

###############################################################################
# 5) Clientside callback: read video.currentTime in the browser, set slider
###############################################################################
app.clientside_callback(
    """
    function(n_intervals) {
        var vid = document.getElementById('video-player');
        if (!vid) {
            return dash_clientside.no_update;
        }
        // Return the current playback time in SECONDS
        return vid.currentTime;
    }
    """,
    Output('time-slider', 'value'),
    Input('poll-video-time', 'n_intervals')
)

###############################################################################
# 6) Server callback: build the figure from the slider's current value
###############################################################################
@app.callback(
    Output('timeline-graph', 'figure'),
    Input('time-slider', 'value')
)
def update_timeline(current_time_seconds):
    current_frame = int(current_time_seconds * FPS)

     # 1) Group intervals by label:
    #    label_to_segments[label] = [(start1, end1), (start2, end2), ...]
    label_to_segments = defaultdict(list)
    for ann in annotations:
        label_to_segments[ann['label']].append((ann['start'], ann['end']))

    # 2) Build a single trace for each label, with "None" to separate segments
    data_traces = []
    for label, segments in label_to_segments.items():
        # We'll build x=[start,end,None,start,end,None,...] for each label
        x_coords = []
        y_coords = []
        for (start, end) in segments:
            x_coords += [start, end, None]   # None => gap
            y_coords += [label, label, None]

        data_traces.append(
            go.Scatter(
                x=x_coords,
                y=y_coords,
                mode='lines',
                line=dict(width=8),
                name=label  # one legend entry per label
            )
        )

    # Vertical line at the current_time
    vertical_line_shape = {
        "type": "line",
        "x0": current_frame,
        "x1": current_frame,
        "y0": 0,
        "y1": 1,
        "xref": "x",
        "yref": "paper",
        "line": {"color": "red", "width": 3, "dash": "dash"}
    }

    layout = go.Layout(
        title=f"Current Frame: {current_frame}",
        xaxis=dict(range=[0, MAX_FRAMES], title="Time (seconds)"),
        yaxis=dict(title='Annotations', type='category'),
        shapes=[vertical_line_shape],
        height=400
    )

    return go.Figure(data=data_traces, layout=layout)

if __name__ == "__main__":
    app.run_server(debug=True, port=3000, host="0.0.0.0")
