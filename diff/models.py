from django.db import models
from django.utils.translation import ugettext_lazy as _


# Create your models here.


class Prototype(models.Model):
    string_one = models.TextField(_("ONE"), blank=True, null=True)
    String_two = models.TextField(_("TWO"), blank=True, null=True)
    string_diff = models.TextField(_("Three"), blank=True, null=True)
    changes = models.CharField(_("changes"), max_length=200, blank=True, null=True)

    def __str__(self):
        return self.string_one
