import time
from datetime import datetime

import requests_mock
import simplejson as json
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from stripe.webhook import WebhookSignature

from aa_stripe.models import StripeCoupon, StripeCustomer
from aa_stripe.settings import stripe_settings

UserModel = get_user_model()


class BaseTestCase(APITestCase):
    def _create_user(self, email="foo@bar.bar", set_self=True):
        user = UserModel.objects.create(email=email, username=email.split("@")[0], password="dump-password")
        if set_self:
            self.user = user
        return user

    def _create_coupon(self, coupon_id, amount_off=None, duration=StripeCoupon.DURATION_FOREVER, metadata=None):
        with requests_mock.Mocker() as m:
            # create a simple coupon which will be used for tests
            stripe_response = {
                "id": coupon_id,
                "object": "coupon",
                "amount_off": int(amount_off * 100) if amount_off else None,
                "created": int(time.mktime(datetime.now().timetuple())),
                "currency": "usd",
                "duration": duration,
                "duration_in_months": None,
                "livemode": False,
                "max_redemptions": None,
                "metadata": metadata or {},
                "percent_off": 25,
                "redeem_by": None,
                "times_redeemed": 0,
                "valid": True
            }
            m.register_uri("POST", "https://api.stripe.com/v1/coupons", text=json.dumps(stripe_response))
            return StripeCoupon.objects.create(
                coupon_id=coupon_id,
                duration=duration,
                amount_off=amount_off
            )

    def _create_customer(self, user=None, customer_id="cus_xyz", sources=None, default_source="", is_active=True,
                         is_created_at_stripe=True):
        if not user:
            if hasattr(self, "user"):
                user = self.user
            else:
                user = self._create_user()

        sources = sources or []
        self.customer = StripeCustomer.objects.create(
            user=user, is_active=is_active,
            stripe_customer_id=customer_id if is_created_at_stripe else "",
            is_created_at_stripe=is_created_at_stripe,
            sources=sources,
            default_source=default_source
        )
        return self.customer

    def _get_signature_headers(self, payload):
        timestamp = int(time.time())

        raw_payload = json.dumps(payload).replace(": ", ":")
        raw_payload = raw_payload.replace(", ", ",")
        signed_payload = "{timestamp:d}.{raw_payload}".format(timestamp=timestamp, raw_payload=raw_payload)
        signature = WebhookSignature._compute_signature(signed_payload, stripe_settings.WEBHOOK_ENDPOINT_SECRET)
        return {
            "HTTP_STRIPE_SIGNATURE": ("t={timestamp:d},v1={signature}"
                                      ",v0=not_important".format(timestamp=timestamp, signature=signature))
        }
