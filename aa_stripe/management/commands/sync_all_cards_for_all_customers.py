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
            actual_cards_map = {c.id: c for c in actual_cards}
            actual_cards_set = set(actual_cards_map)
            our_cards = StripeCard.objects.filter(customer=customer)
            our_cards_set = set(our_cards.values_list('stripe_card_id', flat=True))
            our_deleted_cards = StripeCard.objects.deleted().filter(customer=customer)
            our_deleted_cards_set = set(our_deleted_cards.values_list('stripe_card_id', flat=True))

            stripe_deleted_cards = our_cards_set - actual_cards_set
            for card_id in stripe_deleted_cards:
                card = our_cards.get(stripe_card_id=card_id)
                card.is_deleted = True
                card.save()

            undelete_cards = actual_cards_set & our_deleted_cards_set
            for card_id in undelete_cards:
                card = our_deleted_cards.get(stripe_card_id=card_id)
                card.is_deleted = False
                card.save()

            update_cards = our_cards_set & actual_cards_set
            for card_id in update_cards:
                card = our_cards.get(stripe_card_id=card_id)
                card.update_from_stripe_card(actual_cards_map[card_id])

            created_cards = actual_cards_set - (our_cards_set | our_deleted_cards_set)
            for card_id in created_cards:
                card = StripeCard(customer=customer)
                card.update_from_stripe_card(actual_cards_map[card_id])

            stripe_defaut_source = customer_from_stripe.default_source
            our_defaut_source = customer.default_card.stripe_card_id
            if stripe_defaut_source != our_defaut_source:
                customer.default_card = StripeCard.objects.get(stripe_card_id=stripe_defaut_source)
                customer.save()

            counts["created"] = len(created_cards)
            counts["deleted"] = len(stripe_deleted_cards)
            counts["updated"] = len(update_cards) + len(undelete_cards)

        if options.get("verbosity") > 1:
            print("Coupons created: {created}, updated: {updated}, deleted: {deleted}".format(**counts))
