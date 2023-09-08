from typing import Optional

import explorer.charts


def get_pie_chart(result: "QueryResult") -> Optional[str]:
    raise NotImplementedError


def get_line_chart(result: "QueryResult") -> Optional[str]:
    raise NotImplementedError


explorer.charts.get_pie_chart = get_pie_chart
explorer.charts.get_line_chart = get_line_chart
