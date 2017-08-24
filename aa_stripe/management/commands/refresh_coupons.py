# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from django.core.management.base import BaseCommand

from aa_stripe.models import StripeCoupon
from aa_stripe.utils import timestamp_to_timezone_aware_date


class Command(BaseCommand):
    help = "Update the coupon list from Stripe API"

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_API_KEY

        counts = {
            "created": 0,
            "updated": 0,
            "deleted": 0
        }
        active_coupons_ids = []
        last_stripe_coupon = None
        while True:
            stripe_coupon_list = stripe.Coupon.list(starting_after=last_stripe_coupon)
            for stripe_coupon in stripe_coupon_list["data"]:
                try:
                    coupon = StripeCoupon.objects.get(
                        coupon_id=stripe_coupon.id, created=timestamp_to_timezone_aware_date(stripe_coupon["created"]),
                        is_deleted=False)
                    counts["updated"] += coupon.update_from_stripe_data(stripe_coupon)
                except StripeCoupon.DoesNotExist:
                    coupon = StripeCoupon(coupon_id=stripe_coupon.id)
                    coupon.save(force_retrieve=True)
                    counts["created"] += 1

                # indicate which coupons should have is_deleted=False
                active_coupons_ids.append(coupon.pk)

            if not stripe_coupon_list["has_more"]:
                break
            else:
                last_stripe_coupon = stripe_coupon_list["data"][-1]

        # update can be used here, because those coupons does not exist in the Stripe API anymore
        counts["deleted"] = StripeCoupon.objects.filter(is_deleted=False).exclude(
            pk__in=active_coupons_ids).update(is_deleted=True)
        print("Coupons created: {created}, updated: {updated}, deleted {deleted}".format(**counts))
