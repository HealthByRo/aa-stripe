# -*- coding: utf-8 -*-
import stripe
from django.core.management.base import BaseCommand

from aa_stripe.models import StripeCustomer
from aa_stripe.settings import stripe_settings


class Command(BaseCommand):
    help = "Update customers card data from Stripe API"

    def handle(self, *args, **options):
        stripe.api_key = stripe_settings.API_KEY
        for customer in StripeCustomer.objects.filter(is_active=True, is_created_at_stripe=True):
            try:
                customer.refresh_from_stripe()
            except stripe.StripeError:
                pass
