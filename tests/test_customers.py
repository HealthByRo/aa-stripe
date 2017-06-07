import requests_mock
import simplejson as json
from aa_stripe.models import StripeCustomer
from django.contrib.auth import get_user_model
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

UserModel = get_user_model()


class TestCreatingUsers(APITestCase):
    def setUp(self):
        self.user = UserModel.objects.create(email="foo@bar.bar", username="foo", password="dump-password")

    def test_user_create(self):
        self.assertEqual(StripeCustomer.objects.count(), 0)
        url = reverse("stripe-customers")
        stripe_js_response = {
            "id": "tok_193mTaHSTEMJ0IPXhhZ5vuTX",
            "object": "customer",
            "client_ip": None,
            "created": 1476277734,
            "livemode": False,
            "type": "card",
            "used": False,
            "card": {
                "id": "card_193mTaHSTEMJ0IPXIoOiuOdF",
                "object": "card",
                "address_city": None,
                "address_country": None,
                "address_line1": None,
                "address_line1_check": None,
                "address_line2": None,
                "address_state": None,
                "address_zip": None,
                "address_zip_check": None,
                "brand": "Visa",
                "country": "US",
                "cvc_check": None,
                "dynamic_last4": None,
                "exp_month": 8,
                "exp_year": 2017,
                "funding": "credit",
                "last4": "4242",
                "name": None,
                "customerization_method": None,
                "metadata": {},
            },
        }

        data = {}
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)  # not logged

        with requests_mock.Mocker() as m:
            m.register_uri('POST', 'https://api.stripe.com/v1/customers', [{'text': json.dumps({
                "id": "cus_9Oop0gQ1R1ATMi",
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
                "metadata": {
                },
                "shipping": None,
                "sources": {
                    "object": "list",
                    "data": [

                    ],
                    "has_more": False,
                    "total_count": 0,
                    "url": "/v1/customers/cus_9Oop0gQ1R1ATMi/sources"
                },
                "subscriptions": {
                    "object": "list",
                    "data": [

                    ],
                    "has_more": False,
                    "total_count": 0,
                    "url": "/v1/customers/cus_9Oop0gQ1R1ATMi/subscriptions"
                }
            })}])
            data = {"stripe_js_response": stripe_js_response}
            self.client.force_authenticate(user=self.user)
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, 201)

            self.assertEqual(m.call_count, 1)
            self.assertEqual(StripeCustomer.objects.count(), 1)
            customer = StripeCustomer.objects.first()
            self.assertTrue(customer.is_active)
            self.assertEqual(customer.user, self.user)
            self.assertEqual(customer.stripe_js_response, stripe_js_response)
            self.assertEqual(customer.stripe_customer_id, "cus_9Oop0gQ1R1ATMi")
            self.assertEqual(customer.stripe_response["id"], "cus_9Oop0gQ1R1ATMi")
