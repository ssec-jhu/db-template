from abc import abstractmethod
from functools import partial
import uuid

from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Changes here need to be migrated, committed, and activated.
# See https://docs.djangoproject.com/en/4.2/intro/tutorial02/#activating-models
# python manage.py makemigrations user
# git add biospecdb/apps/user/migrations
# git commit -asm"Update user model(s)"
# python manage.py migrate

def validate_country(value):
    """ Validate ``center.country`` field. """
    if value.lower() in ("us", "usa", "america"):
        raise ValidationError(_("This repository is not HIPAA compliant and cannot be used to collect health data from"
                                " the USA"),
                              code="invalid")


class BaseCenter(models.Model):
    class Meta:
        abstract = True
        unique_together = [["name", "country"]]

    id = models.UUIDField(unique=True, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=128, blank=False, null=False)
    country = models.CharField(max_length=128, blank=False, null=False, validators=[validate_country])

    def __str__(self):
        return f"{self.name}, {self.country}"

    def __eq__(self, other):
        """ Copied from models.Model """
        if not isinstance(other, models.Model):
            return NotImplemented

        # NOTE: Added ``not isinstance(other, BaseCenter)`` condition.
        if (not isinstance(other, BaseCenter)) and \
                (self._meta.concrete_model != other._meta.concrete_model):
            return False

        my_pk = self.pk
        if my_pk is None:
            return self is other
        return my_pk == other.pk

    __hash__ = models.Model.__hash__

    def save_replica(self, *args, **kwargs):
        """ Replicate save action on other database. """
        try:
            # Save is used to update fields, so we need to account for this.
            # Note: We can't use get_or_create() since the fields passed in might not match existing DB
            # entry if this use of save is an update.
            center = self.replica_model.objects.get(id=self.id)
        except self.replica_model.DoesNotExist:
            self.replica_model.objects.create(id=self.id, name=self.name, country=self.country)
        else:
            # Update field values.
            center.name = self.name
            center.country = self.country
            center.full_clean()
            center.save(*args, **kwargs)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """ Save database instance.

            Note: When saving user.Center also replicate for uploader.Center.

            Note: DB replication to the "bsr" database doesn't happen if explicitly stating the use of the "default"
            DB, i.e., ``save(using="default")`` will not save to the "bsr" DB and vice versa for ``using="bsr"``.
        """

        save = partial(super().save,
                       force_insert=force_insert,
                       force_update=force_update,
                       update_fields=update_fields)

        # Save to the default intended DB. Do this first so self.pk is generated.
        if using in (None, self.replica_db):
            # Save to both or not at all.
            # NOTE: This is brittle to DB alias changes and also assumes there's only these two.
            with transaction.atomic(using="default"):
                with transaction.atomic(using="bsr"):
                    if using is None:
                        save(using=using)

                    self.save_replica(force_insert=force_insert, force_update=force_update, update_fields=update_fields)
        else:
            save(using=using)

    def asave(self, *args, **kwargs):
        raise NotImplementedError

    def delete_replica(self, *args, **kwargs):
        """ Replicate delete action on other database. """
        try:
            # This should definitely exist but sanity check via a try-except.
            center = self.replica_model.objects.get(id=self.id)
        except self.replica_model.DoesNotExist:
            pass
        else:
            center.delete(*args, using=self.replica_db, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """ Delete database instance.

            NOTE: When deleting user.Center also replicate for uploader.Center.
        """

        delete = partial(super().delete, keep_parents=keep_parents)

        if using in (None, self.replica_db):
            with transaction.atomic(using="default"):
                with transaction.atomic(using="bsr"):
                    self.delete_replica(keep_parents=keep_parents)

                    # Delete the original.
                    # Note: This has to be done last such that self.pk still exists to conduct the above lookup.
                    # Additionally, deleting this last also means that we don't need to wrap this in a transaction on the
                    # default DB since the other way around could delete from "default" but then fail on "BSR" due to protected
                    # relations but leaving it deleted on the default DB.
                    if using is None:
                        delete(using=using)
        else:
            delete(using=using)

    def adelete(self, *args, **kwargs):
        raise NotImplementedError

    @property
    @abstractmethod
    def replica_model(self):
        ...

    @property
    @abstractmethod
    def replica_db(self):
        ...


class Center(BaseCenter):
    """ A center, institution, or hospital etc., from which patient data has been collected.

        This is also used to specify data visibility such that only users of a given center can access
        patient data from that center.

        Attributes:
            id (:obj:`django.models.UUIDField`): Database primary key. Auto generated if not provided.
            name (:obj:`django.models.CharField`): The name of the center.
            country (:obj:`django.models.CharField`): The country in which the center is located. This can be used to
                determine data compliance, i.e., GDPR and HIPAA etc.
     """
    @property
    def replica_model(self):
        from uploader.models import Center as UploaderCenter
        return UploaderCenter

    @property
    def replica_db(self):
        return "bsr"


@receiver(post_delete, sender=Center)
def center_deletion_handler(sender, **kwargs):
    kwargs["instance"].delete_replica()


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if (center_id := extra_fields.get("center")) and not isinstance(center_id, Center):
            # Note: This field has already been completely validated upstream by this point. It has also even been
            # checked that a Center instance with this ID exists. However, it just fails to actually use it... so that's
            # what we do here.
            # This seems like a django bug, ``... and not isinstance(center_id, Center)`` should guard against this code
            # breaking from an upstream future fix.
            extra_fields["center"] = Center.objects.get(pk=center_id)
        return super().create_superuser(username, email=email, password=password, **extra_fields)


# NOTE: The following code was copied from from django.contrib.auth.models.
class AbstractUser(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Note: This is an almost verbatim copy from Django, with the addition of ``center``. Due to Django's user creation
    pattern and use for this app to be pluggable with others, they advise copying the class.

    Attributes:
        username (:obj:`django.models.CharField`): Username for login.
        first_name (:obj:`django.models.CharField`, optional): User's first name.
        last_name (:obj:`django.models.CharField`, optional): User's last name.
        email (:obj:`django.models.EmailField`, optional): User's email. Used to send forgotten password links.
        center (:obj:`django.models.ForeignKey` of :obj:`Center`): User's associated center.
        is_staff (:obj:`django.models.BooleanField`): Designates whether the user can log into this admin site.
        is_active (:obj:`django.models.BooleanField`): Designates whether this user should be treated as active.
            Unselect this instead of deleting accounts.
        date_joined (:obj:`django.models.DateTimeField`): The user's registration date.
    """

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"), blank=True)

    # NOTE: Allow this to be null for the exception of some admin users that have no listed centers.
    center = models.ForeignKey(Center, blank=False, null=False, on_delete=models.PROTECT, related_name="user")

    is_staff = models.BooleanField(
        _("staff status"),
        default=True,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = CustomUserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "center"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        abstract = True

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


# NOTE: The following code was copied from from django.contrib.auth.models.
class User(AbstractUser):
    """
    Users within the Django authentication system are represented by this
    model.

    Attributes:
        username (:obj:`django.models.CharField`): Username for login.
        first_name (:obj:`django.models.CharField`, optional): User's first name.
        last_name (:obj:`django.models.CharField`, optional): User's last name.
        email (:obj:`django.models.EmailField`, optional): User's email. Used to send forgotten password links.
        center (:obj:`django.models.ForeignKey` of :obj:`Center`): User's associated center.
        is_staff (:obj:`django.models.BooleanField`): Designates whether the user can log into this admin site.
        is_active (:obj:`django.models.BooleanField`): Designates whether this user should be treated as active.
            Unselect this instead of deleting accounts.
        date_joined (:obj:`django.models.DateTimeField`): The user's registration date.
        is_sqluser_view (:obj:`django.models.BooleanField`): SQL explorer user status (view/execute existing queries only)
        is_sqluser_change (:obj:`django.models.BooleanField`): SQL explorer user status (view/add/change/delete/execute)
        is_catalogviewer (:obj:`django.models.BooleanField`): Dataset Catalog user status (readonly)
    """

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    is_sqluser_view = models.BooleanField(
        _("SQL explorer user status (view/execute existing queries only)"),
        default=False,
        help_text=_("Designates whether the user can log into the SQL explorer app with permissions to only view "
                    "and execute existing queries."))

    is_sqluser_change = models.BooleanField(
        _("SQL explorer user status (view/add/change/delete/execute)"),
        default=False,
        help_text=_("Designates whether the user can log into the SQL explorer app with permissions to "
                    "view/add/change/delete/execute queries."))

    is_catalogviewer = models.BooleanField(
        _("Dataset Catalog user status (readonly)"),
        default=False,
        help_text=_("Designates whether the user can log into the Dataset Catalog app. (readonly)"))
