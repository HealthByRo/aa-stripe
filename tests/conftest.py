# -*- coding: utf-8 -*-
def pytest_configure():
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        SECRET_KEY="not very secret in tests",
        USE_I18N=True,
        USE_L10N=True,
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.admin",
            "rest_framework",
            "aa_stripe"
        ),
        ROOT_URLCONF="aa_stripe.api_urls",
        TESTING=True,

        STRIPE_API_KEY="apikey"
    )
