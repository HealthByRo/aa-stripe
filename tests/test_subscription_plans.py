"""Test charging users through the StripeCharge model"""
from aa_stripe.models import StripeToken, StripeSubscription
from django.contrib.auth import get_user_model
from django.test import TestCase
import requests_mock
import simplejson as json

UserModel = get_user_model()


class TestSubscriptionsPlans(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create(email="foo@bar.bar", username="foo", password="dump-password")

    def test_subscription_creation(self):
        self.assertFalse(1)
        self.assertEqual(StripeSubscription.objects.count(), 0)
        token = StripeToken.objects.create(user=self.user, stripe_id="example", stripe_js_response="foo")
        subscription = StripeSubscription.objects.create(
            token=token,
            user=self.user,
            metadata={"name": "test subscription"},
        )
        self.assertFalse(subscription.is_created_at_stripe)
        with requests_mock.Mocker() as m:
            m.register_uri('POST', 'https://api.stripe.com/v1/customers', [{'text': json.dumps({
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
                            "id": "silver-plus-615",
                            "object": "plan",
                            "amount": 999,
                            "created": 1496857185,
                            "currency": "usd",
                            "interval": "month",
                            "interval_count": 1,
                            "livemode": False,
                            "metadata": {},
                            "name": "Silver Plus",
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
                    "id": "silver-plus-615",
                    "object": "plan",
                    "amount": 999,
                    "created": 1496857185,
                    "currency": "usd",
                    "interval": "month",
                    "interval_count": 1,
                    "livemode": False,
                    "metadata": {
                    },
                    "name": "Silver Plus",
                    "statement_descriptor": None,
                    "trial_period_days": None
                },
                "quantity": 1,
                "start": 1496861935,
                "status": "active",
                "tax_percent": None,
                "trial_end": None,
                "trial_start": None
            })}])

            subscription.create_at_stripe()
            self.assertTrue(subscription.is_created_at_stripe)
            self.assertEqual(subscription.stripe_response["id"], "sub_AnksTMRdnWfq9m")
            self.assertEqual(subscription.stripe_subscription_id, "sub_AnksTMRdnWfq9m")
            self.assertEqual(subscription.status, subscription.STATUS_ACTIVE)

        # Add help texts with links to stripe docs!
        # pola:
        # is_created_at_stripe=boolean
        # token
        # user
        # stripe_response
        # status
        # tax_percent, default:0
        # application_fee_percent, defaulf:0
        # coupon: none
        # metadata - Hash send to stripe
        # created
        # updated
