"""Test charging users through the StripeCharge model"""
from datetime import timedelta

import mock
import requests_mock
import simplejson as json
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from aa_stripe.models import StripeCustomer, StripeSubscription, StripeSubscriptionPlan

UserModel = get_user_model()


class TestSubscriptions(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create(email="foo@bar.bar", username="foo", password="dump-password")
        self.customer = StripeCustomer.objects.create(
            user=self.user, stripe_customer_id="example", stripe_js_response='"foo"')
        self.plan = StripeSubscriptionPlan.objects.create(
            amount=100,
            is_created_at_stripe=True,
            name="example plan",
            interval=StripeSubscriptionPlan.INTERVAL_MONTH,
            interval_count=3,
        )

    def test_subscription_creation(self):
        self.assertEqual(StripeSubscription.objects.count(), 0)
        subscription = StripeSubscription.objects.create(
            customer=self.customer,
            user=self.user,
            plan=self.plan,
            metadata={"name": "test subscription"},
        )
        self.assertFalse(subscription.is_created_at_stripe)
        with requests_mock.Mocker() as m:
            stripe_subscription_raw = {
                "id": "sub_AnksTMRdnWfq9m",
                "object": "subscription",
                "application_fee_percent": None,
                "cancel_at_period_end": False,
                "canceled_at": None,
                "created": 1496861935,
                "current_period_end": 1499453935,
                "current_period_start": 1496861935,
                "customer": "cus_AnksoMvJIinvZm",
                "discount": None,
                "ended_at": None,
                "items": {
                    "object": "list",
                    "data": [{
                        "id": "si_1AS9Mp2eZvKYlo2Cmmf01eoi",
                        "object": "subscription_item",
                        "created": 1496861935,
                        "plan": {
                            "id": self.plan.id,
                            "object": "plan",
                            "amount": 100,
                            "created": 1496857185,
                            "currency": "usd",
                            "interval": "month",
                            "interval_count": 3,
                            "livemode": False,
                            "metadata": {},
                            "name": "example plan",
                            "statement_descriptor": None,
                            "trial_period_days": None
                        },
                        "quantity": 1
                    }],
                    "has_more": False,
                    "total_count": 1,
                    "url": "/v1/subscription_items?subscription=sub_AnksTMRdnWfq9m"
                },
                "livemode": False,
                "metadata": {"name": "test subscription"},
                "plan": {
                    "id": self.plan.id,
                    "object": "plan",
                    "amount": 100,
                    "created": 1496857185,
                    "currency": "usd",
                    "interval": "month",
                    "interval_count": 3,
                    "livemode": False,
                    "metadata": {},
                    "name": "example plan",
                    "statement_descriptor": None,
                    "trial_period_days": None
                },
                "quantity": 1,
                "start": 1496861935,
                "status": "active",
                "tax_percent": None,
                "trial_end": None,
                "trial_start": None
            }

            m.register_uri("POST", "https://api.stripe.com/v1/subscriptions",
                           [{"text": json.dumps(stripe_subscription_raw)}])

            subscription.create_at_stripe()
            self.assertTrue(subscription.is_created_at_stripe)
            self.assertEqual(subscription.stripe_response["id"], "sub_AnksTMRdnWfq9m")
            self.assertEqual(subscription.stripe_subscription_id, "sub_AnksTMRdnWfq9m")
            self.assertEqual(subscription.stripe_response["plan"]["name"], self.plan.name)
            self.assertEqual(subscription.stripe_response["plan"]["amount"], self.plan.amount)
            self.assertEqual(subscription.status, subscription.STATUS_ACTIVE)
            self.assertEqual(subscription.stripe_response["current_period_start"], 1496861935)

            # update
            stripe_subscription_raw["status"] = "past_due"
            stripe_subscription_raw["current_period_start"] = 1496869999
            m.register_uri("GET", "https://api.stripe.com/v1/subscriptions/sub_AnksTMRdnWfq9m",
                           [{"text": json.dumps(stripe_subscription_raw)}])
            subscription.refresh_from_stripe()
            self.assertEqual(subscription.status, subscription.STATUS_PAST_DUE)
            self.assertEqual(subscription.stripe_response["current_period_start"], 1496869999)

    @freeze_time("2017-06-29 12:00:00+00")
    def test_subscriptions_end(self):
        subscription = StripeSubscription.objects.create(
            customer=self.customer,
            user=self.user,
            plan=self.plan,
            metadata={"name": "test subscription"},
            end_date=timezone.now() + timedelta(days=5),
            status=StripeSubscription.STATUS_ACTIVE,
        )
        self.assertIsNone(subscription.canceled_at)

        with mock.patch("aa_stripe.models.StripeSubscription._stripe_cancel") as mocked_cancel:
            ret = {
                "status": "canceled"
            }
            mocked_cancel.return_value = ret

            StripeSubscription.end_subscriptions()
            call_command("end_subscriptions")

            with freeze_time("2017-07-04 12:00:00+00"):
                call_command("end_subscriptions")
                mocked_cancel.assert_called_with(at_period_end=True)

                subscription.refresh_from_db()
                self.assertIsNotNone(subscription.canceled_at)

                mocked_cancel.reset_mock()
                call_command("end_subscriptions")
                mocked_cancel.assert_not_called()
