# -*- coding: utf-8 -*-
from elixir import *
from querybuilder.qbuilder import sql_connection_string, QBEntity
metadata.bind = sql_connection_string
metadata.bind.echo = True

class TestModelA(Entity, QBEntity):
    using_options(tablename = 'querybuilder_testmodela')
    
    pk = Field(Integer, primary_key = True, colname = 'id')
    truc = Field(String)
    TestModelC = OneToMany('TestModelC')
    
    qbtitle = u'Truc A'
    qbforeigns = {
        'TestModelC': [],
        'TestModelB': ['TestModelC',],
        }
    qbfilters = {
        'truc' : ('=', 'IN', '!='),
        }
    qbgroup_by = {
        'truc' : ('Truc', 'truc', False),
        }
class TestModelB(Entity, QBEntity):
    using_options(tablename = 'querybuilder_testmodelb')
    
    pk = Field(Integer, primary_key = True, colname = 'id')
    machin = Field(String)
    date = Field(DateTime)
    TestModelC = OneToMany('TestModelC')

    qbtitle = u'Truc B'
    qbforeigns = {
        'TestModelC': [],
        'TestModelA': ['TestModelC',],
        }
    qbfilters = {
        'machin' : ('=', 'IN', '!='),
        'date'   : ('date_gt', 'date_lt'),
        }
    qbgroup_by = {
        'machin' : ('Machin', 'machin', False),
        'date_hour'  : ('Date (heure)', ('extract', ('hour', 'date'), u"Heure"), False),
        'date_day'   : ('Date (jour)', ('extract', ('day', 'date'), u"Jour"), False),
        'date_month' : ('Date (mois)', ('extract', ('month', 'date'), u"Mois"), False),
        'date_year'  : (u'Date (année)', ('extract', ('year', 'date'), u"Année"), False),
        }
class TestModelC(Entity, QBEntity):
    using_options(tablename = 'querybuilder_testmodelc')
    
    pk = Field(Integer, primary_key = True, colname = 'id')
    critere = Field(Integer)
    
    TestModelA = ManyToOne('TestModelA', colname = 'a_id')
    TestModelB = ManyToOne('TestModelB', colname = 'b_id')

    qbtitle = u'Truc C'
    qbforeigns = {
        'TestModelA': [],
        'TestModelB': [],
        }
    qbfilters = {
        'critere' : ('>', '<', '=', '!='),
        }
    qbgroup_by = {
        'critere' : (u'Critère', 'critere', False),
        }

QBSelectables = [TestModelA, TestModelB, TestModelC]
QBModels = [TestModelA, TestModelB, TestModelC]

def get_model_by_name(model_name):
    if not model_name:
        return None
    for model in QBModels:
        if model.__name__ == model_name:
            return model
    return None
    
setup_all()
