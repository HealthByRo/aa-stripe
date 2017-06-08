# -*- coding: utf-8 -*-
from aa_stripe.api import CustomersAPI, WebhookAPI
from django.conf.urls import url
from rest_framework.routers import DefaultRouter

urlpatterns = [
    url(r"^aa-stripe/customers$", CustomersAPI.as_view(), name="stripe-customers"),
    url(r"^aa-stripe/webhooks$", WebhookAPI.as_view(), name="stripe-webhooks"),
]

router = DefaultRouter()
urlpatterns += router.urls
