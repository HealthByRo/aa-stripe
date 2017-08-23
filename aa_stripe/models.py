# -*- coding: utf-8 -*-
from datetime import datetime
from time import sleep

import simplejson as json
import stripe
from django.conf import settings
from django.contrib.contenttypes import fields as generic
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField

from aa_stripe.exceptions import StripeMethodNotAllowed

USER_MODEL = getattr(settings, "STRIPE_USER_MODEL", settings.AUTH_USER_MODEL)


class StripeBasicModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    stripe_response = JSONField()

    class Meta:
        abstract = True


class StripeCustomer(StripeBasicModel):
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name='stripe_customers')
    stripe_js_response = JSONField()
    stripe_customer_id = models.CharField(max_length=255, db_index=True)
    is_active = models.BooleanField(default=True)
    is_created_at_stripe = models.BooleanField(default=False)

    def create_at_stripe(self):
        if self.is_created_at_stripe:
            raise StripeMethodNotAllowed()

        stripe.api_key = settings.STRIPE_API_KEY
        customer = stripe.Customer.create(
            source=self.stripe_js_response["id"],
            description="{user} id: {user.id}".format(user=self.user)
        )
        self.stripe_customer_id = customer["id"]
        self.stripe_response = customer
        self.is_created_at_stripe = True
        self.save()
        return self

    @classmethod
    def get_latest_active_customer_for_user(cls, user):
        """Returns last active stripe customer for user"""
        customer = cls.objects.filter(user_id=user.id, is_active=True).last()
        return customer

    class Meta:
        ordering = ["id"]


