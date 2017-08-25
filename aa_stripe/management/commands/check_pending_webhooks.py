# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from aa_stripe.models import StripeWebhook


def get_pending_events_threshold():
    return getattr(settings, "PENDING_EVENTS_THRESHOLD", 20)


class StripePendingWebooksLimitExceeded(Exception):
    def __init__(self, pending_events):
        self.message = "Pending events limit exceeded, current threshold is {}".format(get_pending_events_threshold)
        # send email to admins
        email_message = "Pending events at {now}:\n\n{events}".format(
            now=now(), events="\n".join(event.id for event in pending_events)
        )
        mail_admins("Stripe webhooks pending threshold exceeded", email_message)
        super(StripePendingWebooksLimitExceeded, self).__init__(self.message)


class Command(BaseCommand):
    help = "Check pending webhooks at Stripe API"

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_API_KEY
        pending_events_threshold = get_pending_events_threshold()

        pending_events = []
        last_event = StripeWebhook.objects.latest("created").id
        while True:
            event_list = stripe.Event.list(starting_after=last_event, limit=100)  # 100 is the maximum
            pending_events += event_list["data"]
            if len(pending_events) > pending_events_threshold:
                raise StripePendingWebooksLimitExceeded(pending_events)

            if not event_list["has_more"]:
                break
            else:
                last_event = event_list["data"][-1]

        print("Pending webhooks: {} (the threshold is {})".format(len(pending_events), pending_events_threshold))
