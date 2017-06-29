"""Test charging users through the StripeCharge model"""
import requests_mock
import simplejson as json
from django.contrib.auth import get_user_model
from django.test import TestCase

from aa_stripe.models import StripeSubscriptionPlan

UserModel = get_user_model()


class TestSubscriptionsPlans(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create(email="foo@bar.bar", username="foo", password="dump-password")

    def test_plan_creation(self):
        self.assertEqual(StripeSubscriptionPlan.objects.count(), 0)
        plan = StripeSubscriptionPlan.objects.create(
            source={"a": "b"},
            amount=5000,
            name="gold-basic",
            interval=StripeSubscriptionPlan.INTERVAL_MONTH,
            interval_count=3,
        )
        self.assertFalse(plan.is_created_at_stripe)
        with requests_mock.Mocker() as m:
            m.register_uri('POST', 'https://api.stripe.com/v1/plans', [{'text': json.dumps({
                "id": plan.id,
                "object": "plan",
                "amount": 5000,
                "created": 1496921795,
                "currency": "usd",
                "interval": "month",
                "interval_count": 3,
                "livemode": False,
                "metadata": {},
                "name": "Gold basic",
                "statement_descriptor": None,
                "trial_period_days": None
            })}])
            plan.create_at_stripe()
            self.assertTrue(plan.is_created_at_stripe)
            self.assertEqual(plan.stripe_response["id"], plan.id)
            self.assertEqual(plan.stripe_response["amount"], 5000)
