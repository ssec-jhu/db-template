from functools import partial
import uuid

from django.db import models
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


class Center(BaseCenter):
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """ When saving user.Center also replicate for uploader.Center. """

        save = partial(super().save,
                       force_insert=force_insert,
                       force_update=force_update,
                       update_fields=update_fields)

        if using in (None, "bsr"):
            if using is None:
                save(using=using)

            # Replicate action to BSR database.
            from uploader.models import Center as UploaderCenter
            try:
                center = UploaderCenter.objects.get(id=self.id)
            except UploaderCenter.DoesNotExist:
                UploaderCenter.objects.create(id=self.id, name=self.name, country=self.country)
            else:
                center.name = self.name
                center.country = self.country
                center.full_clean()
                center.save(force_insert=force_insert,
                            force_update=force_update,
                            update_fields=update_fields)
        else:
            save(using=using)

    def asave(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, using=None, keep_parents=False):
        """ When deleting user.Center also replicate for uploader.Center. """

        delete = partial(super().delete, keep_parents=keep_parents)

        if using in (None, "bsr"):
            # Replicate action to BSR database.
            from uploader.models import Center as UploaderCenter
            try:
                center = UploaderCenter.objects.get(id=self.id)
            except UploaderCenter.DoesNotExist:
                pass
            else:
                center.delete(keep_parents=keep_parents)

            # Delete the original.
            if using is None:
                delete(using=using)
        else:
            delete(using=using)

    def adelete(self, *args, **kwargs):
        raise NotImplementedError


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

    Username and password are required. Other fields are optional.
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
    center = models.ForeignKey(Center, blank=False, null=False, on_delete=models.CASCADE, related_name="user")

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
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

    # def __init__(self, *args, **kwargs):
    #     if center := kwargs.get("center"):
    #         if isinstance(center, Center):
    #             try:
    #                 Center.objects.get(pk=center.pk)
    #             kwargs["center"] = Center.objects.get(pk=str(center.pk))
    #     super().__init__(*args, **kwargs)

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

    Username and password are required. Other fields are optional.
    """

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"
