import dash
from dash import html, dcc, Input, Output, State, Dash
import dash_bootstrap_components as dbc
import pandas as pd
import io
import base64
import plotly.express as px

# Global dictionary to store uploaded data
uploaded_data_store = {}

# Maximum number of data points to display in graphs
MAX_POINTS = 1000

# Style settings to prevent user editing of elements
STYLE_NON_EDITABLE = {'userSelect': 'none', 'outline': 'none'}

# Properties to make elements non-editable
PROPS_NON_EDITABLE = {'tabIndex': "-1", 'contentEditable': "false"}

# Base style for navigation tabs
BASE_NAV_STYLE = {'flex': 1, 'textAlign': 'center', 'padding': '15px', 'cursor': 'pointer', 
                  'margin': '5px', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}

# Default layout settings for Plotly graphs
GRAPH_LAYOUT = dict(template='plotly_white', font=dict(family='Arial, sans-serif', size=12, color='#333'),
                    title_font=dict(size=16, color='#0056D2'), paper_bgcolor='#ffffff', plot_bgcolor='#f8f9fa',
                    margin=dict(l=40, r=40, t=60, b=40), showlegend=True, 
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))

# Function to configure the Dash dashboard app
def setup_dashboard_app(app: Dash):
    # Define styles for active and inactive navigation tabs

    active_style, inactive_style = BASE_NAV_STYLE.copy(), BASE_NAV_STYLE.copy()
    active_style.update({'backgroundColor': '#4fc3f7', 'color': 'white'})  # Active tab style
    inactive_style.update({'backgroundColor': '#b3e5fc', 'color': '#333'})  # Inactive tab style

    # Set up the main layout of the dashboard
    app.layout = dbc.Container([

        # Title of the dashboard
        html.Div(html.H1('Data Consumption Tool', style={'textAlign': 'center', 'color': '#007BFF', **STYLE_NON_EDITABLE}), 
                 **PROPS_NON_EDITABLE),

        # Navigation bar with tabs
        html.Div([
            html.Div('Dashboard', id='nav-dashboard', className='nav-item', style=inactive_style, **PROPS_NON_EDITABLE),
            html.Div('Data Upload', id='nav-data-upload', className='nav-item', style=active_style, **PROPS_NON_EDITABLE),
            html.Div('Settings', id='nav-settings', className='nav-item', style=inactive_style, **PROPS_NON_EDITABLE),

        ], id='nav-bar', style={'display': 'flex', 'border': '1px solid #ddd', 'borderRadius': '5px', 
                                'marginBottom': '30px', 'marginTop': '10px', 'backgroundColor': '#ffffff',
                                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
        
        # Container for dynamic page content
        html.Div(id='page-content', style={'minHeight': '400px', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),

    ], fluid=True, style={'maxWidth': '1400px', 'padding': '20px', 'backgroundColor': '#ffffff', **STYLE_NON_EDITABLE})

    # Callback to update page content based on tab clicks
    @app.callback(Output('page-content', 'children'), 
                  [Input('nav-dashboard', 'n_clicks'), 
                   Input('nav-data-upload', 'n_clicks'), 
                   Input('nav-settings', 'n_clicks')])
    
    def update_page(*clicks):
        # Call helper function to generate content for the selected tab
        return get_page_content(dash.callback_context)

    # Callback to update styles of navigation tabs
    @app.callback([Output('nav-dashboard', 'style'), 
                   Output('nav-data-upload', 'style'),
                   Output('nav-settings', 'style')],
                  [Input('nav-dashboard', 'n_clicks'),
                   Input('nav-data-upload', 'n_clicks'),
                   Input('nav-settings', 'n_clicks')])
    
    def update_tab_styles(*clicks):
        # Get the context of the triggered event

        ctx = dash.callback_context
        # Default to 'Data Upload' tab if no click triggered, otherwise use clicked tab
        active_tab = 'nav-data-upload' if not ctx.triggered else ctx.triggered[0]['prop_id'].split('.')[0]

        # Initialize all tabs with inactive style
        styles = [inactive_style.copy(), inactive_style.copy(), inactive_style.copy()]

        # Set active style for the selected tab
        styles[['nav-dashboard', 'nav-data-upload', 'nav-settings'].index(active_tab)] = active_style.copy()

        return styles

    # Callback to handle file upload and reset actions
    @app.callback(Output('upload-output', 'children'), 
                  [Input('upload-data', 'contents'),
                   Input('reset-button', 'n_clicks')], 
                  [State('upload-data', 'filename')])
    
    def handle_file_upload(contents, reset_clicks, filename):
        # Get the context of the triggered event
        ctx = dash.callback_context

        # Check if reset button was clicked
        if ctx.triggered_id == 'reset-button':

            # Clear the stored data
            uploaded_data_store.clear()
            # Return message indicating dataset was cleared

            return html.P('Dataset cleared. Please upload a new file.', 
                          style={'color': '#dc3545', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)
        
        # Process the uploaded file
        return process_file_upload(contents, filename)

    # Helper function to prepare data for graphing
    def prepare_data(selected_cols):
        # Check if data exists in storage
        if 'data' not in uploaded_data_store or uploaded_data_store['data'].empty: return None, None

        # Get the stored DataFrame
        df = uploaded_data_store['data']

        # Downsample data if it exceeds maximum points
        if len(df) > MAX_POINTS: df = df.iloc[::len(df) // MAX_POINTS, :].copy()

        # Determine the x-axis column (priority: 'Date/Time', 'Date'+'Time', or first column)
        x_col = 'Date/Time' if 'Date/Time' in df.columns else \
                ('Date/Time' if 'Date' in df.columns and 'Time' in df.columns else df.columns[0])
        
        # Convert x-axis to datetime if applicable
        if x_col == 'Date/Time':
            df[x_col] = pd.to_datetime(
                df['Date/Time'] if 'Date/Time' in df.columns else df['Date'] + ' ' + df['Time'], 
                format='%m/%d/%Y %H:%M:%S' if 'Date/Time' in df.columns else None, errors='coerce')
            
        # Convert selected columns to numeric values
        for col in selected_cols: df[col] = pd.to_numeric(df.get(col, pd.Series()), errors='coerce')

        return df, x_col

    # Define callbacks for each graph type
    for graph_id, title, yaxis, input_id in [
        ('chiller-power-graph', 'Chiller Power', 'Power (kW)', 'chiller-power-checklist'),
        ('supply-temp-graph', 'Chiller Water Supply Temperature', 'Temperature (°C)', 'supply-temp-checklist'),
        ('return-temp-graph', 'Chiller Water Return Temperature', 'Temperature (°C)', 'return-temp-checklist')
    ]:
        
        # Callback to update graph based on selected columns
        @app.callback(Output(graph_id, 'figure'), 
                      Input(input_id, 'value'))
        
        def update_graph(cols): 
            # Prepare data for the graph
            df, x_col = prepare_data(cols or [])

            # Create a line graph if data exists, otherwise empty graph
            fig = px.line(df, x=x_col, y=cols or [], title=title, color_discrete_sequence=['#007bff', '#ff5733']) \
                    if df is not None else px.line()
            
            # Apply layout settings to the graph
            fig.update_layout(**GRAPH_LAYOUT, yaxis_title=yaxis)

            return fig

# Function to generate content for the selected page
def get_page_content(ctx):
    # Determine the active tab from the context
    tab_id = 'nav-data-upload' if not ctx.triggered else ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Content for the Dashboard tab
    if tab_id == 'nav-dashboard':
        # Check if data is available
        if 'data' in uploaded_data_store and not uploaded_data_store['data'].empty:

            df = uploaded_data_store['data']

            # Identify columns related to chiller power, supply temp, and return temp
            power_cols = [col for col in df.columns if 'chiller' in col.lower() and 'power' in col.lower()]
            supply_cols = [col for col in df.columns if ('supply' in col.lower() or 'chws' in col.lower()) and ('temp' in col.lower() or 't' in col.lower())]
            return_cols = [col for col in df.columns if ('return' in col.lower() or 'chwr' in col.lower() or 'ret' in col.lower()) and ('temp' in col.lower() or 't' in col.lower())]

            # Define sections for each graph type
            sections = [
                ('Chiller Power', 'chiller-power-checklist', power_cols, 'chiller-power-graph'),
                ('Supply Temperature', 'supply-temp-checklist', supply_cols, 'supply-temp-graph'),
                ('Return Temperature', 'return-temp-checklist', return_cols, 'return-temp-graph')
            ]

            return html.Div([
                # Display available columns if no specific columns detected
                html.P(f"Available columns in dataset: {', '.join(df.columns)}", 
                       style={'color': '#666', 'fontFamily': 'Arial, sans-serif', 'marginTop': '10px', **STYLE_NON_EDITABLE}, 
                       **PROPS_NON_EDITABLE) if not any([power_cols, supply_cols, return_cols]) else None,

                # Generate cards for each graph section
                *[dbc.Row(dbc.Col(dbc.Card([
                    dbc.CardHeader(html.H5(title, style={'color': '#0056D2', 'fontWeight': '600', 'textAlign': 'center', **STYLE_NON_EDITABLE}, 
                                          **PROPS_NON_EDITABLE)),
                    dbc.CardBody([
                        dcc.Checklist(id=check_id, options=[{'label': col, 'value': col} for col in cols], 
                                      value=cols, style={'marginBottom': '15px', 'fontFamily': 'Arial, sans-serif'}),
                        html.P(f"No columns detected for {title}.", style={'color': '#dc3545', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE) if not cols else None,

                        dcc.Graph(id=graph_id, style={'height': '350px'})
                    ])

                ], style={'boxShadow': '0 4px 6px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'marginBottom': '20px'}))) 

                for title, check_id, cols, graph_id in sections]
            ], style=STYLE_NON_EDITABLE, **PROPS_NON_EDITABLE)
        
        # Default content if no data is uploaded
        return html.Div([
            html.H3('Dashboard', style={'color': '#0056D2', 'marginBottom': '20px', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
            html.P('Upload a dataset to view visualizations.', style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)
        ], style=STYLE_NON_EDITABLE, **PROPS_NON_EDITABLE)

    # Content for the Data Upload tab
    elif tab_id == 'nav-data-upload':
        return dbc.Card(dbc.CardBody([
            html.P('Upload only .csv files', style={'color': '#dc3545', 'marginBottom': '15px', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),

            # File upload component
            dcc.Upload(id='upload-data', 
                       children=html.Div(['Drag and Drop or ', html.A('Select Files', style={'color': '#007bff', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)], 
                                        style=STYLE_NON_EDITABLE, **PROPS_NON_EDITABLE),
                       style={'width': '100%', 'height': '80px', 'lineHeight': '80px', 'borderWidth': '2px', 'borderStyle': 'dashed', 
                              'borderRadius': '8px', 'textAlign': 'center', 'backgroundColor': '#f8f9fa', 'borderColor': '#ced4da', 
                              'marginBottom': '20px', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, multiple=False),

            # Reset button to clear uploaded data
            dbc.Button('Reset Dataset', id='reset-button', color='danger', style={'marginRight': '10px'}),

            # Loading indicator and output area for upload status
            dcc.Loading(id="loading-upload", children=html.Div(id='upload-output', style={'marginTop': '20px', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, 
                                                               **PROPS_NON_EDITABLE), type="circle", color='#007bff')

        ]), style={'boxShadow': '0 4px 6px rgba(0,0,0,0.1)', 'borderRadius': '8px', **STYLE_NON_EDITABLE})

    # Placeholder content for the Settings tab
    return dbc.Card(dbc.CardBody(
        html.P("Settings page under development.", style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)
    ), style={'boxShadow': '0 4px 6px rgba(0,0,0,0.1)', 'borderRadius': '8px', **STYLE_NON_EDITABLE})

# Function to process uploaded CSV files
def process_file_upload(contents, filename):
    # Access global data store
    global uploaded_data_store

    # Check if file content is provided
    if contents:
        # Split and decode base64 content
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            # Validate file format (only CSV allowed)
            if not filename.endswith('.csv'):
                return html.Div(html.P('Unsupported file format. Please upload a valid CSV file.', 
                                       style={'color': '#dc3545', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE), 
                               style=STYLE_NON_EDITABLE, **PROPS_NON_EDITABLE)
            
            # Read CSV data into a DataFrame
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

            # Store the DataFrame globally
            uploaded_data_store['data'] = df

            # Identify columns for chiller power, supply temp, and return temp
            power_cols = [col for col in df.columns if 'chiller' in col.lower() and 'power' in col.lower()]
            supply_cols = [col for col in df.columns if ('supply' in col.lower() or 'chws' in col.lower()) and ('temp' in col.lower() or 't' in col.lower())]
            return_cols = [col for col in df.columns if ('return' in col.lower() or 'chwr' in col.lower() or 'ret' in col.lower()) and ('temp' in col.lower() or 't' in col.lower())]

            # Return success message with dataset details
            return html.Div([
                html.P(f'Successfully uploaded: {filename}', style={'fontWeight': 'bold', 'color': '#333', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
                html.P(f'Dataset has {len(df)} rows and {len(df.columns)} columns.', style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
                html.P(f"Detected Chiller Power columns: {', '.join(power_cols) if power_cols else 'None'}", style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
                html.P(f"Detected Supply Temp columns: {', '.join(supply_cols) if supply_cols else 'None'}", style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
                html.P(f"Detected Return Temp columns: {', '.join(return_cols) if return_cols else 'None'}", style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
                html.P(f"All columns in dataset: {', '.join(df.columns)}", style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)
            ], style=STYLE_NON_EDITABLE, **PROPS_NON_EDITABLE)
        
        # Handle errors during file processing
        except Exception as e:
            return html.Div([html.P('There was an error processing the file.', style={'color': '#dc3545', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
                             html.P(str(e), style={'color': '#dc3545', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)], 
                           style=STYLE_NON_EDITABLE, **PROPS_NON_EDITABLE)
        
    # Return status of existing data if no new file uploaded
    return html.Div([html.P('Previously uploaded file is still available.', style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE),
                    html.P(f'Dataset has {len(uploaded_data_store["data"])} rows and {len(uploaded_data_store["data"].columns)} columns.', 
                           style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)], 
                   style=STYLE_NON_EDITABLE, **PROPS_NON_EDITABLE) if 'data' in uploaded_data_store else \
           html.P('No file uploaded yet.', style={'color': '#666', 'fontFamily': 'Arial, sans-serif', **STYLE_NON_EDITABLE}, **PROPS_NON_EDITABLE)