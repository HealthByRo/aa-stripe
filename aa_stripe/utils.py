from aa_stripe.models import StripeCustomer
from django.contrib import admin


def get_latest_active_customer_for_user(user):
    """Returns last active stripe customer for user"""
    customer = StripeCustomer.objects.filter(user_id=user.id, is_active=True).last()
    return customer


class ReadOnlyBase(object):
    extra = 0
    extra_fields = []

    def get_readonly_fields(self, request, obj=None):
        from itertools import chain
        field_names = list(set(chain.from_iterable(
            (field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
            for field in self.model._meta.get_fields()
            # For complete backwards compatibility, you may want to exclude
            # GenericForeignKey from the results.
            # if not (field.many_to_one and field.related_model is None)
            # remove all related fields because it causes admin to break
            if not field.one_to_many and not field.one_to_one and not field.auto_created
        )))
        fields = list(self.extra_fields)
        for field in field_names:
            if not hasattr(self, "editable_fields") or (field not in self.editable_fields):
                fields.append(field)
        return fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class ReadOnly(ReadOnlyBase, admin.ModelAdmin):
    editable_fields = []
