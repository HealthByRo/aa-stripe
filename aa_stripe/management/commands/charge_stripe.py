# -*- coding: utf-8 -*-
import sys
import traceback
from time import sleep

import stripe
from django.core.management.base import BaseCommand

from aa_stripe.models import StripeCharge
from aa_stripe.settings import stripe_settings

try:
    from raven.contrib.django.raven_compat.models import client
    from django.conf import settings
    settings.RAVEN_CONFIG["dsn"]
    if settings.RAVEN_CONFIG["dsn"] != "":
        sentry_available = True
    else:
        sentry_available = False
except (KeyError, NameError, ImportError):
    sentry_available = False


class Command(BaseCommand):
    help = "Charge stripe"

    def handle(self, *args, **options):
        charges = StripeCharge.objects.filter(is_charged=False)
        stripe.api_key = stripe_settings.API_KEY
        exceptions = []
        for c in charges:
            try:
                c.charge()
                sleep(0.25)  # 4 requests per second tops
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if sentry_available:
                    client.captureException()
                else:
                    exceptions.append({
                        "obj": c,
                        "exc_type": exc_type,
                        "exc_value": exc_value,
                        "exc_traceback": exc_traceback,
                    })

        for e in exceptions:
            print("Exception happened")
            print("Charge id: {obj.id}".format(obj=e["obj"]))
            traceback.print_exception(e["exc_type"], e["exc_value"], e["exc_traceback"], file=sys.stdout)
        if exceptions:
            sys.exit(1)
