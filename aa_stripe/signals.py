# -*- coding: utf-8 -*-
import django.dispatch

stripe_charge_succeeded = django.dispatch.Signal()
stripe_charge_card_exception = django.dispatch.Signal()
stripe_charge_refunded = django.dispatch.Signal()
