# plotly dash example
from pathlib import Path


from dash import Dash, html, dash_table, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd

from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware



external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
dash_app = Dash(__name__, requests_pathname_prefix='/dash/', external_stylesheets=external_stylesheets)

app = FastAPI()
app.mount("/dash", WSGIMiddleware(dash_app.server))
# uvicorn example:app
# Then goto http://127.0.0.1:8000/dash/


META_PATH = Path("../../../../data/METADATA_barauna2021ultrarapid.xlsx")
SPEC_PATH = Path("../../../../data/SPECTRA_barauna2021ultrarapid.xlsx")


def ingest_data(filename):
    suffix = filename.suffix
    if suffix == ".xlsx":
        df = pd.read_excel(filename)
    elif suffix == ".csv":
        df = pd.read_csv(filename)
    else:
        raise FileNotFoundError(f"'{suffix}' is not a valid file type of (.csv, .xlsx)")
    return df


def clean_meta(df):
    df = df.rename(columns=lambda x: x.lower().replace(' ', '_')) \
            .dropna(subset=['patient_id']) \
            .set_index('patient_id')
    return df


def clean_spec(df):
    df = df.rename(columns={"PATIENT ID": "patient_id"})
    spec_only = df.drop(columns=["patient_id"], inplace=False)
    wavelengths = spec_only.columns.tolist()
    specv = spec_only.values.tolist()
    freqs = [wavelengths for i in range(len(specv))]
    return pd.DataFrame({"wavelength": freqs, "intensity": specv}, index=df["patient_id"])


meta_df = clean_meta(ingest_data(META_PATH))
spec_df = clean_spec(ingest_data(SPEC_PATH))


dash_app.layout = html.Div([
    html.H1(children='Patient Data', style={'textAlign': 'center'}),
    dash_table.DataTable(data=meta_df.to_dict('records'), page_size=10),
    html.H2("Patients with a cough:"),
    dcc.RadioItems(options=["female", "male"], value='female', id='controls-and-radio-item'),
    dcc.Graph(figure={}, id='controls-and-graph'),
    html.P("Max age"),
    dcc.Slider(id="max age", min=0, max=130, value=130,
               marks={0: '0', 130: '130'}),
    html.H2("Individual patient sample spectral data:"),
    dcc.Dropdown(spec_df.index.unique(), 1, id='dropdown-selection'),
    dcc.Graph(id='graph-content'),
])


@callback(
    Output(component_id='controls-and-graph', component_property='figure'),
    Input(component_id='controls-and-radio-item', component_property='value'),
    Input(component_id="max age", component_property='value')
)
def update_meta_graph(gender, age):
    gender = "F" if gender == "female" else "M"
    data = meta_df[(meta_df["gender_(m/f)"] == gender) & (meta_df["age"] <= age)]
    fig = px.histogram(data, x='cough', histfunc='sum')
    return fig


@callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_spec_graph(value):
    data = spec_df.loc[value]
    return px.line(x=data.wavelength, y=data.intensity)