class StripeCoupon(StripeBasicModel):
    DURATION_FOREVER = "forever"
    DURATION_ONCE = "once"
    DURATION_REPEATING = "repeating"
    DURATION_CHOICES = (
        (DURATION_FOREVER, DURATION_FOREVER),
        (DURATION_ONCE, DURATION_ONCE),
        (DURATION_REPEATING, DURATION_REPEATING)
    )

    CURRENCY_CHOICES = (
        ("USD", "USD"), ("AED", "AED"), ("AFN", "AFN"), ("ALL", "ALL"), ("AMD", "AMD"), ("ANG", "ANG"), ("AOA", "AOA"),
        ("ARS", "ARS"), ("AUD", "AUD"), ("AWG", "AWG"), ("AZN", "AZN"), ("BAM", "BAM"), ("BBD", "BBD"), ("BDT", "BDT"),
        ("BGN", "BGN"), ("BIF", "BIF"), ("BMD", "BMD"), ("BND", "BND"), ("BOB", "BOB"), ("BRL", "BRL"), ("BSD", "BSD"),
        ("BWP", "BWP"), ("BZD", "BZD"), ("CAD", "CAD"), ("CDF", "CDF"), ("CHF", "CHF"), ("CLP", "CLP"), ("CNY", "CNY"),
        ("COP", "COP"), ("CRC", "CRC"), ("CVE", "CVE"), ("CZK", "CZK"), ("DJF", "DJF"), ("DKK", "DKK"), ("DOP", "DOP"),
        ("DZD", "DZD"), ("EGP", "EGP"), ("ETB", "ETB"), ("EUR", "EUR"), ("FJD", "FJD"), ("FKP", "FKP"), ("GBP", "GBP"),
        ("GEL", "GEL"), ("GIP", "GIP"), ("GMD", "GMD"), ("GNF", "GNF"), ("GTQ", "GTQ"), ("GYD", "GYD"), ("HKD", "HKD"),
        ("HNL", "HNL"), ("HRK", "HRK"), ("HTG", "HTG"), ("HUF", "HUF"), ("IDR", "IDR"), ("ILS", "ILS"), ("INR", "INR"),
        ("ISK", "ISK"), ("JMD", "JMD"), ("JPY", "JPY"), ("KES", "KES"), ("KGS", "KGS"), ("KHR", "KHR"), ("KMF", "KMF"),
        ("KRW", "KRW"), ("KYD", "KYD"), ("KZT", "KZT"), ("LAK", "LAK"), ("LBP", "LBP"), ("LKR", "LKR"), ("LRD", "LRD"),
        ("LSL", "LSL"), ("MAD", "MAD"), ("MDL", "MDL"), ("MGA", "MGA"), ("MKD", "MKD"), ("MMK", "MMK"), ("MNT", "MNT"),
        ("MOP", "MOP"), ("MRO", "MRO"), ("MUR", "MUR"), ("MVR", "MVR"), ("MWK", "MWK"), ("MXN", "MXN"), ("MYR", "MYR"),
        ("MZN", "MZN"), ("NAD", "NAD"), ("NGN", "NGN"), ("NIO", "NIO"), ("NOK", "NOK"), ("NPR", "NPR"), ("NZD", "NZD"),
        ("PAB", "PAB"), ("PEN", "PEN"), ("PGK", "PGK"), ("PHP", "PHP"), ("PKR", "PKR"), ("PLN", "PLN"), ("PYG", "PYG"),
        ("QAR", "QAR"), ("RON", "RON"), ("RSD", "RSD"), ("RUB", "RUB"), ("RWF", "RWF"), ("SAR", "SAR"), ("SBD", "SBD"),
        ("SCR", "SCR"), ("SEK", "SEK"), ("SGD", "SGD"), ("SHP", "SHP"), ("SLL", "SLL"), ("SOS", "SOS"), ("SRD", "SRD"),
        ("STD", "STD"), ("SVC", "SVC"), ("SZL", "SZL"), ("THB", "THB"), ("TJS", "TJS"), ("TOP", "TOP"), ("TRY", "TRY"),
        ("TTD", "TTD"), ("TWD", "TWD"), ("TZS", "TZS"), ("UAH", "UAH"), ("UGX", "UGX"), ("UYU", "UYU"), ("UZS", "UZS"),
        ("VND", "VND"), ("VUV", "VUV"), ("WST", "WST"), ("XAF", "XAF"), ("XCD", "XCD"), ("XOF", "XOF"), ("XPF", "XPF"),
        ("YER", "YER"), ("ZAR", "ZAR"), ("ZMW", "ZMW")
    )

    coupon_id = models.CharField(max_length=255, help_text=_("Identifier for the coupon"))
    amount_off = models.PositiveIntegerField(
        blank=True, null=True, help_text=_("Amount (in the currency specified) that will be taken off the subtotal of "
                                           "any invoices for this customer."))
    currency = models.CharField(
        max_length=3, default="USD", choices=CURRENCY_CHOICES,
        help_text=_("If amount_off has been set, the three-letter ISO code for the currency of the amount to take "
                    "off."))
    duration = models.CharField(
        max_length=255, choices=DURATION_CHOICES,
        help_text=_("Describes how long a customer who applies this coupon will get the discount."))
    duration_in_months = models.PositiveIntegerField(
        blank=True, null=True, help_text=_("If duration is repeating, the number of months the coupon applies. "
                                           "Null if coupon duration is forever or once."))
    livemode = models.BooleanField(
        default=False, help_text=_("Flag indicating whether the object exists in live mode or test mode."))
    max_redemptions = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Maximum number of times this coupon can be redeemed, in total, before it is no longer valid."))
    metadata = JSONField(help_text=_("Set of key/value pairs that you can attach to an object. It can be useful for "
                                     "storing additional information about the object in a structured format."))
    percent_off = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Percent that will be taken off the subtotal of any invoicesfor this customer for the duration of "
                    "the coupon. For example, a coupon with percent_off of 50 will make a $100 invoice $50 instead."))
    redeem_by = models.DateTimeField(
        blank=True, null=True, help_text=_("Date after which the coupon can no longer be redeemed."))
    times_redeemed = models.PositiveIntegerField(
        default=0, help_text=_("Number of times this coupon has been applied to a customer."))
    valid = models.BooleanField(
        default=False,
        help_text=_("Taking account of the above properties, whether this coupon can still be applied to a customer."))
    created = models.DateTimeField()
    is_deleted = models.BooleanField(default=False)
    is_created_at_stripe = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super(StripeCoupon, self).__init__(*args, **kwargs)
        self._previous_is_deleted = self.is_deleted

    def __str__(self):
        return self.coupon_id

    def save(self, *args, **kwargs):
        stripe.api_key = settings.STRIPE_API_KEY
        if self._previous_is_deleted != self.is_deleted and self.is_deleted:
            try:
                coupon = stripe.Coupon.retrieve(self.coupon_id)
                coupon.delete()
            except stripe.error.InvalidRequestError:
                # means that the coupon has already been removed from stripe
                pass

            return super(StripeCoupon, self).save(*args, **kwargs)

        if self.pk:
            try:
                coupon = stripe.Coupon.retrieve(self.coupon_id)
                coupon.metadata = self.metadata
                coupon.save()

                # update all fields in the local object in case someone tried to change them
                readonly_fields = [
                    "amount_off", "currency", "duration", "duration_in_months", "livemode", "max_redemptions",
                    "percent_off", "redeem_by", "times_redeemed", "valid",
                ]
                for field in readonly_fields:
                    setattr(self, field, getattr(coupon, field))
            except stripe.error.InvalidRequestError:
                self.is_deleted = True
        else:
            self.stripe_response = stripe.Coupon.create(
                id=self.coupon_id,
                duration=self.duration,
                amount_off=self.amount_off,
                currency=self.currency,
                duration_in_months=self.duration_in_months,
                max_redemptions=self.max_redemptions,
                metadata=self.metadata,
                percent_off=self.percent_off,
                redeem_by=self.redeem_by
            )
            self.created = timezone.make_aware(datetime.fromtimestamp(self.stripe_response["created"]))

            # stripe will generate coupon_id if none was specified in the request
            if not self.coupon_id:
                self.coupon_id = self.stripe_response["id"]

        # for future
        self.is_created_at_stripe = True
        return super(StripeCoupon, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()
        return 0, {self._meta.label: 0}


class StripeCharge(StripeBasicModel):
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name='stripe_charges')
    customer = models.ForeignKey(StripeCustomer, on_delete=models.SET_NULL, null=True)
    amount = models.IntegerField(null=True, help_text=_("in cents"))
    is_charged = models.BooleanField(default=False)
    stripe_charge_id = models.CharField(max_length=255, blank=True, db_index=True)
    description = models.CharField(max_length=255, help_text=_("Description sent to Stripe"))
    comment = models.CharField(max_length=255, help_text=_("Comment for internal information"))
    content_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, db_index=True)
    source = generic.GenericForeignKey('content_type', 'object_id')

    def charge(self):
        if self.is_charged:
            raise StripeMethodNotAllowed("Already charged.")

        stripe.api_key = settings.STRIPE_API_KEY
        customer = StripeCustomer.get_latest_active_customer_for_user(self.user)
        if customer:
            try:
                stripe_charge = stripe.Charge.create(
                    amount=self.amount,
                    currency="usd",
                    customer=customer.stripe_customer_id,
                    description=self.description
                )
            except stripe.error.StripeError:
                self.is_charged = False
                self.save()
                raise

            self.stripe_charge_id = stripe_charge["id"]
            self.stripe_response = stripe_charge
            self.is_charged = True
            self.save()
            return stripe_charge


