import mock
import requests_mock
import simplejson as json
import stripe
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.reverse import reverse

from aa_stripe.models import StripeCustomer
from tests.test_utils import BaseTestCase

UserModel = get_user_model()


class TestCreatingUsers(BaseTestCase):
    def setUp(self):
        self.user = self._create_user()
        self.stripe_js_response = {
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

    def test_user_create(self):
        self.assertEqual(StripeCustomer.objects.count(), 0)
        url = reverse("stripe-customers")

        data = {}
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)  # not logged

        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)

        with requests_mock.Mocker() as m:
            m.register_uri(
                "POST",
                "https://api.stripe.com/v1/customers",
                [
                    {
                        "text": json.dumps(
                            {
                                "error": {
                                    "message": "Your card was declined.",
                                    "type": "card_error",
                                    "param": "",
                                    "code": "card_declined",
                                    "decline_code": "do_not_honor",
                                }
                            }
                        ),
                        "status_code": 400,
                    },
                    {
                        "text": json.dumps(
                            {
                                "id": "cus_9Oop0gQ1R1ATMi",
                                "object": "customer",
                                "account_balance": 0,
                                "created": 1476810921,
                                "currency": "usd",
                                "default_source": "card_xyz",
                                "delinquent": False,
                                "description": None,
                                "discount": None,
                                "email": None,
                                "livemode": False,
                                "metadata": {},
                                "shipping": None,
                                "sources": {
                                    "object": "list",
                                    "data": [{"id": "card_xyz", "object": "card"}],
                                    "has_more": False,
                                    "total_count": 1,
                                    "url": "/v1/customers/cus_9Oop0gQ1R1ATMi/sources",
                                },
                                "subscriptions": {
                                    "object": "list",
                                    "data": [],
                                    "has_more": False,
                                    "total_count": 0,
                                    "url": "/v1/customers/cus_9Oop0gQ1R1ATMi/subscriptions",
                                },
                            }
                        )
                    },
                ],
            )

            # test response error
            stripe_customer_qs = StripeCustomer.objects.filter(is_created_at_stripe=True)
            data = {"stripe_js_response": self.stripe_js_response}
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
            self.assertEqual(customer.stripe_js_response, self.stripe_js_response)
            self.assertEqual(customer.stripe_customer_id, "cus_9Oop0gQ1R1ATMi")
            self.assertEqual(customer.stripe_response["id"], "cus_9Oop0gQ1R1ATMi")
            self.assertEqual(customer.sources, [{"id": "card_xyz", "object": "card"}])
            self.assertEqual(customer.default_source, "card_xyz")

    def test_change_description(self):
        customer_id = self.stripe_js_response["id"]
        customer = StripeCustomer(user=self.user, stripe_customer_id=customer_id)
        api_url = "https://api.stripe.com/v1/customers/{customer_id}".format(customer_id=customer_id)
        with requests_mock.Mocker() as m:
            m.register_uri("GET", api_url, text=json.dumps(self.stripe_js_response))
            m.register_uri("POST", api_url, text=json.dumps(self.stripe_js_response))
            customer.change_description("abc")


