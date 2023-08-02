import pytest

from uploader.models import FullPatientView, SymptomsView, VisitSymptomsView, Symptom
from uploader.sql import execute_sql

def test_symptoms_view(mock_data):
    all_view_data = SymptomsView.update_view(limit=None)
    all_symptoms = Symptom.objects.all()
    assert len(all_symptoms) > 1  # Check non-empty.
    assert len(all_view_data) == len(all_symptoms)


def test_symptoms_view_django_model(mock_data):
    all_view_data = SymptomsView.update_view(limit=None)
    all_django_view_data = SymptomsView.objects.all()
    assert len(all_view_data) > 1  # Check non-empty.
    assert len(all_view_data) == len(all_django_view_data)


def test_symptoms_view_django_model_filter(mock_data):
    SymptomsView.update_view()
    week_long_symptoms_1 = execute_sql(f"""
                                       select *
                                       from {SymptomsView._meta.db_table}
                                       where days_symptomatic = 7
                                       """)
    week_long_symptoms_2 = SymptomsView.objects.filter(days_symptomatic=7)
    assert len(week_long_symptoms_1) > 1  # Check non-empty.
    assert len(week_long_symptoms_1) == len(week_long_symptoms_2)
