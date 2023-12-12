# -*- coding: utf-8 -*-
from django.urls import re_path
from rest_framework.routers import DefaultRouter

from aa_stripe.api import CouponDetailsAPI, CustomerDetailsAPI, CustomersAPI, WebhookAPI

urlpatterns = [
    re_path(r"^aa-stripe/coupons/(?P<coupon_id>.*)$", CouponDetailsAPI.as_view(), name="stripe-coupon-details"),
    re_path(r"^aa-stripe/customers$", CustomersAPI.as_view(), name="stripe-customers"),
    re_path(r"^aa-stripe/customers/(?P<stripe_customer_id>[\w\-]+)$", CustomerDetailsAPI.as_view(),
            name="stripe-customer-details"),
    re_path(r"^aa-stripe/webhooks$", WebhookAPI.as_view(), name="stripe-webhooks")
]

router = DefaultRouter()
urlpatterns += router.urls
