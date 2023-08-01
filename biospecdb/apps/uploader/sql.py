import re

from django.db import connection
from django.db.utils import OperationalError


def secure_name(name):
    if re.search(name, r"[^_a-zA-Z]"):
        raise RuntimeError(f"SQL security issue! Expected table_name consisting of only [_a-zA-Z] but got '{name}'")


def execute_sql(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params=params)
        result = cursor.fetchall()
        if not result:
            return
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in result]


def drop_view(view):
    secure_name(view)
    try:
        execute_sql(f"drop view {view}")  # nosec B608
    except OperationalError as error:
        if "no such view:" not in str(error):
            raise


def update_view(view, sql, params=None, check=True, limit=1):
    secure_name(view)
    drop_view(view)
    execute_sql(sql, params=params)

    # The view isn't actually used upon creation so may contain latent errors. To check for errors, we query it so that
    # it complains upon creation not later upon usage.
    if check:
        sql = f"select * from {view}"  # nosec B608
        params = []
        if limit:
            sql += " limit %s"
            params.append(limit)
        return execute_sql(sql, params=params)
