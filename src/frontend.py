from dash import html, Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import numpy as np
from sklearn.cluster import DBSCAN
import pathlib
import json
import uuid
import requests

from app_layout import app
from latentxp_utils import hex_to_rgba, generate_scatter_data, remove_key_from_dict_list, get_content, job_content_dict
from dimension_reduction import computePCA, computeUMAP
from dash_component_editor import JSONParameterEditor

#### GLOBAL PARAMS ####
OUTPUT_DIR = pathlib.Path('data/output') # save the latent vectors
USER = 'mlexchange-team'
UPLOAD_FOLDER_ROOT = "data/upload"

@app.callback(
    Output('additional-model-params', 'children'),
    Output('model_id', 'data'),
    Input('algo-dropdown', 'value')
)
def show_gui_layouts(selected_algo):

    data = requests.get('http://content-api:8000/api/v0/models').json() # all model
   
    if selected_algo == 'PCA':
        conditions = {'name': 'PCA'}
    if selected_algo == 'UMAP':
        conditions = {'name': 'UMAP'}
    
    model = [d for d in data if all((k in d and d[k] == v) for k, v in conditions.items())] # filter pca or umap
    model_uid = model[0]["content_id"]
    new_model = remove_key_from_dict_list(model[0]["gui_parameters"], 'comp_group')
    # print("---")
    # print(new_model)
    # print("---")

    item_list = JSONParameterEditor(_id={'type': str(uuid.uuid4())},
                                    json_blob=new_model,
    )
    item_list.init_callbacks(app)
        
    return item_list, model_uid
        
@app.callback(
    Output('input_data', 'data'),
    Output('input_labels', 'data'),
    Output('label_schema', 'data'),
    Output('label-dropdown', 'options'),
    Input('dataset-selection', 'value'),
)
def update_label_schema(selected_dataset):
    data = None
    labels = None
    label_schema = None 

    if selected_dataset == "data/Demoshapes.npz":
        data = np.load("/app/work/data/Demoshapes.npz")['arr_0']
        labels = np.load("/app/work/data/DemoLabels.npy")  
        f = open("/app/work/data/label_schema.json")
        label_schema = json.load(f)
    
    options = [{'label': f'Label {label}', 'value': label} for label in label_schema]
    options.insert(0, {'label': 'Unlabeled', 'value': -1})
    options.insert(0, {'label': 'All', 'value': -2})

    return data, labels, label_schema, options

@app.callback(
    [
        Output('latent_vectors', 'data'),
        Output('clusters', 'data'),
        Output('cluster-dropdown', 'options'),
        # reset scatter plot control panel
        Output('scatter-color',  'value'),
        Output('cluster-dropdown', 'value'),
        Output('label-dropdown', 'value'),
        # reset heatmap
        Output('heatmap', 'figure', allow_duplicate=True),
    ],
    Input('run-algo', 'n_clicks'),
    [
        State('input_data', 'data'),
        State('model_id', 'data'),
        State('algo-dropdown', 'value'),
        State('additional-model-params', 'children'),
    ],
    prevent_initial_call=True
)
def update_latent_vectors_and_clusters(submit_n_clicks, model_id,
                                       input_data, selected_algo, children):
    """
    This callback is triggered every time the Submit button is hit.
    """
    print(selected_algo)
    #print("model id", model_id)
    input_data = np.array(input_data)
    if (submit_n_clicks is None) or (input_data is None):
        raise PreventUpdate
    
    input_params = {}
    if children:
        for child in children['props']['children']:
            key   = child["props"]["children"][1]["props"]["id"]["param_key"]
            value = child["props"]["children"][1]["props"]["value"]
            input_params[key] = value
    print(input_params)

    model_content = get_content(model_id)
    job_content = job_content_dict(model_content)
    job_content['job_kwargs']['kwargs']['parameters'] = input_params

    compute_dict = {'user_uid': USER,
                    'host_list': ['mlsandbox.als.lbl.gov', 'local.als.lbl.gov', 'vaughan.als.lbl.gov'],
                    'requirements': {'num_processors': 2,
                                     'num_gpus': 0,
                                     'num_nodes': 2},
                    }
    compute_dict['job_list'] = [job_content]
    compute_dict['dependencies'] = {'0':[]}
    compute_dict['requirements']['num_nodes'] = 1


    if selected_algo == 'PCA':
        cmd_list = ["python pca_run.py", "data/Demoshapes.npz", "output"]
    if selected_algo == 'UMAP':
        cmd_list = ["python umap_run.py", "data/Demoshapes.npz", "output"]
        #latent_vectors = computeUMAP(input_data, input_params)
    docker_cmd = " ".join(cmd_list)
    docker_cmd = docker_cmd + ' \'' + json.dumps(input_params) + '\''
    job_content['job_kwargs']['cmd'] = docker_cmd
    print("job cont")
    #print(job_content)
    response = requests.post('http://job-service:8080/api/v0/workflows', json=compute_dict)
    print("respnse: ", response)
    # print("latent vector", latent_vectors.shape)
    clusters = None
    # if latent_vectors is not None:
    #     obj = DBSCAN(eps=1.70, min_samples=1, leaf_size=5)
    #     clusters = obj.fit_predict(latent_vectors)
    
    unique_clusters = np.unique(clusters)
    options = [{'label': f'Cluster {cluster}', 'value': cluster} for cluster in unique_clusters if cluster != -1]
    options.insert(0, {'label': 'All', 'value': -1})

    return latent_vectors, clusters, options, 'cluster', -1, -2 , go.Figure(go.Heatmap())

