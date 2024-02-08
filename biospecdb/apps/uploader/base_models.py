from enum import auto

from django.db import models, transaction
from django.utils.module_loading import import_string

import biospecdb.util
from uploader.sql import drop_view, update_view


class BasedModel(models.Model):
    class Meta:
        abstract = True

    @classmethod
    def get_column_names(cls):
        # Note: This is a set of model.field.name and not model.field.verbose_name.
        exclude = {"created at",
                   "data",
                   "date",
                   "id",
                   "spectral data file",
                   "updated at"}

        if hasattr(cls, "parse_fields_from_pandas_series"):  # Only models with this func have bulk data upload columns.
            return {field.verbose_name.lower() for field in cls._meta.fields if not field.is_relation} - exclude

        return ()


class DatedModel(BasedModel):
    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TextChoices(models.TextChoices):
    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return

        for item in cls:
            if value.lower() in (item.name.lower(),
                                 item.label.lower(),
                                 item.value.lower(),
                                 item.name.lower().replace('_', '-'),
                                 item.label.lower().replace('_', '-'),
                                 item.value.lower().replace('_', '-')):
                return item


class Types(TextChoices):
    BOOL = auto()
    STR = auto()
    INT = auto()
    FLOAT = auto()

    def cast(self, value):
        if value is None:
            return

        if self.name == "BOOL":
            return biospecdb.util.to_bool(value)
        elif self.name == "STR":
            return str(value)
        elif self.name == "INT":
            return int(value)
        elif self.name == "FLOAT":
            return float(value)
        else:
            raise NotImplementedError


class SqlView:
    sql_view_dependencies = tuple()
    db = "default"

    # TODO: Add functionality to auto create own view if doesn't already exist.

    @classmethod
    def sql(cls):
        """ Returns the SQL string and an optional list of params used in string. """
        raise NotImplementedError

    @classmethod
    def drop_view(cls, *args, **kwargs):
        if "db" not in kwargs:
            kwargs["db"] = cls.db
        return drop_view(cls._meta.db_table, *args, **kwargs)

    @classmethod
    @transaction.atomic(using="bsr")
    def update_view(cls, *args, **kwargs):
        """ Update view and view dependencies.

            NOTE: This func is transactional such that all views are updated or non are. However, also note that this
                  can result in the views being rolled back to, being stale and outdated (depending on the cause of the
                  update).
        """
        if "db" not in kwargs:
            kwargs["db"] = cls.db

        for view_dependency in cls.sql_view_dependencies:
            view_dependency.update_view(*args, **kwargs)

        sql, params = cls.sql()
        return update_view(cls._meta.db_table, sql, *args, params=params, **kwargs)


class ModelWithViewDependency(DatedModel):
    class Meta:
        abstract = True

    sql_view_dependencies = None

    @transaction.atomic(using="bsr")
    def save(self, *args, update_view=True, **kwargs):
        super().save(*args, **kwargs)

        if update_view and self.sql_view_dependencies:
            for sql_view in self.sql_view_dependencies:
                if isinstance(sql_view, str):
                    sql_view = import_string(sql_view)
                sql_view.update_view()

    def asave(self, *args, **kwargs):
        raise NotImplementedError("See https://github.com/ssec-jhu/biospecdb/issues/66")
