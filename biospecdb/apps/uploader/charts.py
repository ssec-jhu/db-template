from io import StringIO
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from django.conf import settings
from biospecdb.util import spectral_data_from_csv
from uploader.models import Disease, SpectralData


def fig_to_html(fig) -> str:
    buffer = StringIO()
    fig.write_html(buffer, auto_open=False, full_html=False)
    buffer.seek(0)
    graph = buffer.getvalue()
    buffer.close()
    return graph


def count_bool_diseases(result: "QueryResult"):  # noqa: F821
    if len(result.data) < 1:
        return

    bool_diseases = [d.name for d in Disease.objects.all() if d.value_class == "BOOL"]
    df = pd.DataFrame(result.data, columns=result.header_strings)
    df = df[bool_diseases].replace({"True": True, "False": False})
    df = pd.DataFrame([(column, df[column].values.sum()) for column in df], columns=("disease", "count"))
    return df


def get_pie_chart(result: "QueryResult") -> Optional[str]:  # noqa: F821
    try:
        df = count_bool_diseases(result)
    except Exception:
        if settings.DEBUG:
            raise
        else:
            return

    if df is None:
        return

    fig = px.pie(df, values="count", names="disease", title=f"SQL query: '{result.sql}'")
    return fig_to_html(fig)


def get_line_chart(result: "QueryResult") -> Optional[str]:  # noqa: F821
    if len(result.data) < 1:
        return

    try:
        df = pd.DataFrame(result.data, columns=result.header_strings)
        df = df[["patient_id", SpectralData.data.field.name]]

        fig = go.Figure()
        fig.update_layout(xaxis_title="Wavelength",
                          yaxis_title="Intensity",
                          title=f"Spectral Data for SQL query: '{result.sql}'"
)
        for _, (patient_id, filename) in df.iterrows():
            spectral_data = spectral_data_from_csv(filename)
            fig.add_scatter(x=spectral_data["wavelength"],
                            y=spectral_data["intensity"],
                            name=patient_id)

        return fig_to_html(fig)
    except Exception:
        if settings.DEBUG:
            raise
        else:
            return
