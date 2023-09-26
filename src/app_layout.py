from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

import plotly.graph_objects as go
import numpy as np
from sklearn.cluster import DBSCAN

import templates
from latentxp_utils import generate_cluster_dropdown_options, generate_label_dropdown_options


external_stylesheets = [dbc.themes.BOOTSTRAP, "../assets/segmentation-style.css"]
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

server = app.server

#--------------------------------- IO ----------------------------------
label_names = {"Disc":0, "Triangle": 1, "Rectangle":2, "Annulus":3}
latent_vectors = np.load("/app/work/data/pacmacX.npy")

obj = DBSCAN(eps=1.70, min_samples=1, leaf_size=5)
clusters = obj.fit_predict(latent_vectors)

header = templates.header()
body = html.Div([
    html.Div([
        # latent plot
        html.Div([
            dcc.Graph(id='scatter-b',
                      figure=go.Figure(go.Scattergl(mode='markers')),
                      style={'padding-bottom': '5%'}),
        ], className='column', style={'flex': '50%', 'padding': '10px'}),

        # individual image
        html.Div([
            dcc.Graph(id='heatmap-a', figure=go.Figure(go.Heatmap()), style={'padding-bottom': '5%'}),
        ], className='column', style={'flex': '50%', 'padding': '10px'}),

    ], className='row', style={'display': 'flex'}),
    html.Div([
        # control panel
        html.Div([
            # Add controls and human interactions here
            # Example: dcc.Slider(), dcc.Dropdown(), etc.

            html.Label('Select cluster:'),
            dcc.Dropdown(id='cluster-dropdown',
                         options=generate_cluster_dropdown_options(clusters),
                         value=-1),

            html.Label('Select label:'),
            dcc.Dropdown(id='label-dropdown',
                         options=generate_label_dropdown_options(label_names),
                         value=-2),

            # Add a radio button for toggling mean and standard deviation
            html.Label('Display Image Options:'),
            dcc.RadioItems(id='mean-std-toggle', options=[{'label': 'Mean', 'value': 'mean'},
                                                          {'label': 'Standard Deviation', 'value': 'sigma'}],
                           value='mean'),

            # Add a radio button for toggling coloring options
            html.Label('Scatter Colors:'),
            dcc.RadioItems(id='scatter-color', options=[{'label': 'cluster', 'value': 'cluster'},
                                                        {'label': 'label', 'value': 'label'}],
                           value='cluster'),

        ], className='column', style={'flex': '50%', 'padding-bottom': '5%'}),

        # Labeler
        # Add a new div for displaying statistics
        html.Div([

            html.Div(id='stats-div', children=[
                html.P("Number of images selected: 0"),
                html.P("Clusters represented: N/A"),
                html.P("Labels represented: N/A"),
            ]),

            html.Label('Assign Label:'),
            dcc.Dropdown(id='labeler',
                         options=generate_label_dropdown_options(label_names, False),
                         value=-1),

            html.Button('Assign Labels', id='assign-labels-button'),

            html.Div(id='label-assign-output'),

        ], className='column', style={'flex': '50%', 'padding': '10px'}),

    ], className='row', style={'display': 'flex'}),

    # hidden components
    html.Div(id="scatter-update-trigger", style={"display": "none"}),
    dcc.Store(id='scatter-axis-range', storage_type='session'),
    dcc.Store(id='selected-points', storage_type='memory'),
    dcc.Store(id='selected-data-store', data=None),
    html.Script("""
                    document.addEventListener('DOMContentLoaded', function() {
                        document.getElementById('assign-labels-button').onclick = function() {
                            setTimeout(function() {
                                document.getElementById('scatter-b').focus();
                            }, 100);
                        };
                    });
                """)

], style={'display': 'grid', 'gridTemplateRows': '1fr 1fr', 'height': '100vh'})


app.layout = html.Div ([header, body])


