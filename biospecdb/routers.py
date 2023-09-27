class BaseRouter:
    route_app_labels = {}
    exclude_app_labels = {}
    db = None

    # NOTE: For the funcs below returning None := ambivalence (Returns None if there is no suggestion.),
    # whilst False := don't route to db. See https://docs.djangoproject.com/en/4.2/topics/db/multi-db/#database-routers
    # However, the main routing code only iterates over all routers if they return None, e.g. a router returning
    # False will exit the routing iteration just as it does when returning True - router order matters!
    def _is_allowed(self, obj):
        return (obj not in self.exclude_app_labels) and (obj in self.route_app_labels)

    def db_for_read(self, model, **hints):
        """ Suggest the database that should be used for read operations for objects of type model.
            If a database operation is able to provide any additional information that might assist in selecting a
            database, it will be provided in the hints dictionary. Details on valid hints are provided below.

            Returns None if there is no suggestion.
        """
        if self._is_allowed(model._meta.app_label):
            return self.db
        return None

    def db_for_write(self, model, **hints):
        """ Suggest the database that should be used for writes of objects of type Model.
            If a database operation is able to provide any additional information that might assist in selecting a
            database, it will be provided in the hints dictionary. Details on valid hints are provided below.
            Returns None if there is no suggestion.
        """
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        """ Return True if a relation between obj1 and obj2 should be allowed, False if the relation should be
            prevented, or None if the router has no opinion. This is purely a validation operation, used by foreign key
            and many to many operations to determine if a relation should be allowed between two objects.
            If no router has an opinion (i.e. all routers return None), only relations within the same database are
            allowed.
        """
        # Insist on NO cross-database relationships.
        res = self._is_allowed(obj1._meta.app_label) and self._is_allowed(obj2._meta.app_label)
        return res if res else None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """ Determine if the migration operation is allowed to run on the database with alias db. Return True if the
            operation should run, False if it shouldn’t run, or None if the router has no opinion.
            The app_label positional argument is the label of the application being migrated.
            model_name is set by most migration operations to the value of model._meta.model_name (the lowercased
            version of the model __name__) of the model being migrated. Its value is None for the RunPython and RunSQL
            operations unless they provide it using hints.
            hints are used by certain operations to communicate additional information to the router.
            When model_name is set, hints normally contains the model class under the key 'model'. Note that it may be a
            historical model, and thus not have any custom attributes, methods, or managers. You should only rely on
            _meta.
            This method can also be used to determine the availability of a model on a given database.
            makemigrations always creates migrations for model changes, but if allow_migrate() returns False, any
            migration operations for the model_name will be silently skipped when running migrate on the db. Changing
            the behavior of allow_migrate() for models that already have migrations may result in broken foreign keys,
            extra tables, or missing tables. When makemigrations verifies the migration history, it skips databases
            where no app is allowed to migrate.
        """
        if self._is_allowed(app_label):
            return db == self.db
        return None


class BSRRouter(BaseRouter):
    route_app_labels = {"uploader"}
    exclude_app_labels = {}
    db = "bsr"

    # Override base methods here when needing to convert None -> False.


class AdminRouter(BaseRouter):
    """ Catch all router.
        Technically, this could just go last in the router chain and just return True, however, for better correctness
        we still check against ``exclude_app_labels``.
        NOTE: Methods here don't return None so this router must still go last in the list settings.DATABASE_ROUTERS.
        """

    route_app_labels = {}
    exclude_app_labes = {"uploader"}
    db = "admin"

    def db_for_read(self, model, **hints):
        return self.db

        if model._meta.app_label not in self.exclude_app_labels:
            return self.db
        return False

    db_for_write = db_for_read

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db not in self.exclude_app_labels
