from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Test email server by sending a test email."

    def add_arguments(self, parser):
        parser.add_argument("email_address",
                            default=None,
                            help="Send test email to this email address.")

    def handle(self, *args, **options):
        email_address = options["email_address"]
        email_from = settings.EMAIL_FROM
        try:
            send_mail("BiospecDB test email", "This is just a test.", email_from, [email_address],
                      fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f"Test email sent to {email_address}"))
        except CommandError:
            raise
        except Exception as error:
            raise CommandError(f"An error occurred whilst trying to send a test email to '{email_address}': "
                               f"{type(error).__name__}: {error}")
