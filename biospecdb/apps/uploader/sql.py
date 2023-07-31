from django.db import connection
from django.db.utils import OperationalError


def execute_sql(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchall()
        if not result:
            return
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in result]


def drop_view(view):
    try:
        execute_sql(f"drop view {view}")
    except OperationalError:
        pass


def update_view(view, sql, check=True, limit=1):
    drop_view(view)
    execute_sql(sql)
    if check:
        sql = f"select * from {view}" + (f" limit {limit}" if limit else '')
        return execute_sql(sql)