class StripeSubscriptionPlan(StripeBasicModel):
    INTERVAL_DAY = "day"
    INTERVAL_WEEK = "week"
    INTERVAL_MONTH = "month"
    INTERVAL_YEAR = "year"

    INTERVAL_CHOICES = (
        (INTERVAL_DAY, INTERVAL_DAY),
        (INTERVAL_WEEK, INTERVAL_WEEK),
        (INTERVAL_MONTH, INTERVAL_MONTH),
        (INTERVAL_YEAR, INTERVAL_YEAR),
    )

    is_created_at_stripe = models.BooleanField(default=False)
    source = JSONField(blank=True, help_text=_("Source of the plan, ie: {\"prescription\": 1}"))
    amount = models.IntegerField(help_text=_("In cents. More: https://stripe.com/docs/api#create_plan-amount"))
    currency = models.CharField(
        max_length=3, help_text=_("3 letter ISO code, default USD, https://stripe.com/docs/api#create_plan-currency"),
        default="USD")
    name = models.CharField(
        max_length=255, help_text=_("Name of the plan, to be displayed on invoices and in the web interface."))
    interval = models.CharField(
        max_length=10, help_text=_("Specifies billing frequency. Either day, week, month or year."),
        choices=INTERVAL_CHOICES)
    interval_count = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    metadata = JSONField(help_text=_("A set of key/value pairs that you can attach to a plan object. It can be useful"
                         " for storing additional information about the plan in a structured format."))
    statement_descriptor = models.CharField(
        max_length=22, help_text=_("An arbitrary string to be displayed on your customer’s credit card statement."),
        blank=True)
    trial_period_days = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text=_("Specifies a trial period in (an integer number of) days. If you include a trial period,"
                    " the customer won’t be billed for the first time until the trial period ends. If the customer "
                    "cancels before the trial period is over, she’ll never be billed at all."))

    def create_at_stripe(self):
        if self.is_created_at_stripe:
            raise StripeMethodNotAllowed()

        stripe.api_key = settings.STRIPE_API_KEY
        try:
            plan = stripe.Plan.create(
                id=self.id,
                amount=self.amount,
                currency=self.currency,
                interval=self.interval,
                interval_count=self.interval_count,
                name=self.name,
                metadata=self.metadata,
                statement_descriptor=self.statement_descriptor,
                trial_period_days=self.trial_period_days
            )
        except stripe.error.StripeError:
            self.is_created_at_stripe = False
            self.save()
            raise

        self.stripe_response = plan
        self.is_created_at_stripe = True
        self.save()
        return plan


