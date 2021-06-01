=========
aa-stripe
=========
|pypi|_ |coveralls|_

Stripe integration for Django-based projects

This project's target is to make the Stripe API easier to use in Django-based applications.
At the moment the library supports:

* charging users
* plans
* subscriptions
* webhooks

**Support for Python 2.7 has been dropped since aa-stripe 0.6.0.**

Installation
============
Add ``aa_stripe`` to your app's ``INSTALLED_APPS``, and also set ``STRIPE_API_KEY`` in project settings. After all please migrate the app (``./manage.py migrate aa_stripe``).
Add ``STRIPE_WEBHOOK_ENDPOINT_SECRET`` into your settings from stripe webhooks configuration to enable webhooks.
Add ``STRIPE_USER_MODEL`` if it is different than settings.AUTH_USER_MODEL. In example when CC is connected to office not person. ``STRIPE_USER_MODEL`` defaults to AUTH_USER_MODEL.

Add ``aa_stripe.api_urls`` into your url conf.


Usage
=====


Creating a token for user
-------------------------
Use stripe.js (https://stripe.com/docs/stripe.js) to get single use token (stripe.js->createToken) and send it to API using ``/aa-stripe/customers`` to create Customer for the user. It runs:

::

    customer = stripe.Customer.create(source=data["id"]) # data is the response dictionary from Stripe API (in front-end)
    token = StripeToken.objects.create(user=request.user, content=data,
                                     customer_id=customer["id"])

This endpoint requires authenticated user. In case you need diferent implementation (like one call with register) you'll have to adjust your code.

Charging
--------
First of all, make sure to obtain Stripe user token from the Stripe API, and then save it to ``aa_stripe.models.StripeToken``, for example:
::

  import stripe
  from aa_stripe.models import StripeToken

  customer = stripe.Customer.create(source=data["id"]) # data is the response dictionary from Stripe API (in front-end)
  token = StripeToken.objects.create(user=request.user, content=data,
                                     customer_id=customer["id"])

To charge users, create an instance of ``aa_stripe.models.StripeCharge`` model and then call the ``charge()`` method:
::

  c = StripeCharge.objects.create(user=user, token=token, amount=500,  # in cents
                                  description="Charge for stuff",  # sent to Stripe
                                  comment="Comment for internal information",
                                  statement_descriptor="My Company" # sent to Stripe
  )
  c.charge()

Upon successfull charge also sends signal, ``stripe_charge_succeeded`` with instance as single parameter.

If charge fails due to CardError, ``charge_attept_failed`` is set to True and this charge will not be automatically retried by ``charge_stripe`` command. Signal ``stripe_charge_card_exception`` with instance and exception will be send.

There is also a management command called ``charge_stripe`` in case you need to process all the remaining charges or to run it by cron.

Subscriptions support
---------------------
With Stripe user token already obtained you can create subscription.
::

  import stripe
  from aa_stripe.models import StripeSubscription

  subscription = StripeSubscription.objects.create(
    customer=self.customer,
    user=self.user,
    plan=self.plan,
    metadata={"name": "test subscription"},
  )

The newly created object is not sent to Stripe just yet.
::

  subscription_data = subscription.create_at_stripe()

The command above returns whole subscription data send by stripe, including, in example, discounts.

https://stripe.com/docs/api#subscriptions

Utility functions for subscriptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* subscription.refresh_from_stripe() - gets updated subscription data from Stripe. Example usage: parsing webhooks - when webhook altering subscription is received it is good practice to verify the subscription at Stripe before making any actions.
* subscription.cancel() - cancels subscription at Stripe.
* StripeSubscription.get_subcriptions_for_cancel() - returns all subscriptions that should be canceled. Stripe does not support end date for subscription so it is up the user to implement expiration mechanism. Subscription has end_date that can be used for that.
* StripeSubscription.end_subscriptions() - cancels all subscriptions on Stripe that has passed end date. Use with caution, check internal comments.
* management command: end_subscription.py. Terminates outdated subscriptions in a safe way. In case of error returns it at the end, using Sentry if available or in console. Should be used in cron script. By default sets at_period_end=True.

Subscription Plans
------------------
Subscription Plans can be created using Stripe UI however there are cases when those needs to be created using API.
::

  import stripe
  from aa_stripe.models import StripeSubscriptionPlan

  plan = StripeSubscriptionPlan.objects.create(
    source={"a": "b"},
    amount=5000,
    name="gold-basic",
    interval=StripeSubscriptionPlan.INTERVAL_MONTH,
    interval_count=3,
  )

As with Subscription, the object has to be sent to stripe.
::

  plan_data = plan.create_at_stripe()

The command above returns whole plan data send by stripe.

https://stripe.com/docs/api#plans


Coupons Support
---------------
Stripe coupons can be created both in the Stripe Dashboard and using the ``aa_stripe.models.StripeCoupon`` model, and also if webhooks are properly configured in your app, you will be able to see all changes related to coupons made in the Stripe Dashboard.
This works both ways, if a coupon was created, edited or deleted on the application side, the list of coupons in Stripe will be updated respectively.
::

    from aa_stripe.models import StripeCoupon

    coupon = StripeCoupon.objects.create(
        coupon_id="SALE10",
        duration=StripeCoupon.DURATION_FOREVER,
        currency="usd",
        amount_off=10,  # in dollars
    )
    # coupon was created at Stripe
    coupon.delete()
    # coupon was deleted from Stripe, but the StripeCoupon object is kept
    print(coupon.is_deleted)  # True

**Important:** When updating coupon data, do not use the ``StripeCoupon.objects.update()`` method, because it does not call the ``StripeCoupon.save()`` method, and therefore the coupon will not be updated at Stripe.

The refresh_coupons management command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To make sure your app is always up to date with Stripe, the ``refresh_coupons`` management command should be run chronically.
It allows to periodically verify if all coupons are correctly stored in your app and no new coupons were created or deleted at Stripe.

For more information about coupons, see: https://stripe.com/docs/api#coupons


Webhooks support
----------------
All webhooks should be sent to ``/aa-stripe/webhooks`` url. Add ``STRIPE_WEBHOOK_ENDPOINT_SECRET`` to your settings to enable webhook verifications. Each received webhook is saved as StripeWebhook object in database. User need to add parsing webhooks depending on the project.
Be advised. There might be times that Webhooks will not arrive because of some error or arrive in incorrect order. When parsing webhook it is also good to download the refered object to verify it's state.

Stripe has the weird tendency to stop sending webhooks, and they have not fixed it yet on their side. To make sure all events have arrived into your system, the ``check_pending_webhooks`` management command should be run chronically.
In case there is more pending webhooks than specified in the ``STRIPE_PENDING_WEBHOOKS_THRESHOLD`` variable in your settings (default: ``20``), an email to project admins will be sent with ids of the pending events, and also the command will fail raising an exception,
so if you have some kind of error tracking service configured on your servers (for example: `Sentry <https://sentry.io>`_), you will be notified. Also if ``ENV_PREFIX`` is specified in your settings file, it will be included in the email to admins to indicate on which server the fail occurred.

By default the site used in the ``check_pending_webhooks`` command is the first ``django.contrib.sites.models.Site`` object from the database, but in case you need to use some other site, please use the ``--site`` parameter to pass your site's id.

Parsing webhooks
^^^^^^^^^^^^^^^^
To parse webhooks, you can connect to the ``aa_stripe.models.webhook_pre_parse`` signal, which is sent each time a
``StripeWebhook`` object is parsed.

Sample usage:

::

    from aa_stripe.models import StripeWebhook, webhook_pre_parse

    def stripewebhook_pre_parse(sender, instance, event_type, event_model, event_action, **kwargs):
        if not instance.is_parsed:
            # parse

    webhook_pre_parse.connect(stripewebhook_pre_parse, sender=StripeWebhook)

Arguments:

* sender - the ``StripeWebhook`` class
* instance - the ``StripeWebhook`` event object
* event_type - Stripe event type (for example: ``coupon.created``, ``invoice.payment_failed``, ``ping``, etc., see: https://stripe.com/docs/api#event_types)
* event_model - the model which created the event (for example: ``coupon``, ``invoice``, ``charge.dispute``, etc.)
* event_action - the action done on the ``event_model`` (for example: ``created``, ``updated``, ``payment_failed``, etc.)

Both ``event_model`` and ``event_action`` equal to ``None`` if ``event_type`` is a ``ping`` event.

Updating customer card data
---------------------------
StripeCustomer.sources list is updated after receiving Webhook from Stripe about updating the customer object. It is a list of `Stripe source <https://stripe.com/docs/api#sources>`_ objects.

Another way of updating the credit card information is to run the `refresh_customers` management command in cron.

Support
=======
* Django 2.2-3.2
* Python 3.6-3.9

.. |pypi| image:: https://img.shields.io/pypi/v/aa-stripe.svg
.. _pypi: https://pypi.python.org/pypi/aa-stripe

.. |coveralls| image:: https://coveralls.io/repos/github/HealthByRo/aa-stripe/badge.svg?branch=master
.. _coveralls: https://coveralls.io/github/HealthByRo/aa-stripe
