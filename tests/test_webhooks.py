import time

import simplejson as json
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from stripe.webhook import WebhookSignature

from aa_stripe.models import StripeWebhook


class TestWebhook(APITestCase):

    def test_subscription_creation(self):
        self.assertEqual(StripeWebhook.objects.count(), 0)
        payload = json.loads("""{
          "created": 1326853478,
          "livemode": false,
          "id": "evt_00000000000000",
          "type": "charge.failed",
          "object": "event",
          "request": null,
          "pending_webhooks": 1,
          "api_version": "2017-06-05",
          "data": {
            "object": {
              "id": "ch_00000000000000",
              "object": "charge",
              "amount": 100,
              "amount_refunded": 0,
              "application": null,
              "application_fee": null,
              "balance_transaction": "txn_00000000000000",
              "captured": false,
              "created": 1496953100,
              "currency": "usd",
              "customer": null,
              "description": "My First Test Charge (created for API docs)",
              "destination": null,
              "dispute": null,
              "failure_code": null,
              "failure_message": null,
              "fraud_details": {
              },
              "invoice": null,
              "livemode": false,
              "metadata": {
              },
              "on_behalf_of": null,
              "order": null,
              "outcome": null,
              "paid": false,
              "receipt_email": null,
              "receipt_number": null,
              "refunded": false,
              "refunds": {
                "object": "list",
                "data": [
                ],
                "has_more": false,
                "total_count": 0,
                "url": "/v1/charges/ch_1ASX5ELoWm2f6pRwC6ZyewYR/refunds"
              },
              "review": null,
              "shipping": null,
              "source": {
                "id": "card_00000000000000",
                "object": "card",
                "address_city": null,
                "address_country": null,
                "address_line1": null,
                "address_line1_check": null,
                "address_line2": null,
                "address_state": null,
                "address_zip": null,
                "address_zip_check": null,
                "brand": "Visa",
                "country": "US",
                "customer": null,
                "cvc_check": null,
                "dynamic_last4": null,
                "exp_month": 8,
                "exp_year": 2018,
                "fingerprint": "DsGmBIQwiNOvChPk",
                "funding": "credit",
                "last4": "4242",
                "metadata": {
                },
                "name": null,
                "tokenization_method": null
              },
              "source_transfer": null,
              "statement_descriptor": null,
              "status": "succeeded",
              "transfer_group": null
            }
          }
        }""")

        url = reverse("stripe-webhooks")
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)  # not signed

        headers = {
            "HTTP_STRIPE_SIGNATURE": "wrong",  # todo: generate signature
        }
        self.client.credentials(**headers)
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)  # wrong signature

        timestamp = int(time.time())
        raw_payload = json.dumps(payload).replace(": ", ":")
        raw_payload = raw_payload.replace(", ", ",")
        signed_payload = "{timestamp:d}.{raw_payload}".format(timestamp=timestamp, raw_payload=raw_payload)
        signature = WebhookSignature._compute_signature(signed_payload, settings.STRIPE_WEBHOOK_ENDPOINT_SECRET)
        headers = {
            "HTTP_STRIPE_SIGNATURE": ("t={timestamp:d},v1={signature}"
                                      ",v0=not_important".format(timestamp=timestamp, signature=signature))
        }
        self.client.credentials(**headers)
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(StripeWebhook.objects.count(), 1)
        webhook = StripeWebhook.objects.first()
        self.assertEqual(webhook.id, payload["id"])
        self.assertEqual(webhook.raw_data, payload)
        self.assertFalse(webhook.is_parsed)