## TODO: update state 
@app.callback(
    Output('scatter', 'figure'),
    [
        Input('latent_vectors', 'data'),
        Input('cluster-dropdown', 'value'),
        Input('label-dropdown', 'value'),
        Input('scatter-color', 'value'),
    ],
    [
        State('scatter', 'figure'),
        State('scatter', 'selectedData'),
        #State('ncomponents-dropdown', 'value'),
        State('additional-model-params', 'children'),
        State('clusters', 'data'),
        State('input_labels', 'data'),
        State('label_schema', 'data'),
    ]
)
def update_scatter_plot(latent_vectors, selected_cluster, selected_label, scatter_color,
                        current_figure, selected_data, children, clusters, labels, label_names):
    if latent_vectors is None or children is None:
        raise PreventUpdate
    latent_vectors = np.array(latent_vectors)

    n_components = children['props']['children'][0]["props"]["children"][1]["props"]["value"]

    if selected_data is not None and len(selected_data.get('points', [])) > 0:
        selected_indices = [point['customdata'][0] for point in selected_data['points']]
    else:
        selected_indices = None

    cluster_names = {a: a for a in np.unique(clusters).astype(int)}
    
    scatter_data = generate_scatter_data(latent_vectors,
                                        n_components,
                                        selected_cluster,
                                        clusters,
                                        cluster_names,
                                        selected_label,
                                        labels,
                                        label_names,
                                        scatter_color)

    fig = go.Figure(scatter_data)
    fig.update_layout(legend=dict(tracegroupgap=20))

    if current_figure and 'xaxis' in current_figure['layout'] and 'yaxis' in current_figure[
        'layout'] and 'autorange' in current_figure['layout']['xaxis'] and current_figure['layout']['xaxis'][
        'autorange'] is False:
        # Update the axis range with current figure's values if available and if autorange is False
        fig.update_xaxes(range=current_figure['layout']['xaxis']['range'])
        fig.update_yaxes(range=current_figure['layout']['yaxis']['range'])
    else:
        # If it's the initial figure or autorange is True, set autorange to True to fit all points in view
        fig.update_xaxes(autorange=True)
        fig.update_yaxes(autorange=True)

    if selected_indices is not None:
        # Use the selected indices to highlight the selected points in the updated figure
        for trace in fig.data:
            if trace.marker.color is not None:
                trace.marker.color = [hex_to_rgba('grey', 0.3) if i not in selected_indices else 'red' for i in
                                      range(len(trace.marker.color))]
    return fig

@app.callback(
    Output('heatmap', 'figure', allow_duplicate=True),
    [
        Input('scatter', 'clickData'),
        Input('scatter', 'selectedData'),
        Input('mean-std-toggle', 'value'),
    ],
    State('input_data', 'data'),
    prevent_initial_call=True
)
def update_heatmap(click_data, selected_data, display_option, input_data):
    if input_data is None:
        raise PreventUpdate
    
    images = np.array(input_data)
    if selected_data is not None and len(selected_data['points']) > 0:
        selected_indices = [point['customdata'][0] for point in selected_data['points']]  # Access customdata for the original indices
        selected_images = images[selected_indices]
        if display_option == 'mean':
            heatmap_data = go.Heatmap(z=np.mean(selected_images, axis=0))
        elif display_option == 'sigma':
            heatmap_data = go.Heatmap(z=np.std(selected_images, axis=0))
    elif click_data is not None and len(click_data['points']) > 0:
        selected_index = click_data['points'][0]['customdata'][0]  # click_data['points'][0]['pointIndex']
        heatmap_data = go.Heatmap(z=images[selected_index])
    else:
        heatmap_data = go.Heatmap()
    
    # Determine the aspect ratio based on the shape of the heatmap_data's z-values
    aspect_x = 1
    aspect_y = 1
    if heatmap_data['z'] is not None:
        if heatmap_data['z'].size > 0:
            aspect_y, aspect_x = np.shape(heatmap_data['z'])

    return go.Figure(
        data=heatmap_data,
        layout=dict(
            autosize=True,
            yaxis=dict(scaleanchor="x", scaleratio=aspect_y / aspect_x),
        )
    )

@app.callback(
    Output('stats-div', 'children'),
    Input('scatter', 'selectedData'),
    [
        State('clusters', 'data'),
        State('input_labels', 'data'),
        State('label_schema', 'data')
    ]
)
def update_statistics(selected_data, clusters, assigned_labels, label_names):
    clusters = np.array(clusters)
    assigned_labels = np.array(assigned_labels)
    if selected_data is not None and len(selected_data['points']) > 0:
        selected_indices = [point['customdata'][0] for point in
                            selected_data['points']]  # Access customdata for the original indices
        selected_clusters = clusters[selected_indices]
        selected_labels = assigned_labels[selected_indices]

        num_images = len(selected_indices)
        unique_clusters = np.unique(selected_clusters)
        unique_labels = np.unique(selected_labels)

        # Format the clusters and labels as comma-separated strings
        clusters_str = ", ".join(str(cluster) for cluster in unique_clusters)
        label_int_to_str_map = {val: key for key, val in label_names.items()}
        labels_str = ", ".join(str(label_int_to_str_map[label]) for label in unique_labels)
    else:
        num_images = 0
        clusters_str = "N/A"
        labels_str = "N/A"

    return [
        f"Number of images selected: {num_images}",
        html.Br(),
        f"Clusters represented: {clusters_str}",
        html.Br(),
        f"Labels represented: {labels_str}",
    ]


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8070, )


