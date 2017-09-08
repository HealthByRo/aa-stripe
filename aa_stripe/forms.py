from django import forms
from django.utils.translation import ugettext_lazy as _

from aa_stripe.models import StripeCoupon


class StripeCouponForm(forms.ModelForm):
    def clean_currency(self):
        amount_off = self.cleaned_data.get("amount_off")
        currency = self.cleaned_data.get("currency")
        if amount_off and not currency:
            raise forms.ValidationError(_("Currency is required when amount_off is set"))

        return currency

    def clean_coupon_id(self):
        coupon_id = self.cleaned_data.get("coupon_id")
        if coupon_id:
            if StripeCoupon.objects.filter(coupon_id=coupon_id).exists():
                raise forms.ValidationError(_("Coupon with this id already exists"))

        return coupon_id

    def clean_duration_in_months(self):
        duration = self.cleaned_data.get("duration")
        duration_in_months = self.cleaned_data.get("duration_in_months")
        if duration == StripeCoupon.DURATION_REPEATING and not duration_in_months:
            raise forms.ValidationError(_("Cannot be empty with when duration is set to repeating"))

        if duration_in_months and duration != StripeCoupon.DURATION_REPEATING:
            raise forms.ValidationError(_("Cannot be set when duration is not set to repeating"))

        return duration_in_months

    def clean(self):
        if self.instance.pk:
            return self.cleaned_data

        discount_list = [self.cleaned_data.get("amount_off"), self.cleaned_data.get("percent_off")]
        if not any(discount_list) or all(discount_list):
            raise forms.ValidationError(_("Coupon must specify amount_off or percent_off"))

        return self.cleaned_data

    class Meta:
        model = StripeCoupon
        fields = [
            "coupon_id", "amount_off", "currency", "duration", "duration_in_months", "livemode", "max_redemptions",
            "metadata", "percent_off", "redeem_by", "times_redeemed", "valid", "is_deleted"
        ]
