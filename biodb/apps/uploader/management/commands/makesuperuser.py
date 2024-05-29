from django.core.management import BaseCommand, call_command, CommandError


class Command(BaseCommand):
    # A wrapper to Django's builtin createsuperuser command that doesn't raise when username already exists.

    help = "Used to create a superuser. Won't fail if username already exists."

    def add_arguments(self, parser):
        parser.add_argument("--username",
                            default=None,
                            help="Specifies the login for the superuser.")
        parser.add_argument("--noinput", "--no-input",
                            action="store_true",
                            default=False,
                            help="Tells Django to NOT prompt the user for input of any kind. You must use --username "
                                 "with --noinput, along with an option for any other required field. Superusers created"
                                 " with --noinput will not be able to log in until they're given a valid password.")
        parser.add_argument("--database",
                            default="default",
                            help="Specifies the database to use. Default is 'default'.")
        parser.add_argument("--email",
                            default=None,
                            help="Specifies the email for the superuser.")
        parser.add_argument("--center",
                            default=None,
                            help="Specifies the center for the superuser.")
        parser.add_argument("--fail",
                            action="store_true",
                            default=False,
                            help="Fail if user already exists.")

    def handle(self, *args, **options):
        cmd = ["createsuperuser"]
        if username := options["username"]:
            cmd.append(f"--username={username}")
        if options["noinput"]:
            cmd.append("--noinput")
        if database := options["database"]:
            cmd.append(f"--database={database}")
        if email := options["email"]:
            cmd.append(f"--email={email}")
        if center := options["center"]:
            cmd.append(f"--center={center}")

        try:
            call_command(*cmd)
        except CommandError as error:
            if options["fail"] or "That username is already taken" not in str(error):
                raise
