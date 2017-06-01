# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from django.core.management.base import BaseCommand

from django_stripe.models import StripeCharge


class Command(BaseCommand):
    help = "Charge stripe"

    def handle(self, *args, **options):
        charges = StripeCharge.objects.filter(is_charged=False)
        stripe.api_key = settings.STRIPE_API_KEY
        for c in charges:
            if c.token.is_active:
                stripe_charge = stripe.Charge.create(
                    amount=c.amount,
                    currency="usd",
                    customer=c.token.customer_id,
                    description=c.description
                )
                c.stripe_charge_id = stripe_charge["id"]
                c.is_charged = True
                c.save()