class TestCustomerDetailsAPI(BaseTestCase):
    def setUp(self):
        self._create_user()
        self.second_user = self._create_user(email="second@user.com", set_self=False)
        self._create_customer(
            user=self.user, customer_id="cus_xyz", sources=[{"id": "card_1"}], default_source="card_1"
        )
        self.url = reverse("stripe-customer-details", args=["cus_xyz"])

    def test_api(self):
        # other user should not be able to update other user's customer
        self.client.force_authenticate(user=self.second_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "id": self.customer.id,
                "user": self.user.id,
                "stripe_customer_id": "cus_xyz",
                "is_active": True,
                "sources": [{"id": "card_1"}],
                "default_source": "card_1",
                "default_source_data": {"id": "card_1"},
            },
        )

        response = self.client.patch(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"stripe_js_response": ["This field is required."]})

        # test changing card with incorrect data
        data = {"stripe_js_response": {"card": {}}}
        response = self.client.patch(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"stripe_js_response": ["This field must contain JSON data from Stripe JS."]})

        # test adding new default card
        # customer response after update
        stripe_customer_response = {
            "id": "cus_xyz",
            "object": "customer",
            "created": 1476810921,
            "default_source": "card_2",
            "sources": {
                "object": "list",
                "data": [{"id": "card_1", "object": "card"}, {"id": "card_2", "object": "card"}],
                "has_more": False,
                "total_count": 1,
                "url": "/v1/customers/cus_xyz/sources",
            },
        }
        stripe_js_response = {
            "id": "tok_193mTaHSTEMJ0IPXhhZ5vuTX",
            "card": {
                "id": "card_2",
                "object": "card",
                "brand": "Visa",
                "exp_month": 8,
                "exp_year": 2017,
                "last4": "4242",
            },
        }
        data["stripe_js_response"] = stripe_js_response
        api_url = "https://api.stripe.com/v1/customers/cus_xyz"
        with requests_mock.Mocker() as m:
            m.register_uri("GET", api_url, text=json.dumps(stripe_customer_response))
            m.register_uri(
                "POST",
                api_url,
                [
                    {
                        "status_code": 400,
                        "text": json.dumps(
                            {
                                "error": {
                                    "message": "Some error.",
                                    "type": "customer_error",
                                    "param": "",
                                    "code": "error",
                                }
                            }
                        ),
                    },
                    {"status_code": 200, "text": json.dumps(stripe_customer_response)},
                ],
            )
            # test in case of error from Stripe
            response = self.client.patch(self.url, data, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, {"stripe_error": "Some error."})

            response = self.client.patch(self.url, data, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(dict(response.data["default_source_data"]), {"id": "card_2", "object": "card"})


class TestRefreshCustomersCommand(BaseTestCase):
    def setUp(self):
        self._create_customer(is_active=False, is_created_at_stripe=False)
        self.active_customer = self._create_customer()

    @requests_mock.Mocker()
    def test_command(self, m):
        def get_customer_data(customer_id, sources, default_source=None):
            return {
                "id": customer_id,
                "object": "customer",
                "sources": {
                    "object": "list",
                    "data": sources,
                    "has_more": False,
                    "total_count": 1,
                    "url": "/v1/customers/{}/sources".format(customer_id),
                },
                "default_source": default_source,
            }

        stripe_response_part1 = {
            "object": "list",
            "url": "/v1/customers",
            "has_more": True,
            "data": [get_customer_data("cus_xyz", [{"id": "card_1"}], default_source="card_1")],
        }
        stripe_response_part2 = {
            "object": "list",
            "url": "/v1/customers",
            "has_more": False,
            "data": [get_customer_data("cus_b", [{"id": "card_2"}])],
        }
        m.register_uri("GET", "https://api.stripe.com/v1/customers", text=json.dumps(stripe_response_part1))
        m.register_uri(
            "GET",
            "https://api.stripe.com/v1/customers?starting_after=cus_xyz",
            [
                {"text": "", "status_code": 500},  # make sure the command will try again
                {"text": json.dumps(stripe_response_part2), "status_code": 200},
            ],
        )
        call_command("refresh_customers", verbosity=2)
        self.active_customer.refresh_from_db()
        self.assertEqual(self.active_customer.default_source_data, {"id": "card_1"})

        # the command should fail if call to api fails more than 5 times
        with mock.patch("stripe.Customer.list") as mocked_list:
            mocked_list.side_effect = stripe.error.APIError()
            with self.assertRaises(stripe.error.APIError):
                call_command("refresh_customers")

    @requests_mock.Mocker()
    def test_customer_refresh_from_stripe(self, m):
        self._create_customer()
        api_url = "https://api.stripe.com/v1/customers/cus_xyz"
        api_response = {
            "id": "cus_xyz",
            "object": "customer",
            "account_balance": 0,
            "created": 1476810921,
            "currency": "usd",
            "default_source": "card_xyz",
            "delinquent": False,
            "description": None,
            "discount": None,
            "email": None,
            "livemode": False,
            "metadata": {},
            "shipping": None,
            "sources": {
                "object": "list",
                "data": [{"id": "card_xyz", "object": "card"}],
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
        m.register_uri("GET", api_url, text=json.dumps(api_response))
        self.customer.refresh_from_stripe()
        self.assertEqual(self.customer.sources, [{"id": "card_xyz", "object": "card"}])
        self.assertEqual(self.customer.default_source, "card_xyz")

    def test_get_default_source(self):
        self._create_customer()
        self.customer.sources = [{"id": "card_abc"}, {"id": "card_xyz"}]
        self.customer.save()

        self.assertIsNone(self.customer.default_source_data)
        self.customer.default_source = "card_xyz"
        self.customer.save()
        self.assertEqual(self.customer.default_source_data, {"id": "card_xyz"})
