from datetime import datetime

from django.db import models
from django.utils import timezone


def timestamp_to_timezone_aware_date(timestamp):
    return timezone.make_aware(datetime.fromtimestamp(timestamp))


class SafeDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class SafeDeleteQuerySet(models.query.QuerySet):
    def delete(self):
        deleted_counter = 0
        for obj in self:
            obj.delete()
            deleted_counter = deleted_counter + 1

        return deleted_counter, {self.model._meta.label: deleted_counter}


class SafeDeleteManager(models.Manager):
    def all_with_deleted(self):
        return SafeDeleteQuerySet(self.model, using=self._db)

    def deleted(self):
        return self.all_with_deleted().filter(is_deleted=True)

    def get_queryset(self):
        return self.all_with_deleted().filter(is_deleted=False)
