from enum import auto

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import connection, models, transaction
from django.utils.module_loading import import_string
from uploader.sql import drop_view, update_view

import biodb.util


class BasedModel(models.Model):
    class Meta:
        abstract = True

    @classmethod
    def get_column_names(cls, help_text=False):
        # Note: This is a set of model.field.name and not model.field.verbose_name.
        exclude = {"created at", "data", "date", "id", "array data file", "updated at"}

        if hasattr(cls, "parse_fields_from_pandas_series"):  # Only models with this func have bulk data upload columns.
            if help_text:
                info = {
                    field.verbose_name.lower(): field.help_text for field in cls._meta.fields if not field.is_relation
                }
                fields = info.keys() - exclude

                return [(k, v) for k, v in info.items() if k in fields]
            else:
                return {field.verbose_name.lower() for field in cls._meta.fields if not field.is_relation} - exclude

        return set()

    def full_clean(
        self,
        exclude=None,
        validate_unique=True,
        validate_constraints=True,
        fail_early=settings.FAIL_EARLY_IN_FULL_CLEAN,
    ):
        # Pulled directly from django.db.models.Model.full_clean with added custom option to fail early.
        """
        Call clean_fields(), clean(), validate_unique(), and
        validate_constraints() on the model. Raise a ValidationError for any
        errors that occur.
        """
        errors = {}
        if exclude is None:
            exclude = set()
        else:
            exclude = set(exclude)

        try:
            self.clean_fields(exclude=exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)
            if fail_early:
                raise ValidationError(errors)

        # Form.clean() is run even if other validation fails, so do the
        # same with Model.clean() for consistency.
        try:
            self.clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)
            if fail_early:
                raise ValidationError(errors)

        # Run unique checks, but only for fields that passed validation.
        if validate_unique:
            for name in errors:
                if name != NON_FIELD_ERRORS and name not in exclude:
                    exclude.add(name)
            try:
                self.validate_unique(exclude=exclude)
            except ValidationError as e:
                errors = e.update_error_dict(errors)
                if fail_early:
                    raise ValidationError(errors)

        # Run constraints checks, but only for fields that passed validation.
        if validate_constraints:
            for name in errors:
                if name != NON_FIELD_ERRORS and name not in exclude:
                    exclude.add(name)
            try:
                self.validate_constraints(exclude=exclude)
            except ValidationError as e:
                errors = e.update_error_dict(errors)
                if fail_early:
                    raise ValidationError(errors)

        if errors:
            raise ValidationError(errors)


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
            if value.lower() in (
                item.name.lower(),
                item.label.lower(),
                item.value.lower(),
                item.name.lower().replace("_", "-"),
                item.label.lower().replace("_", "-"),
                item.value.lower().replace("_", "-"),
            ):
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
            return biodb.util.to_bool(value)
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

    @staticmethod
    def _create_field_str_list(prefix, model, extra_excluded_field_names=None):
        excluded_field_names = ["created_at", "updated_at"]
        if extra_excluded_field_names:
            excluded_field_names.extend(extra_excluded_field_names)
        excluded_field_names = [x.lower() for x in excluded_field_names]
        return ",".join(
            [
                f"{prefix}.{field.name} as {model.__name__.lower()}_{field.name}"
                for field in model._meta.fields
                if (not field.is_relation and field.name.lower() not in excluded_field_names)
            ]
        )

    @classmethod
    def sql(cls):
        """Returns the SQL string and an optional list of params used in string."""
        raise NotImplementedError

    @classmethod
    def drop_view(cls, *args, drop_dependencies=False, **kwargs):
        if "db" not in kwargs:
            kwargs["db"] = cls.db

        if drop_dependencies:
            for view_dependency in cls.sql_view_dependencies:
                view_dependency.drop_view(*args, drop_dependencies=drop_dependencies, **kwargs)

        return drop_view(cls._meta.db_table, *args, **kwargs)

    @classmethod
    @transaction.atomic(using="bsr")
    def update_view(cls, *args, **kwargs):
        """Update view and view dependencies.

        NOTE: This func is transactional such that all views are updated or non are. However, also note that this
              can result in the views being rolled back to, being stale and outdated (depending on the cause of the
              update).
        """
        if "db" not in kwargs:
            kwargs["db"] = cls.db

        sql, params = cls.sql()

        if connection.vendor == "postgresql":
            # Drop views on the way down so that all are gone before any are created.
            # psql allows only cascading view deletions so this order is necessary.
            cls.drop_view(*args, **kwargs)

        for view_dependency in cls.sql_view_dependencies:
            view_dependency.update_view(*args, **kwargs)

        return update_view(cls._meta.db_table, sql, *args, params=params, **kwargs)


class ModelWithViewDependency(DatedModel):
    class Meta:
        abstract = True

    # Note: This should only inc. direct dependencies and let the view itself handle its own subsequent dependencies.
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
        raise NotImplementedError()
