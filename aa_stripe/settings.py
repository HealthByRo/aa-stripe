# -*- coding: utf-8 -*-
"""
Settings for aa-stripe are all namespaced in the STRIPE_SETTINGS setting. For example your project's "settings.py" file
might look like this:

STRIPE_SETTINGS = {
    "PENDING_EVENTS_THRESHOLD": 20
}

To simplify overriding those settings they have a flat structure.

This module provides the "api_setting" object, that is used to access aa-stripe settings, checking for user settings
first, then falling back to the defaults.

This code is based on Django Rest Framework's settings.
"""
from __future__ import unicode_literals

from django.conf import settings
from django.test.signals import setting_changed
from rest_framework.settings import perform_import

DEFAULTS = {
    "PENDING_EVENTS_THRESHOLD": 20,
    "API_KEY": "",
    "WEBHOOK_ENDPOINT_SECRET": "",
    "USER_MODEL": settings.AUTH_USER_MODEL
}

# List of settings that may be in string import notation.
IMPORT_STRINGS = []


class StripeSettings(object):
    """
    A settings object, that allows API settings to be accessed as properties.
    For example:

        from aa_stripe.settings import stripe_settings
        print(stripe_settings.PENDING_EVENTS_THRESHOLD)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """

    def __init__(self, user_settings=None):
        if user_settings:
            self._user_settings = self.__check_user_settings(user_settings)

    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(settings, 'STRIPE_SETTINGS', {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in DEFAULTS:
            raise AttributeError("Invalid API setting: '%s'" % attr)

        try:  # than user settings
            val = self.user_settings[attr]
        except KeyError:  # fall back to defaults
            val = DEFAULTS[attr]

        # Coerce import strings into classes
        if attr in IMPORT_STRINGS:
            val = perform_import(val, attr)

        # Cache the result
        setattr(self, attr, val)
        return val

    def __check_user_settings(self, user_settings):
        for setting in user_settings:
            if setting not in DEFAULTS:
                raise RuntimeError("The '%s' is incorrect. Please check settings.DEFAULTS for the available options")
        return user_settings


class StripeSettingOutter(object):
    def __init__(self, settings_inner):
        self.settings_inner = settings_inner

    def __getattr__(self, attr):
        return getattr(self.settings_inner, attr)


stripe_settings = StripeSettingOutter(StripeSettings())


def reload_api_settings(*args, **kwargs):
    global stripe_settings
    setting, value = kwargs['setting'], kwargs['value']
    if setting == 'STRIPE_SETTINGS':
        stripe_settings.settings_inner = StripeSettings(value)


setting_changed.connect(reload_api_settings)
