import time
from datetime import datetime
from uuid import uuid4

import mock
import requests_mock
import simplejson as json
import stripe
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from rest_framework.reverse import reverse

from aa_stripe.exceptions import StripeWebhookAlreadyParsed
from aa_stripe.management.commands.check_pending_webhooks import StripePendingWebooksLimitExceeded
from aa_stripe.models import StripeCoupon, StripeWebhook
from aa_stripe.settings import stripe_settings
from tests.test_utils import BaseTestCase


class TestWebhook(BaseTestCase):
    def _create_ping_webhook(self):
        payload = json.loads(
            """{
          "id": "",
          "object": "event",
          "api_version": "2017-06-05",
          "created": 1503474921,
          "livemode": false,
          "pending_webhooks": 0,
          "request": {
            "id": "",
            "idempotency_key": null
          },
          "type": "ping"
        }"""
        )
        payload["id"] = "evt_{}".format(uuid4())
        payload["request"]["id"] = "req_{}".format(uuid4())
        payload["created"] = int(time.mktime(datetime.now().timetuple()))
        return StripeWebhook.objects.create(id=payload["id"], raw_data=payload)

    def test_subscription_creation(self):
        self.assertEqual(StripeWebhook.objects.count(), 0)
        payload = json.loads(
            """{
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
              "refunds": {},
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
        }"""
        )

        url = reverse("stripe-webhooks")
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)  # not signed

        headers = {"HTTP_STRIPE_SIGNATURE": "wrong"}  # todo: generate signature
        self.client.credentials(**headers)
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)  # wrong signature

        self.client.credentials(**self._get_signature_headers(payload))
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(StripeWebhook.objects.count(), 1)
        webhook = StripeWebhook.objects.first()
        self.assertEqual(webhook.id, payload["id"])
        self.assertEqual(webhook.raw_data, payload)
        self.assertTrue(webhook.is_parsed)

    def test_coupon_create(self):
        self.assertEqual(StripeCoupon.objects.count(), 0)
        payload = json.loads(
            """{
          "id": "evt_1AtuXzLoWm2f6pRwC5YntNLU",
          "object": "event",
          "api_version": "2017-06-05",
          "created": 1503478151,
          "data": {
            "object": {
              "id": "nicecoupon",
              "object": "coupon",
              "amount_off": 1000,
              "created": 1503478151,
              "currency": "usd",
              "duration": "once",
              "duration_in_months": null,
              "livemode": false,
              "max_redemptions": null,
              "metadata": {
              },
              "percent_off": null,
              "redeem_by": null,
              "times_redeemed": 0,
              "valid": true
            }
          },
          "livemode": false,
          "pending_webhooks": 1,
          "request": {
            "id": "req_RzV8JI9bg7fPiR",
            "idempotency_key": null
          },
          "type": "coupon.created"
        }"""
        )
        stripe_response = json.loads(
            """{
          "id": "nicecoupon",
          "object": "coupon",
          "amount_off": 1000,
          "created": 1503478151,
          "currency": "usd",
          "duration": "once",
          "duration_in_months": null,
          "livemode": false,
          "max_redemptions": null,
          "metadata": {
          },
          "percent_off": null,
          "redeem_by": null,
          "times_redeemed": 0,
          "valid": true
        }"""
        )
        url = reverse("stripe-webhooks")
        with requests_mock.Mocker() as m:
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/coupons/nicecoupon",
                text=json.dumps(stripe_response),
            )
            self.client.credentials(**self._get_signature_headers(payload))
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(StripeCoupon.objects.count(), 1)
            coupon = StripeCoupon.objects.first()
            # the rest of the data is retrieved from Stripe API, which is stubbed above
            # so there is no need to compare it
            self.assertEqual(coupon.coupon_id, "nicecoupon")

            # test coupon.created while the coupon has already been deleted from Stripe before the webhook arrived
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/coupons/doesnotexist",
                status_code=404,
                text=json.dumps({"error": {"type": "invalid_request_error"}}),
            )
            payload["id"] = "evt_another"
            payload["request"]["id"] = ["req_blahblah"]
            payload["data"]["object"]["id"] = "doesnotexist"
            self.client.credentials(**self._get_signature_headers(payload))
            self.assertEqual(StripeCoupon.objects.filter(coupon_id="doesnotexist").count(), 0)
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(StripeCoupon.objects.filter(coupon_id="doesnotexist").count(), 0)

            # test receiving coupon.created to a coupon that already exists in our database
            coupon_qs = StripeCoupon.objects.all_with_deleted().filter(coupon_id="nicecoupon")
            payload["id"] = "evt_1"
            payload["request"]["id"] = "req_1"
            payload["data"]["object"]["id"] = "nicecoupon"
            self.assertEqual(coupon_qs.count(), 1)
            self.client.credentials(**self._get_signature_headers(payload))
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(
                StripeWebhook.objects.get(id=response.data["id"]).parse_error,
                "Coupon with this coupon_id and creation date already exists",
            )
            self.assertEqual(coupon_qs.count(), 1)

        # test receiving coupon.created to a coupon that already exists in our
        # database but creation timestamps are different
        stripe_response["created"] += 1
        payload["id"] = "evt_2"
        payload["request"]["id"] = "req_2"
        payload["data"]["object"]["created"] = stripe_response["created"]
        with requests_mock.Mocker() as m:
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/coupons/nicecoupon",
                text=json.dumps(stripe_response),
            )
            self.assertEqual(coupon_qs.filter(is_deleted=False).count(), 1)
            self.assertEqual(coupon_qs.filter(is_deleted=True).count(), 0)
            self.client.credentials(**self._get_signature_headers(payload))
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(coupon_qs.count(), 2)
            self.assertEqual(coupon_qs.filter(is_deleted=False).count(), 1)
            self.assertEqual(coupon_qs.filter(is_deleted=True).count(), 1)

        # test receiving coupon.created with a coupon in webhook data that does not exist in our database
        # but when the webhook is being saved, it receives other coupon (same name, but different creation timestamp)
        # it's to make sure we are saving proper coupon, because the webhook for the new coupon will arrive later
        payload["id"] = "evt_3"
        payload["request"]["id"] = "req_3"
        payload["data"]["object"]["created"] = stripe_response["created"] + 1
        with requests_mock.Mocker() as m:
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/coupons/nicecoupon",
                text=json.dumps(stripe_response),
            )
            self.assertEqual(coupon_qs.count(), 2)
            self.client.credentials(**self._get_signature_headers(payload))
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(
                StripeWebhook.objects.get(id=response.data["id"]).parse_error,
                "Coupon with this coupon_id and creation date already exists",
            )
            self.assertEqual(coupon_qs.count(), 2)

    def test_coupon_update(self):
        coupon = self._create_coupon(
            "nicecoupon",
            amount_off=100,
            duration=StripeCoupon.DURATION_ONCE,
            metadata={"nie": "tak", "lol1": "rotfl"},
        )
        payload = json.loads(
            """{
          "id": "evt_1AtuTOLoWm2f6pRw6dYfQzWh",
          "object": "event",
          "api_version": "2017-06-05",
          "created": 1503477866,
          "data": {
            "object": {
              "id": "nicecoupon",
              "object": "coupon",
              "amount_off": 10000,
              "created": 1503412710,
              "currency": "usd",
              "duration": "forever",
              "duration_in_months": null,
              "livemode": false,
              "max_redemptions": null,
              "metadata": {
                "lol1": "rotfl2",
                "lol2": "yeah"
              },
              "percent_off": null,
              "redeem_by": null,
              "times_redeemed": 0,
              "valid": true
            },
            "previous_attributes": {
              "metadata": {
                "nie": "tak",
                "lol1": "rotfl",
                "lol2": null
              }
            }
          },
          "livemode": false,
          "pending_webhooks": 1,
          "request": {
            "id": "req_putcEg4hE9bkUb",
            "idempotency_key": null
          },
          "type": "coupon.updated"
        }"""
        )
        payload["data"]["object"]["created"] = coupon.stripe_response["created"]

        url = reverse("stripe-webhooks")
        self.client.credentials(**self._get_signature_headers(payload))
        response = self.client.post(url, data=payload, format="json")
        coupon.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(coupon.metadata, {"lol1": "rotfl2", "lol2": "yeah"})

        # test updating non existing coupon - nothing else than saving the webhook should happen
        payload["id"] = "evt_1"
        payload["request"]["id"] = "req_1"
        payload["data"]["object"]["id"] = "doesnotexist"
        self.assertFalse(StripeCoupon.objects.filter(coupon_id="doesnotexist").exists())
        self.client.credentials(**self._get_signature_headers(payload))
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(StripeCoupon.objects.filter(coupon_id="doesnotexist").exists())

    @requests_mock.Mocker()
    def test_coupon_delete(self, m):
        coupon = self._create_coupon("nicecoupon", amount_off=100, duration=StripeCoupon.DURATION_ONCE)
        self.assertFalse(coupon.is_deleted)
        payload = json.loads(
            """{
          "id": "evt_1Atthtasdsaf6pRwkdLOSKls",
          "object": "event",
          "api_version": "2017-06-05",
          "created": 1503474921,
          "data": {
            "object": {
              "id": "nicecoupon",
              "object": "coupon",
              "amount_off": 10000,
              "created": 1503474890,
              "currency": "usd",
              "duration": "once",
              "duration_in_months": null,
              "livemode": false,
              "max_redemptions": null,
              "metadata": {
              },
              "percent_off": null,
              "redeem_by": null,
              "times_redeemed": 0,
              "valid": false
            }
          },
          "livemode": false,
          "pending_webhooks": 1,
          "request": {
            "id": "req_9UO71nsJyOhQfi",
            "idempotency_key": null
          },
          "type": "coupon.deleted"
        }"""
        )
        payload["data"]["object"]["created"] = coupon.stripe_response["created"]
        m.register_uri(
            "GET",
            "https://api.stripe.com/v1/coupons/nicecoupon",
            status_code=404,
            text=json.dumps({"error": {"type": "invalid_request_error"}}),
        )

        url = reverse("stripe-webhooks")
        self.client.credentials(**self._get_signature_headers(payload))
        with mock.patch("aa_stripe.models.webhook_pre_parse.send") as mocked_signal:
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertTrue(StripeCoupon.objects.deleted().filter(pk=coupon.pk).exists())
            webhook = StripeWebhook.objects.first()
            self.assertTrue(webhook.is_parsed)
            mocked_signal.assert_called_with(
                event_action="deleted",
                event_model="coupon",
                event_type="coupon.deleted",
                instance=webhook,
                sender=StripeWebhook,
            )

        # test deleting event that has already been deleted - should not raise any errors
        # it will just make sure is_deleted is set for this coupon
        payload["id"] = "evt_someother"
        payload["request"]["id"] = ["req_someother"]
        self.client.credentials(**self._get_signature_headers(payload))
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StripeCoupon.objects.deleted().filter(pk=coupon.pk).exists())

        # make sure trying to parse already parsed webhook is impossible
        self.assertTrue(webhook.is_parsed)
        with self.assertRaises(StripeWebhookAlreadyParsed):
            webhook.parse()

    def test_ping(self):
        # test receiving ping event (the only event without "." inside the event name)
        StripeWebhook.objects.all().delete()
        payload = json.loads(
            """{
          "id": "evt_1Atthtasdsaf6pRwkdLOhKls",
          "object": "event",
          "api_version": "2017-06-05",
          "created": 1503474921,
          "livemode": false,
          "pending_webhooks": 1,
          "request": {
            "id": "req_9UO71nsJyzhQfi",
            "idempotency_key": null
          },
          "type": "ping"
        }"""
        )
        self.client.credentials(**self._get_signature_headers(payload))
        with mock.patch("aa_stripe.models.webhook_pre_parse.send") as mocked_signal:
            response = self.client.post(reverse("stripe-webhooks"), data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            mocked_signal.assert_called_with(
                event_action=None,
                event_model=None,
                event_type="ping",
                instance=StripeWebhook.objects.first(),
                sender=StripeWebhook,
            )

    @override_settings(ADMINS=(("Admin", "admin@example.com"),))
    def test_check_pending_webhooks_command(self):
        stripe_settings.PENDING_WEBHOOKS_THRESHOLD = 1

        # create site
        self._create_ping_webhook()
        webhook = self._create_ping_webhook()

        # create response with fake limits
        base_stripe_response = json.loads(
            """{
          "object": "list",
          "url": "/v1/events",
          "has_more": true,
          "data": []
        }"""
        )
        event1_data = webhook.raw_data.copy()
        event1_data["id"] = "evt_1"
        stripe_response_part1 = base_stripe_response.copy()
        stripe_response_part1["data"] = [event1_data]

        event2_data = event1_data.copy()
        event2_data["id"] = "evt_2"
        stripe_response_part2 = base_stripe_response.copy()
        stripe_response_part2["data"] = [event2_data]
        stripe_response_part2["has_more"] = False

        last_webhook = StripeWebhook.objects.first()
        with requests_mock.Mocker() as m:
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/events/{}".format(last_webhook.id),
                [
                    {"text": json.dumps(last_webhook.raw_data)},
                    {"text": json.dumps(last_webhook.raw_data)},
                    {
                        "text": json.dumps({"error": {"type": "invalid_request_error"}}),
                        "status_code": 404,
                    },
                ],
            )
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/events?ending_before={}&limit=100".format(last_webhook.id),
                text=json.dumps(stripe_response_part1),
            )
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/events?ending_before={}&limit=100".format(event1_data["id"]),
                text=json.dumps(stripe_response_part2),
            )

            with self.assertRaises(StripePendingWebooksLimitExceeded):
                call_command("check_pending_webhooks")
                self.assertEqual(len(mail.outbox), 1)
                message = mail.outbox[0]
                self.assertEqual(message.to, "admin@example.com")
                self.assertIn(event1_data["id"], message)
                self.assertIn(event2_data["id"], message)
                self.assertIn("Server environment: test-env", message)
                self.assertIn("example.com", message)
                self.assertNotIn(webhook["id"], message)

            mail.outbox = []
            stripe_settings.PENDING_WEBHOOKS_THRESHOLD = 20
            call_command("check_pending_webhooks")
            self.assertEqual(len(mail.outbox), 0)

            # in case the last event in the database does not longer exist at Stripe
            # the url below must be called (events are removed after 30 days)
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/events?&limit=100",
                text=json.dumps(stripe_response_part2),
            )
            call_command("check_pending_webhooks")

            # make sure the --site parameter works - pass not existing site id - should fail
            with self.assertRaises(Site.DoesNotExist):
                call_command("check_pending_webhooks", site=-1)

    def test_dispute(self):
        self.assertEqual(StripeWebhook.objects.count(), 0)
        payload = {
            "object": "event",
            "type": "charge.dispute.created",
            "id": "evt_123",
            "api_version": "2018-01-01",
            "created": 1503477866,
            "data": {
                "object": {
                    "id": "dp_ANSJH7zPDQPGqPEw0Cxq",
                    "object": "dispute",
                    "charge": "ch_5Q4BjL06oPWwho",
                    "evidence": {
                        "customer_name": "Jane Austen",
                        "customer_purchase_ip": "127.0.0.1",
                        "product_description": "An Awesome product",
                        "shipping_tracking_number": "Z01234567890",
                        "uncategorized_text": "Additional notes and comments",
                    },
                    "evidence_details": {"due_by": 1403047735, "submission_count": 1},
                }
            },
        }
        self.client.credentials(**self._get_signature_headers(payload))
        response = self.client.post(reverse("stripe-webhooks"), data=payload, format="json")
        self.assertEqual(201, response.status_code)

    @requests_mock.Mocker()
    def test_customer_update(self, m):
        payload = {
            "id": "evt_xyz",
            "object": "event",
            "api_version": "2018-01-01",
            "created": 1503477866,
            "data": {
                "object": {
                    "id": "cus_xyz",
                    "object": "customer",
                    "sources": [{"id": "card_xyz"}],
                }
            },
            "request": {"id": "req_putcEg4hE9bkUb", "idempotency_key": None},
            "type": "customer.updated",
        }
        customer_api_response = {
            "id": "cus_xyz",
            "object": "customer",
            "account_balance": 0,
            "created": 1476810921,
            "currency": "usd",
            "default_source": None,
            "delinquent": False,
            "description": None,
            "discount": None,
            "email": None,
            "livemode": False,
            "metadata": {},
            "shipping": None,
            "sources": {
                "object": "list",
                "data": [  # different than in Webhook (data from Webhook is not always up to date!)
                    {"id": "card_xyz", "object": "card"}
                ],
                "has_more": False,
                "total_count": 1,
                "url": "/v1/customers/cus_xyz/sources",
            },
            "subscriptions": {
                "object": "list",
                "data": [],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/customers/cus_xyz/subscriptions",
            },
        }

        self._create_customer()
        m.register_uri(
            "GET",
            "https://api.stripe.com/v1/customers/cus_xyz",
            text=json.dumps(customer_api_response),
        )
        url = reverse("stripe-webhooks")
        self.client.credentials(**self._get_signature_headers(payload))
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.sources, [{"id": "card_xyz", "object": "card"}])

        # customer should also be updated when one of it's sources is updated
        # (although if a card is removed or added, Stripe will trigger customer.updated webhook)
        payload["type"] = "customer.source.updated"
        payload["id"] = "evt_123"
        payload["data"]["object"] = {
            "id": "card_1BhOfILoWm2f6pRwe4gkIJc7",
            "object": "card",
            "customer": "cus_xyz",
        }
        self.client.credentials(**self._get_signature_headers(payload))
        with mock.patch("aa_stripe.models.StripeCustomer.refresh_from_stripe") as mocked_refresh:
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201, response.content)
            mocked_refresh.assert_called()

        # make sure that any Stripe API error will not cause 500 error
        self.customer.sources = []
        self.customer.save()
        payload["id"] = "evt_abc"
        self.client.credentials(**self._get_signature_headers(payload))
        with mock.patch("aa_stripe.models.StripeCustomer.refresh_from_stripe") as mocked_refresh:
            mocked_refresh.side_effect = stripe.error.APIError("error")
            response = self.client.post(url, data=payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.customer.refresh_from_db()
            self.assertEqual(self.customer.sources, [])
