# -*- coding: utf-8 -*-
def pytest_configure():
    import django
    from django.conf import settings
    from django.core.management import call_command

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        SECRET_KEY="not very secret in tests",
        USE_I18N=True,
        USE_L10N=True,
        USE_TZ=True,
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.admin",
            "django.contrib.sites",
            "rest_framework",
            "aa_stripe",
        ),
        ROOT_URLCONF="aa_stripe.api_urls",
        TESTING=True,
        ENV_PREFIX="test-env",
        STRIPE_SETTINGS_API_KEY="apikey",
        STRIPE_SETTINGS_WEBHOOK_ENDPOINT_SECRET="fake",
    )
    django.setup()
    call_command("migrate")
    call_command("makemigrations", "--dry-run", "--check")