class StripeSubscription(StripeBasicModel):
    STATUS_TRIAL = "trialing"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELED = "canceled"
    STATUS_UNPAID = "unpaid"

    STATUS_CHOICES = (
        (STATUS_TRIAL, STATUS_TRIAL),
        (STATUS_ACTIVE, STATUS_ACTIVE),
        (STATUS_PAST_DUE, STATUS_PAST_DUE),
        (STATUS_CANCELED, STATUS_CANCELED),
        (STATUS_UNPAID, STATUS_UNPAID),
    )
    stripe_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)
    is_created_at_stripe = models.BooleanField(default=False)
    plan = models.ForeignKey(StripeSubscriptionPlan, on_delete=models.CASCADE)
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name="stripe_subscriptions")
    customer = models.ForeignKey(StripeCustomer, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=255, help_text="https://stripe.com/docs/api/python#subscription_object-status, "
        "empty if not sent created at stripe", blank=True, choices=STATUS_CHOICES)
    metadata = JSONField(help_text="https://stripe.com/docs/api/python#create_subscription-metadata")
    tax_percent = models.DecimalField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], decimal_places=2, max_digits=3,
        help_text="https://stripe.com/docs/api/python#subscription_object-tax_percent")
    # application_fee_percent = models.DecimalField(
    #     default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], decimal_places=2, max_digits=3,
    #     help_text="https://stripe.com/docs/api/python#create_subscription-application_fee_percent")
    coupon = models.ForeignKey(
        StripeCoupon, blank=True, null=True, on_delete=models.SET_NULL,
        help_text="https://stripe.com/docs/api/python#create_subscription-coupon")
    end_date = models.DateField(null=True, blank=True, db_index=True)
    canceled_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def create_at_stripe(self):
        if self.is_created_at_stripe:
            raise StripeMethodNotAllowed()

        stripe.api_key = settings.STRIPE_API_KEY
        customer = StripeCustomer.get_latest_active_customer_for_user(self.user)
        if customer:
            data = {
                "customer": customer.stripe_customer_id,
                "plan": self.plan.id,
                "metadata": self.metadata,
                "tax_percent": self.tax_percent,
            }
            if self.coupon:
                data["coupon"] = self.coupon.coupon_id

            try:
                subscription = stripe.Subscription.create(**data)
            except stripe.error.StripeError:
                self.is_created_at_stripe = False
                self.save()
                raise

            self.set_stripe_data(subscription)
            return subscription

    def set_stripe_data(self, subscription):
        self.stripe_subscription_id = subscription["id"]
        # for some reason it doesnt work with subscription only
        self.stripe_response = json.loads(str(subscription))
        self.is_created_at_stripe = True
        self.status = subscription["status"]
        self.save()

    def refresh_from_stripe(self):
        stripe.api_key = settings.STRIPE_API_KEY
        subscription = stripe.Subscription.retrieve(self.stripe_subscription_id)
        self.set_stripe_data(subscription)
        return subscription

    def _stripe_cancel(self):
        subscription = self.refresh_from_stripe()
        if subscription["status"] != "canceled":
            return stripe.Subscription.delete(subscription)

    def cancel(self):
        sub = self._stripe_cancel()
        if sub and sub["status"] == "canceled":
            self.canceled_at = timezone.now()
            self.status = self.STATUS_CANCELED
            self.save()

    @classmethod
    def get_subcriptions_for_cancel(cls):
        today = timezone.localtime(timezone.now()).date()
        return cls.objects.filter(
            end_date__lte=today, status=cls.STATUS_ACTIVE)

    @classmethod
    def end_subscriptions(cls):
        # do not use in cron - one broken subscription will kill all.
        # instead please use end_subscriptions.py script.
        for subscription in cls.get_subcriptions_for_cancel():
            subscription.cancel()
            sleep(0.25)  # 4 requests per second tops


class StripeWebhook(models.Model):
    id = models.CharField(primary_key=True, max_length=255)  # id from stripe. This will prevent subsequent calls.
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_parsed = models.BooleanField(default=False)
    raw_data = JSONField()
