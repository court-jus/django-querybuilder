# -*- coding: utf-8 -*-

from django.db                  import models

class QbuilderQuery(models.Model):
    """
    Une "requête" QBuilder sauvegardée en BDD
    """
    
    name  = models.TextField()
    data  = models.TextField()
    
    def __unicode__(self):
        return self.name
    

class TestModelA(models.Model):
    truc = models.TextField()

class TestModelB(models.Model):
    machin = models.TextField()
    date = models.DateTimeField()

class TestModelC(models.Model):
    a = models.ForeignKey(TestModelA)
    b = models.ForeignKey(TestModelB)
    critere = models.IntegerField()
