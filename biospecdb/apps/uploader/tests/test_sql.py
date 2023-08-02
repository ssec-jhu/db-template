import pytest

from django.core.exceptions import SuspiciousOperation
from django.db.utils import OperationalError

from uploader.models import Disease
from uploader.sql import drop_view, execute_sql, secure_name, update_view


def test_ok_secure_name():
    secure_name("my_table1")


def test_not_ok_secure_name():
    with pytest.raises(SuspiciousOperation):
        secure_name("; drop view my_table")


def test_execute_sql(db, diseases):
    results = execute_sql("select * from uploader_disease order by name")
    diseases = Disease.objects.all().order_by("name")
    for d1, d2 in zip(results, diseases):
        assert d1["name"] == d2.name


def test_drop_nonexistent_view(db):
    drop_view("khbihb")


def test_update_view(db, diseases):
    view = "my_view"
    resp1 = update_view(view,
                        f"""
                        create view {view} as
                        select *
                        from uploader_disease
                        """,
                        check=True,
                        limit=None
                        )

    resp2 = execute_sql(f"select * from {view}")
    assert resp1 == resp2


def test_non_persistent_test_view(db):
    with pytest.raises(OperationalError, match="no such table:"):
        execute_sql("select * from my_view")


def test_update_view_limit(db, diseases):
    view = "my_view"
    limit = 1

    resp1 = update_view(view,
                        f"""
                        create view {view} as
                        select *
                        from uploader_disease
                        """,
                        check=True,
                        limit=limit
                        )
    assert len(resp1) == limit


def test_update_view_check(db, diseases):
    view = "my_view"

    with pytest.raises(OperationalError, match="syntax error"):
        update_view(view,
                    f"""
                    ceate view {view} as -- note typo in create
                    select *
                    from uploader_disease
                    """,
                    check=True,
                    )


def test_drop_view(db, diseases):
    view = "my_view"
    update_view(view,
                f"""
                    create view {view} as
                    select *
                    from uploader_disease
                    """,
                )
    resp = execute_sql(f"select * from {view}")
    assert len(resp) == len(Disease.objects.all())
    drop_view(view)
    with pytest.raises(OperationalError, match="no such table:"):
        execute_sql(f"select * from {view}")


