# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from aa_stripe.models import StripeWebhook
from aa_stripe.settings import stripe_settings


class StripePendingWebooksLimitExceeded(Exception):
    def __init__(self, pending_webhooks, site):
        self.message = "Pending webhooks threshold limit exceeded, current threshold is {}".format(
            stripe_settings.PENDING_WEBHOOKS_THRESHOLD)
        # send email to admins
        server_env = getattr(settings, "ENV_PREFIX", None)
        email_message = "Pending webhooks for {domain} at {now}:\n\n{webhooks}".format(
            domain=site.domain, now=now(), webhooks="\n".join(webhook["id"] for webhook in pending_webhooks)
        )
        if server_env:
            email_message += "\n\nServer environment: {}".format(server_env)

        mail_admins("Stripe webhooks pending threshold exceeded", email_message)
        super(StripePendingWebooksLimitExceeded, self).__init__(self.message)


class Command(BaseCommand):
    help = "Check pending webhooks at Stripe API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--site",
            help="Site id to use while running the command. First site in the database will be used if not provided."
        )

    def handle(self, *args, **options):
        stripe.api_key = stripe_settings.API_KEY

        site_id = options.get("site")
        site = Site.objects.get(pk=site_id) if site_id else Site.objects.all()[0]
        pending_webhooks = []
        last_event = StripeWebhook.objects.first()
        last_event_id = last_event.id if last_event else None
        try:
            if last_event:
                stripe.Event.retrieve(last_event_id)
        except stripe.error.InvalidRequestError:
            last_event_id = None

        while True:
            event_list = stripe.Event.list(ending_before=last_event_id, limit=100)  # 100 is the maximum
            pending_webhooks += event_list["data"]

            if len(pending_webhooks) > stripe_settings.PENDING_WEBHOOKS_THRESHOLD:
                raise StripePendingWebooksLimitExceeded(pending_webhooks, site)

            if not event_list["has_more"]:
                break
            else:
                last_event_id = event_list["data"][-1]["id"]
