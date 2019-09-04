# -*- coding: utf-8 -*-
import sys

import stripe
from django.core.management.base import BaseCommand
from django.utils import timezone

from aa_stripe.models import StripeCustomer
from aa_stripe.settings import stripe_settings


class Command(BaseCommand):
    help = "Update customers card data from Stripe API"

    def handle(self, *args, **options):
        stripe.api_key = stripe_settings.API_KEY
        last_customer = None
        retry_count = 0
        updated_count = 0
        start_time = timezone.now()
        verbose = options["verbosity"] >= 2
        if verbose:
            print("Began refreshing customers")

        while True:
            try:
                response = stripe.Customer.list(limit=100, starting_after=last_customer)
            except stripe.error.StripeError:
                if retry_count > 5:
                    raise
                retry_count += 1
                continue
            else:
                retry_count = 0

            for stripe_customer in response["data"]:
                updated_count += StripeCustomer.objects.filter(stripe_customer_id=stripe_customer["id"]).update(
                    sources=stripe_customer["sources"]["data"], default_source=stripe_customer["default_source"]
                )

            if not response["has_more"]:
                break

            if verbose:
                sys.stdout.write(".")  # indicate that the command did not hung up
                sys.stdout.flush()
            last_customer = response["data"][-1]

        if verbose:
            if updated_count:
                print("\nCustomers updated: {} (took {:2f}s)".format(
                    updated_count, (timezone.now() - start_time).total_seconds()))
            else:
                print("No customers were updated.")
