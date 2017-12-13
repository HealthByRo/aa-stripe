import time
from datetime import datetime
from uuid import uuid4

import requests_mock
import simplejson as json
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from stripe.webhook import WebhookSignature

from aa_stripe.models import StripeCard, StripeCoupon, StripeCustomer
from aa_stripe.settings import stripe_settings

UserModel = get_user_model()


class BaseTestCase(APITestCase):
    def _create_user(self, i=1, set_self=True):
        user = UserModel.objects.create(email="foo{}@bar.bar".format(i), username="foo{}".format(i),
                                        password="dump-password")
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

    def _create_customer(self, customer_id=None, set_self=True):
        customer_id = customer_id or "cus_{}".format(uuid4().hex)
        stripe_response = {
            "id": customer_id, "object": "customer", "account_balance": 0, "created": 1512126654, "currency": None,
            "default_source": "card_1BUCsadPxLoWm2fwZbz", "delinquent": False,
            "description": "foo@bar.bar id: 1", "discount": None, "email": None, "livemode": False, "metadata": {},
            "shipping": None, "sources": {"object": "list", "data": [
                {"id": "card_1BAXCPxLoWm2f6pRwe9pGwZbz", "object": "card", "address_city": None,
                 "address_country": None, "address_line1": None, "address_line1_check": None, "address_line2": None,
                 "address_state": None, "address_zip": None, "address_zip_check": None, "brand": "Visa",
                 "country": "US", "customer": customer_id, "cvc_check": "pass", "dynamic_last4": None, "exp_month": 9,
                 "exp_year": 2025, "fingerprint": "DmBIQwsaiNOChP", "funding": "credit", "last4": "4242",
                 "metadata": {}, "name": None, "tokenization_method": None
                 }], "has_more": False, "total_count": 1, "url": "/v1/customers/cus_BrwISa2lfUVaoa/sources"
            }, "subscriptions": {"object": "list", "data": [], "has_more": False, "total_count": 0,
                                 "url": "/v1/customers/{}/subscriptions".format(customer_id)}}
        customer = StripeCustomer.objects.create(
            stripe_response=stripe_response, user=self.user, stripe_customer_id=customer_id, is_created_at_stripe=True)
        if set_self:
            self.customer = customer
        return customer

    def _create_card(self, customer=None, stripe_card_id="", is_default=True, set_self=True):
        card = StripeCard.objects.create(customer=customer or self.customer, last4=4242, exp_month=1, exp_year=2025,
                                         stripe_card_id=stripe_card_id or "card_{}".format(uuid4().hex))
        if is_default:
            card.customer.default_card = card
            card.customer.save()

        if set_self:
            self.card = card
        return card

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
