from io import StringIO
from pathlib import Path

import pytest

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db.models import Q
from django.db.utils import OperationalError

from uploader.models import Center, Observable, UploadedFile, ArrayData
from uploader.sql import execute_sql

User = get_user_model()


@pytest.mark.django_db(databases=["default", "bsr"])
class TestUpdateSqlViews:
    def test_exception(self):
        out = StringIO()
        with pytest.raises(CommandError, match="No model with view 'some_random_view' exists"):
            call_command("update_sql_views", "some_random_view", stdout=out)

    def test_ok(self, mock_data_from_files):
        # Check views don't exist.
        with pytest.raises(OperationalError, match="no such table: flat_view"):
            execute_sql("SELECT * FROM flat_view LIMIT 1", db="bsr")
        with pytest.raises(OperationalError, match="no such table: v_observations"):
            execute_sql("SELECT * FROM v_observations LIMIT 1", db="bsr")
        with pytest.raises(OperationalError, match="no such table: v_visit_observations"):
            execute_sql("SELECT * FROM v_visit_observations LIMIT 1", db="bsr")

        # Update views.
        call_command("update_sql_views", "flat_view")

        # Check they exist.
        execute_sql("SELECT * FROM flat_view LIMIT 1", db="bsr")
        execute_sql("SELECT * FROM v_observations LIMIT 1", db="bsr")
        execute_sql("SELECT * FROM v_visit_observations LIMIT 1", db="bsr")

        # Drop views.
        call_command("update_sql_views", "--drop_only", "flat_view")

        # Check views don't exist.
        with pytest.raises(OperationalError, match="no such table: flat_view"):
            execute_sql("SELECT * FROM flat_view LIMIT 1", db="bsr")
        with pytest.raises(OperationalError, match="no such table: v_observations"):
            execute_sql("SELECT * FROM v_observations LIMIT 1", db="bsr")
        with pytest.raises(OperationalError, match="no such table: v_visit_observations"):
            execute_sql("SELECT * FROM v_visit_observations LIMIT 1", db="bsr")


@pytest.mark.django_db(databases=["default", "bsr"])
class TestPruneFiles:

    def test_empty(self):
        out = StringIO()
        call_command("prune_files", stdout=out)
        assert "No orphaned files detected." in out.getvalue()

    @pytest.mark.parametrize(("cmd", "delete", "expected"),
                             ((("prune_files",), True, (0, 0)),
                              (("prune_files", "--dry_run"), True, (0, 0)),
                              (("prune_files",), False, (0, 0)),
                              (("prune_files", "--dry_run"), False, (2, 10))))
    def test_core(self, mock_data_from_files, cmd, delete, expected):
        def get_file_count(path):
            return len(list(Path(path).glob('*')))

        # Check objects exist.
        assert UploadedFile.objects.count() == 1
        assert ArrayData.objects.count() == 10

        # Check files exist.
        assert get_file_count(UploadedFile.UPLOAD_DIR) == 2
        assert get_file_count(ArrayData.UPLOAD_DIR) == 10

        # Delete objects and files (if delete).
        def delete_objs(model):
            for obj in model.objects.all():
                obj.delete(delete_files=delete)
            assert model.objects.count() == 0
        delete_objs(UploadedFile)
        delete_objs(ArrayData)

        # Run prune_files command.
        out = StringIO()
        call_command(*cmd, stdout=out)

        # Check files have been deleted.
        assert get_file_count(UploadedFile.UPLOAD_DIR) == expected[0]
        assert get_file_count(ArrayData.UPLOAD_DIR) == expected[1]

        out.seek(0)
        assert len(out.readlines()) == 1 if delete else 13


