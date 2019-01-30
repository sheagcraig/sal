from django.db import models
from server.models import *


class Application(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(db_index=True, max_length=255)
    bundleid = models.CharField(db_index=True, max_length=255)
    bundlename = models.CharField(db_index=True, max_length=255)

    class Meta:
        ordering = ['name']
        unique_together = (('name', 'bundleid', 'bundlename'))

    def __str__(self):
        return self.name


class Inventory(models.Model):
    id = models.BigAutoField(primary_key=True)
    machine = models.OneToOneField(Machine, on_delete=models.CASCADE)
    datestamp = models.DateTimeField(auto_now=True)
    sha256hash = models.CharField(max_length=64)

    class Meta:
        ordering = ['datestamp']


class InventoryItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    version = models.CharField(db_index=True, max_length=64)
    path = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['application', '-version']
