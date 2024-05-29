from django.conf import settings
from django.contrib.auth.views import PasswordResetView
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Test email server by sending a test email."

    def add_arguments(self, parser):
        parser.add_argument("email_address",
                            default=None,
                            help="Send test email to this email address.")
        parser.add_argument("--mimic_password_reset",
                            action="store_true",
                            default=False,
                            help="Send test email to this email address, via the Django's password reset mechanism.")

    def handle(self, *args, **options):
        email_address = options["email_address"]

        try:
            if options["mimic_password_reset"]:
                opts = {
                    "use_https": True,
                    "token_generator": PasswordResetView.token_generator,
                    "from_email": settings.EMAIL_FROM,
                    "email_template_name": PasswordResetView.email_template_name,
                    "subject_template_name": PasswordResetView.subject_template_name,
                    "html_email_template_name": PasswordResetView.html_email_template_name,
                    "extra_email_context": PasswordResetView.extra_email_context,
                    "domain_override": settings.HOST_DOMAIN
                }
                form = PasswordResetView.form_class(data={"email": email_address})
                form.is_valid()
                form.save(**opts)
            else:
                email_from = settings.EMAIL_FROM
                send_mail("BiospecDB test email", "This is just a test.", email_from, [email_address],
                          fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f"Test email sent to {email_address}, check inbox for verification."))
        except CommandError:
            raise
        except Exception as error:
            raise
            raise CommandError(f"An error occurred whilst trying to send a test email to '{email_address}': "
                               f"{type(error).__name__}: {error}")
