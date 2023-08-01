from django.db import connection
from django.db.utils import OperationalError


def execute_sql(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params=params)
        result = cursor.fetchall()
        if not result:
            return
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in result]


def drop_view(view):
    try:
        execute_sql("drop view %s", params=[view])
    except OperationalError:
        pass


def update_view(view, sql, params=None, check=True, limit=1):
    drop_view(view)
    execute_sql(sql, params=params)

    # The view isn't actually used upon creation so may contain latent errors. To check for errors, we query it so that
    # it complains upon creation not later upon usage.
    if check:
        sql = "select * from %s"
        params = [view]
        if limit:
            sql += " limit %s"
            params.append(limit)
        return execute_sql(sql, params=params)
