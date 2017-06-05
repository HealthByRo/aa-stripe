=============
django-stripe
=============
|travis|_ |pypi|_ |coveralls|_ |requiresio|_

Stripe integration for Django-based projects

This project's target is to make the Stripe API easier to use in Django-based applications.
At the moment the library supports:

* charging users

Installation
============
Add ``django_stripe`` to your app's ``INSTALLED_APPS``, and also set ``STRIPE_API_KEY`` in project settings. After all please migrate the app (``./manage.py migrate django_stripe``).

Usage
=====

Charging
--------
First of all, make sure to obtain Stripe user token from the Stripe API, and then save it to ``django_stripe.models.StripeToken``, for example:
::
  
  customer = stripe.Customer.create(source=data["id"])
  token = StripeToken.objects.create(user=request.user, content=data, # JSON response from Stripe API (in front-end) 
                                    customer_id=customer["id"])
  
To charge users, create an instance of ``django_stripe.models.StripeCharge`` model:
::

  StripeCharge.objects.create(user=user, token=token, amount=500 # in cents
                              description="Charge for stuff" # sent to Stripe
                              comment="Comment for internal information")
                              
The last thing is to execute the ``./manage.py charge_stripe`` command (should be run chronically), which will send all requests to the Stripe API (you can check ``StripeCharge.is_charged`` and ``StripeCharge.stripe_charge_id`` fields, to see whether charge was completed).

Support
=======
* Django 1.11
* Python 2.7, 3.6

.. |travis| image:: https://secure.travis-ci.org/ArabellaTech/django-stripe.svg?branch=master
.. _travis: http://travis-ci.org/ArabellaTech/django-stripe

.. |pypi| image:: https://img.shields.io/pypi/v/django-stripe.svg
.. _pypi: https://pypi.python.org/pypi/django-stripe

.. |coveralls| image:: https://coveralls.io/repos/github/ArabellaTech/django-stripe/badge.svg?branch=master
.. _coveralls: https://coveralls.io/github/ArabellaTech/django-stripe

.. |requiresio| image:: https://requires.io/github/ArabellaTech/django-stripe/requirements.svg?branch=master
.. _requiresio: https://requires.io/github/ArabellaTech/django-stripe/requirements/
