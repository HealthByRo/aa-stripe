# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from aa_stripe.models import StripeWebhook
from aa_stripe.settings import stripe_settings


class StripePendingWebooksLimitExceeded(Exception):
    def __init__(self, pending_events):
        self.message = "Pending events limit exceeded, current threshold is {}".format(
            stripe_settings.PENDING_EVENTS_THRESHOLD)
        # send email to admins
        server_env = getattr(settings, "ENV_PREFIX", None)
        email_message = "Pending events at {now}:\n\n{events}".format(
            now=now(), events="\n".join(event["id"] for event in pending_events)
        )
        if server_env:
            email_message += "\n\nServer environment: {}".format(server_env)

        mail_admins("Stripe webhooks pending threshold exceeded", email_message)
        super(StripePendingWebooksLimitExceeded, self).__init__(self.message)


class Command(BaseCommand):
    help = "Check pending webhooks at Stripe API"

    def handle(self, *args, **options):
        stripe.api_key = stripe_settings.API_KEY
        pending_events_threshold = stripe_settings.PENDING_EVENTS_THRESHOLD

        pending_events = []
        last_event = StripeWebhook.objects.last()
        last_event_id = last_event.id if last_event else None
        while True:
            event_list = stripe.Event.list(ending_before=last_event_id, limit=100)  # 100 is the maximum
            for event in event_list["data"]:
                if event["pending_webhooks"] > 0:
                    pending_events.append(event)

            if len(pending_events) > pending_events_threshold:
                raise StripePendingWebooksLimitExceeded(pending_events)

            if not event_list["has_more"]:
                break
            else:
                last_event_id = event_list["data"][-1]["id"]
