# -*- coding: utf-8 -*-
from time import sleep

import stripe
from aa_stripe.models import StripeCharge
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Charge stripe"

    def handle(self, *args, **options):
        charges = StripeCharge.objects.filter(is_charged=False)
        stripe.api_key = settings.STRIPE_API_KEY
        for c in charges:
            # TODO(poxip): catch errors and inform after command finishes
            c.charge()
            sleep(0.25)  # 4 requests per second tops
