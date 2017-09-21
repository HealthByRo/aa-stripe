# -*- coding: utf-8 -*-
import django.dispatch

stripe_charge_completed = django.dispatch.Signal(providing_args=["instance"])
