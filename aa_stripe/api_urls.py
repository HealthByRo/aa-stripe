# -*- coding: utf-8 -*-
from aa_stripe.api import CustomersAPI
from django.conf.urls import url
from rest_framework.routers import DefaultRouter

urlpatterns = [
    url(r"^aa-stripe/customers$", CustomersAPI.as_view(), name="stripe-customers"),
]

router = DefaultRouter()
urlpatterns += router.urls
