# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from aa_stripe.models import StripeSubscription


class Command(BaseCommand):
    help = "Terminate outdated subscriptions"

    def handle(self, *args, **options):
        StripeSubscription.end_subscriptions()
