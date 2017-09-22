# -*- coding: utf-8 -*-
"""
Settings for aa-stripe all start with STRIPE_ namespace. For example your project's "settings.py" file
might look like this:

STRIPE_API_KEY = "api_key"
STRIPE_WEBHOOK_ENDPOINT_SECRET = "secret"

and the settings can be accessed by the aa_stripe.settings.stripe_settings object:

from aa_stripe.settings import stripe_settings
stripe_settings.API_KEY  # "api_key"
"""
from __future__ import unicode_literals

from django.conf import settings
from django.test.signals import setting_changed

DEFAULTS = {
    "PENDING_WEBHOOKS_THRESHOLD": 20,
    "API_KEY": "",
    "WEBHOOK_ENDPOINT_SECRET": "",
    "USER_MODEL": settings.AUTH_USER_MODEL
}


class StripeSettings(object):
    def __getattr__(self, attr):
        if attr not in DEFAULTS:
            raise AttributeError("Invalid API setting: '%s'" % attr)

        val = getattr(settings, "STRIPE_{}".format(attr), DEFAULTS[attr])
        # Cache the result
        setattr(self, attr, val)
        return val


class StripeSettingOutter(object):
    def __init__(self, settings_inner):
        self.settings_inner = settings_inner

    def __getattr__(self, attr):
        return getattr(self.settings_inner, attr)


stripe_settings = StripeSettingOutter(StripeSettings())


def reload_api_settings(*args, **kwargs):
    global stripe_settings
    if kwargs["setting"].startswith("STRIPE_"):
        stripe_settings.settings_inner = StripeSettings()


setting_changed.connect(reload_api_settings)
