import logging
from io import StringIO
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import uploader.io
from uploader.models import ArrayData, Observable, Patient

from biodb.util import to_uuid

logger = logging.getLogger(__name__)


def fig_to_html(fig) -> str:
    """Convert a ploty figure to html."""
    buffer = StringIO()
    fig.write_html(buffer, auto_open=False, full_html=False)
    buffer.seek(0)
    graph = buffer.getvalue()
    buffer.close()
    return graph


def count_bool_observables(result: "QueryResult"):  # noqa: F821
    """Count boolean observables present in data result."""
    if len(result.data) < 1:
        return

    bool_observables = [d.name for d in Observable.objects.all() if d.value_class == "BOOL"]
    df = pd.DataFrame(result.data, columns=result.header_strings)
    cols = set(bool_observables) & set(df.columns)
    if not cols:
        return
    df = df[list(cols)]
    df.replace({"True": True, "False": False}, inplace=True)
    return df.sum()


def get_pie_chart(result: "QueryResult") -> Optional[str]:  # noqa: F821
    """Generate ploty pi chart of boolean Observation data present in data result."""
    try:
        counts = count_bool_observables(result)

        if counts is None:
            return

        fig = px.pie(counts, values=counts.values, names=counts.index, title=f"SQL query: '{result.sql}'")
        return fig_to_html(fig)
    except Exception as error:
        logger.exception(f"Exception raised from `get_pie_chart`: {error}")
        return


def get_line_chart(result: "QueryResult") -> Optional[str]:  # noqa: F821
    """Generate ploty line chart of array data present in data result."""

    if len(result.data) < 1:
        return

    try:
        df = pd.DataFrame(result.data, columns=result.header_strings)

        if Patient.patient_id.field.name not in df.columns or ArrayData.data.field.name not in df.columns:
            return
        df = df[[Patient.patient_id.field.name, ArrayData.data.field.name]]

        fig = go.Figure()
        fig.update_layout(xaxis_title="x", yaxis_title="y", title=f"Array Data for SQL query: '{result.sql}'")
        for row in df.itertuples():
            array_data = uploader.io.read_array_data(row.data)
            assert to_uuid(array_data.patient_id) == to_uuid(row.patient_id)
            fig.add_scatter(x=array_data.x, y=array_data.y, name=str(row.patient_id))

        return fig_to_html(fig)
    except Exception as error:
        logger.error(f"Exception raised from `get_line_chart`: {error}")
        return
