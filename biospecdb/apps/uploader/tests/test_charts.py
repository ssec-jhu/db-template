import pytest
from django.conf import settings

from conftest import SimpleQueryFactory
from uploader.charts import count_bool_diseases, get_pie_chart, get_line_chart


@pytest.fixture()
def query(request):
    sql_marker = request.node.get_closest_marker("sql")
    sql = sql_marker.args[0] if sql_marker and sql_marker.args[0] else "select * from uploader_spectraldata"

    q = SimpleQueryFactory(sql=sql)
    results = q.execute_query_only()
    return results


@pytest.mark.django_db(databases=["default", "bsr"])
class TestCharts:
    def test_empty_count_bool_diseases(self, query):
        df = count_bool_diseases(query)
        assert df is None

    @pytest.mark.sql("select * from full_patient")
    def test_get_pie_chart(self, mock_data_from_files, sql_views, query):
        html = get_pie_chart(query)
        assert html

    @pytest.mark.sql("select * from full_patient")
    def test_get_line_chart(self, mock_data_from_files, sql_views, query):
        html = get_line_chart(query)
        assert html

    def test_empty_get_pie_chart(self, query):
        assert get_pie_chart(query) is None

    def test_empty_get_line_chart(self, query):
        assert get_line_chart(query) is None

    def test_get_pie_chart_exceptions(self, monkeypatch, mock_data_from_files, query):
        assert get_pie_chart(query) is None

        monkeypatch.setattr(settings, "DEBUG", True)
        with pytest.raises(KeyError):
            get_pie_chart(query)

    def test_get_line_chart_exceptions(self, monkeypatch, mock_data_from_files, query):
        assert get_line_chart(query) is None

        monkeypatch.setattr(settings, "DEBUG", True)
        with pytest.raises(KeyError):
            get_line_chart(query)
