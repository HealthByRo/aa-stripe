import time
from datetime import datetime

import requests_mock
import simplejson as json
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APITestCase

from aa_stripe.forms import StripeCouponForm
from aa_stripe.models import StripeCoupon


class TestCoupons(APITestCase):
    def _create_coupon(self, coupon_id, amount_off=None, duration=StripeCoupon.DURATION_FOREVER):
        with requests_mock.Mocker() as m:
            # create a simple coupon which will be used for tests
            stripe_response = {
                "id": coupon_id,
                "object": "coupon",
                "amount_off": amount_off,
                "created": int(time.mktime(datetime.now().timetuple())),
                "currency": "usd",
                "duration": duration,
                "duration_in_months": None,
                "livemode": False,
                "max_redemptions": None,
                "metadata": {},
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

    @freeze_time("2016-01-01 00:00:00")
    def test_create(self):
        # test creating simple coupon with no coupon_id specified (will be generated by Stripe)
        stripe_response = {
            "id": "25OFF",
            "object": "coupon",
            "amount_off": 1,
            "created": int(time.mktime(datetime.now().timetuple())),
            "currency": "usd",
            "duration": StripeCoupon.DURATION_FOREVER,
            "duration_in_months": None,
            "livemode": False,
            "max_redemptions": None,
            "metadata": {},
            "percent_off": 25,
            "redeem_by": None,
            "times_redeemed": 0,
            "valid": True
        }
        with requests_mock.Mocker() as m:
            m.register_uri("POST", "https://api.stripe.com/v1/coupons", text=json.dumps(stripe_response))
            coupon = StripeCoupon.objects.create(
                duration=StripeCoupon.DURATION_FOREVER,
                percent_off=25
            )
            self.assertEqual(coupon.coupon_id, stripe_response["id"])
            self.assertEqual(coupon.created, timezone.make_aware(datetime.fromtimestamp(stripe_response["created"])))
            self.assertEqual(coupon.stripe_response, stripe_response)

            # test creating coupon with coupon_id
            stripe_response["id"] = "YOLO1"
            m.register_uri("POST", "https://api.stripe.com/v1/coupons", text=json.dumps(stripe_response))
            coupon = StripeCoupon.objects.create(
                coupon_id=stripe_response["id"],
                duration=StripeCoupon.DURATION_FOREVER
            )
            self.assertEqual(coupon.coupon_id, stripe_response["id"])

    def test_update(self):
        with requests_mock.Mocker() as m:
            stripe_response = {
                "id": "25OFF",
                "object": "coupon",
                "amount_off": 1,
                "created": int(time.mktime(datetime.now().timetuple())),
                "currency": "usd",
                "duration": StripeCoupon.DURATION_FOREVER,
                "duration_in_months": None,
                "livemode": False,
                "max_redemptions": None,
                "metadata": {},
                "percent_off": 25,
                "redeem_by": None,
                "times_redeemed": 0,
                "valid": True
            }
            coupon = self._create_coupon(coupon_id="25OFF", duration=StripeCoupon.DURATION_FOREVER, amount_off=1)
            self.assertFalse(coupon.is_deleted)

            # try accessing coupon that does not exist - should delete the coupon from our database
            m.register_uri("GET", "https://api.stripe.com/v1/coupons/25OFF", status_code=404, text=json.dumps({
                "error": {
                    "type": "invalid_request_error"
                }
            }))
            coupon.metadata = {"yes": "no"}
            coupon.save()
            coupon.refresh_from_db()
            self.assertTrue(coupon.is_deleted)

            # try changing other Stripe data than coupon's metadata
            m.register_uri("GET", "https://api.stripe.com/v1/coupons/25OFF", text=json.dumps(stripe_response))
            m.register_uri("POST", "https://api.stripe.com/v1/coupons/25OFF", text=json.dumps(stripe_response))
            coupon = self._create_coupon(coupon_id="25OFF", duration=StripeCoupon.DURATION_FOREVER, amount_off=1)
            coupon.duration = StripeCoupon.DURATION_ONCE
            coupon.save()
            coupon.refresh_from_db()
            self.assertNotEqual(coupon.duration, StripeCoupon.DURATION_ONCE)

    def test_delete(self):
        coupon = self._create_coupon(coupon_id="CPON", amount_off=1, duration=StripeCoupon.DURATION_FOREVER)
        self.assertFalse(coupon.is_deleted)
        stripe_response = {
            "id": "CPON",
            "object": "coupon",
            "amount_off": 1,
            "created": int(time.mktime(datetime.now().timetuple())),
            "currency": "usd",
            "duration": StripeCoupon.DURATION_FOREVER,
            "duration_in_months": None,
            "livemode": False,
            "max_redemptions": None,
            "metadata": {},
            "percent_off": 25,
            "redeem_by": None,
            "times_redeemed": 0,
            "valid": True
        }
        with requests_mock.Mocker() as m:
            for method in ["GET", "DELETE"]:
                m.register_uri(method, "https://api.stripe.com/v1/coupons/CPON", text=json.dumps(stripe_response))
            coupon.delete()
            coupon.refresh_from_db()
            self.assertTrue(coupon.is_deleted)

    def test_admin_form(self):
        # test correct creation
        data = {
            "coupon_id": "25OFF",
            "amount_off": 1,
            "currency": "USD",
            "duration": StripeCoupon.DURATION_ONCE,
            "metadata": {},
            "times_redeemed": 0,
            "valid": True
        }
        self.assertTrue(StripeCouponForm(data=data).is_valid())

        # test passing none of amount_off or percent_off
        del data["amount_off"]
        self.assertFalse(StripeCouponForm(data=data).is_valid())

        # test passing both of amount_off and percent_off
        data["amount_off"] = 100
        data["percent_off"] = 10
        self.assertFalse(StripeCouponForm(data=data).is_valid())
        del data["percent_off"]

        # test passing duration repeating with empty duration_in_months
        data["duration"] = StripeCoupon.DURATION_REPEATING
        self.assertFalse(StripeCouponForm(data=data).is_valid())

        # test passing duration_in_months when duration is not repeating
        data["duration"] = StripeCoupon.DURATION_ONCE
        data["duration_in_months"] = 1
        self.assertFalse(StripeCouponForm(data=data).is_valid())
        del data["duration_in_months"]

        stripe_response = {
            "id": "25OFF",
            "object": "coupon",
            "amount_off": 1,
            "created": int(time.mktime(datetime.now().timetuple())),
            "currency": "usd",
            "duration": StripeCoupon.DURATION_FOREVER,
            "duration_in_months": None,
            "livemode": False,
            "max_redemptions": None,
            "metadata": {},
            "percent_off": 25,
            "redeem_by": None,
            "times_redeemed": 0,
            "valid": True
        }
        with requests_mock.Mocker() as m:
            for method in ["GET", "POST", "DELETE"]:
                m.register_uri(method, "https://api.stripe.com/v1/coupons/25OFF", text=json.dumps(stripe_response))
            coupon = self._create_coupon(data["coupon_id"], amount_off=1)

            # test creating a new coupon, when there is one that is not deleted
            self.assertTrue(StripeCoupon.objects.filter(coupon_id=data["coupon_id"], is_deleted=False).exists())
            self.assertFalse(StripeCouponForm(data=data).is_valid())

            # delete and try again
            coupon.is_deleted = True
            coupon.save()
            self.assertTrue(StripeCouponForm(data=data).is_valid())
