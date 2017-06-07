# -*- coding: utf-8 -*-
from aa_stripe.api import TokensAPI
from django.conf.urls import url
from rest_framework.routers import DefaultRouter

urlpatterns = [
    url(r"^aa-stripe/tokens$", TokensAPI.as_view(), name="stripe-tokens"),
]

router = DefaultRouter()
urlpatterns += router.urls