@pytest.mark.django_db(databases=["default", "bsr"])
class TestGetColumnNames:
    n_non_observables = 22

    @pytest.fixture
    def more_observables(self, centers):
        category = (x.value for x in Observable.Category)
        names = iter(("blah", "foo", "bar", "huh"))
        for center in Center.objects.all():
            name = next(names)
            observable = Observable.objects.create(name=name,
                                                   alias=name,
                                                   description=name,
                                                   category=next(category))
            observable.center.set([center])
            observable.full_clean()
            observable.save()

    def test_observables_only(self, observables):
        out = StringIO()
        call_command("get_column_names", "--exclude_non_observables", stdout=out)
        assert Observable.objects.count()
        out.seek(0)
        assert Observable.objects.count() == len(out.readlines())

    def test_empty_observables(self):
        out = StringIO()
        call_command("get_column_names", "--exclude_non_observables", stdout=out)
        assert not Observable.objects.count()
        out.seek(0)
        assert len(out.readlines()) == 0

    def test_non_observables_only(self, observables):
        out = StringIO()
        call_command("get_column_names", "--exclude_observables", stdout=out)
        out.seek(0)
        assert len(out.readlines()) == self.n_non_observables

    def test_all(self, observables):
        out = StringIO()
        call_command("get_column_names", stdout=out)
        assert Observable.objects.count()
        out.seek(0)
        assert len(out.readlines()) == Observable.objects.count() + self.n_non_observables

    @pytest.mark.parametrize("center_filter", ("JHU",
                                               "imperial college london",
                                               "oxford university",
                                               "d2160c33-0bbc-4605-a2ce-7e83296e7c84",
                                               "None"))
    def test_center_filter(self, observables, more_observables, center_filter):
        out = StringIO()
        call_command("get_column_names", "--exclude_non_observables", f"--center={center_filter}", stdout=out)

        if center_filter == "None":
            queryset = Observable.objects.filter(center=None)
        else:
            queryset = Observable.objects.filter(Q(center__name__iexact=center_filter) |
                                                 Q(center__id__iexact=center_filter))
        assert queryset.count()
        out.seek(0)
        assert len(out.readlines()) == queryset.count()

    @pytest.mark.parametrize(("center_filter", "category_filter"), (("JHU", "bloodwork"),
                                                                    ("imperial college london", "comorbidity"),
                                                                    ("oxford university", "drug"),
                                                                    ("d2160c33-0bbc-4605-a2ce-7e83296e7c84", "bloodwork")))
    def test_category_and_center_filter(self, observables, more_observables, center_filter, category_filter):
        out = StringIO()
        call_command("get_column_names",
                     "--exclude_non_observables",
                     f"--center={center_filter}",
                     f"--category={category_filter}",
                     stdout=out)

        queryset = Observable.objects.filter(Q(center__name__iexact=center_filter) |
                                             Q(center__id__iexact=center_filter)).filter(
            category__iexact=category_filter)
        out.seek(0)
        assert len(out.readlines()) == queryset.count()

    @pytest.mark.parametrize("category_filter", ("symptom",
                                                 "comorbidity",
                                                 "test"))
    def test_category(self, observables, category_filter):
        out = StringIO()
        call_command("get_column_names",
                     "--exclude_non_observables",
                     f"--category={category_filter}",
                     stdout=out)

        queryset = Observable.objects.filter(category__iexact=category_filter)
        assert queryset.count()
        out.seek(0)
        assert len(out.readlines()) == queryset.count()

    def test_exception(self):
        with pytest.raises(CommandError, match="Unrecognized observable category"):
            out = StringIO()
            call_command("get_column_names",
                         "--exclude_non_observables",
                         f"--category={'this is not a category '}",
                         stdout=out)

    def test_descriptions(self, observables):
        out = StringIO()
        call_command("get_column_names",
                     "--exclude_non_observables",
                     "--descriptions",
                     stdout=out)
        queryset = Observable.objects.all()
        assert queryset.count()
        out.seek(0)
        info = out.readlines()
        assert len(info) == queryset.count()
        for line in info:
            name, description = line.split(',')
            assert Observable.objects.get(alias__iexact=name.strip()).description.strip() == description.strip()

    @pytest.mark.parametrize("include", (True, False))
    def test_instrument(self, observables, include):
        out = StringIO()
        if include:
            call_command("get_column_names", "--include_instrument_fields", stdout=out)
        else:
            call_command("get_column_names", stdout=out)
        out.seek(0)
        if include:
            assert "instrument" in out.read()
        else:
            assert "instrument" not in out.read()


@pytest.mark.django_db(databases=["default", "bsr"])
class TestMakeSuperUser:
    def test_existing_user(self, centers):
        user = "admin"
        assert not User.objects.count()

        options = [f"--username={user}",
                   "--noinput",
                   "--email=admin@site.com",
                   "--center=16721944-ff91-4adf-8fb3-323b99aba801"]

        cmd = ("createsuperuser", *options)
        call_command(*cmd)
        assert User.objects.get(username=user)

        with pytest.raises(CommandError):
            call_command(*cmd)

        call_command(*("makesuperuser", *options))

        with pytest.raises(CommandError, match="That username is already taken"):
            call_command(*("makesuperuser", "--fail", *options))
