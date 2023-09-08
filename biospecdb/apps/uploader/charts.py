from io import StringIO
from typing import Optional

import pandas as pd
import plotly.express as px

from uploader.models import Disease


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
        return

    if df is None:
        return

    fig = px.pie(df, values="count", names="disease", title=f"SQL query: '{result.sql}'")
    return fig_to_html(fig)


def get_line_chart(result: "QueryResult") -> Optional[str]:  # noqa: F821
    raise None
