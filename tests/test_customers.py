import requests_mock
import simplejson as json
from django.contrib.auth import get_user_model
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from aa_stripe.models import StripeCustomer

UserModel = get_user_model()


class TestCreatingUsers(APITestCase):
    def setUp(self):
        self.user = UserModel.objects.create(email="foo@bar.bar", username="foo", password="dump-password")

    def get_stripe_js_response(self):
        return {
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

    def get_successful_create_stripe_customer_response(self, id="cus_9Oop0gQ1R1ATMi"):
        return {
            "id": id,
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
                "data": [],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/customers/{}/sources".format(id)
            },
            "subscriptions": {
                "object": "list",
                "data": [],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/customers/{}/subscriptions".format(id)
            }
        }

    def test_user_create(self):
        self.assertEqual(StripeCustomer.objects.count(), 0)
        url = reverse("stripe-customers")
        stripe_js_response = self.get_stripe_js_response()

        stripe_customer_id = "cus_9Oop0gQ1R1ATMi"
        data = {}
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)  # not logged

        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)

        with requests_mock.Mocker() as m:
            m.register_uri('POST', 'https://api.stripe.com/v1/customers', [
                {
                    "text": json.dumps({
                        "error": {"message": "Your card was declined.", "type": "card_error", "param": "",
                                  "code": "card_declined", "decline_code": "do_not_honor"}
                    }),
                    "status_code": 400
                },
                {
                    "text": json.dumps(self.get_successful_create_stripe_customer_response(stripe_customer_id))
                }])

            # test response error
            stripe_customer_qs = StripeCustomer.objects.filter(is_created_at_stripe=True)
            data = {"stripe_js_response": stripe_js_response}
            self.client.force_authenticate(user=self.user)
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(m.call_count, 1)
            self.assertEqual(set(response.data.keys()), {"stripe_error"})
            self.assertEqual(response.data["stripe_error"], "Your card was declined.")
            self.assertEqual(stripe_customer_qs.count(), 0)

            # test success response from Stripe
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(m.call_count, 2)
            self.assertEqual(stripe_customer_qs.count(), 1)
            customer = stripe_customer_qs.first()
            self.assertTrue(customer.is_active)
            self.assertEqual(customer.user, self.user)
            self.assertEqual(customer.stripe_js_response, stripe_js_response)
            self.assertEqual(customer.stripe_customer_id, stripe_customer_id)
            self.assertEqual(customer.stripe_response["id"], stripe_customer_id)

    def test_user_get_stripe_customer_id(self):
        url = reverse("stripe-customers")
        stripe_customer_id = "cus_Bw7eXawkf0zsal"

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403)  # not logged

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 404)  # logged in but cunstomer is not yet created

        with requests_mock.Mocker() as m:
            m.register_uri(
                'POST', 'https://api.stripe.com/v1/customers',
                [{
                    "text": json.dumps(self.get_successful_create_stripe_customer_response(stripe_customer_id))
                }])
            data = {"stripe_js_response": self.get_stripe_js_response()}
            self.client.post(url, data, format="json")

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)  # logged in and cunstomer is created
        self.assertEqual(set(response.data.keys()), {"stripe_customer_id"})
        self.assertEqual(response.data["stripe_customer_id"], stripe_customer_id)
