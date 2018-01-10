# -*- coding: utf-8 -*-
import stripe
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from aa_stripe.models import StripeCard, StripeCustomer
from aa_stripe.settings import stripe_settings


class Command(BaseCommand):
    help = "Sync all cards for all customers with Stripe API"

    def add_arguments(self, parser):
        user_ids = get_user_model().objects.values_list("id")
        min_user_id, max_user_id = min(user_ids)[0], max(user_ids)[0]
        parser.add_argument(
            '--max_user_id',
            nargs='?',
            const=max_user_id,
            default=max_user_id,
            type=int,
            dest='max_id',
            help='Id of the last user for whom to update cards',
        )
        parser.add_argument(
            '--min_user_id',
            nargs='?',
            const=min_user_id,
            default=min_user_id,
            type=int,
            dest='min_id',
            help='Id of the first user for whom to update cards',
        )

    def handle(self, *args, **options):
        stripe.api_key = stripe_settings.API_KEY

        counts = {"created": 0, "updated": 0, "deleted": 0}

        for customer in map(
                StripeCustomer.get_latest_active_customer_for_user,
                get_user_model().objects.filter(id__range=(options['min_id'], options['max_id']))):
            customer_from_stripe = stripe.Customer.retrieve(customer.stripe_customer_id)
            actual_cards = customer_from_stripe.sources.all(object="card")
            actual_cards_set = set([c.id for c in actual_cards])
            our_cards_set = set(StripeCard.objects.filter(customer=customer).values_list('stripe_card_id', flat=True))
            print(actual_cards_set & our_cards_set)

        if options.get("verbosity") > 1:
            print("Coupons created: {created}, updated: {updated}, deleted: {deleted}".format(**counts))
