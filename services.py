# -*- coding: utf-8 -*-
from django.template.loader             import render_to_string
from django.template                import RequestContext
from django.utils import simplejson as json
from django.core import serializers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func, extract
from django.http                        import HttpResponse, HttpResponseBadRequest

from functools import wraps
import datetime, time
import logging
logger = logging.getLogger("querybuilder")

def cp_service_wrapper(data_required = False, requested_fields = [], on_data_missing = u"Données manquantes"):
    def decorator(fonction):
        @wraps(fonction)
        def f(request, *args, **kwargs):
            if request.method != 'POST':
                return HttpResponseBadRequest(u"Please use POST")
            data = {}
            if 'requete' in request.POST:
                data = json.loads(request.POST['requete'])
            if not data and data_required:
                return HttpResponse(on_data_missing)
            if requested_fields:
                for requested_field in requested_fields:
                    if not requested_field in data:
                        logger.debug(u"Appel à service sans champs requis. %s (%s) : %s" % (on_data_missing, requested_field, data,))
                        return HttpResponse("%s (%s)" % (on_data_missing, requested_field,))
            request.qb_data = data
            fonction_result = None
            try: 
                fonction_result = fonction(request, *args, **kwargs)
                logger.debug("%s", fonction_result)
            except:
                import traceback
                logger.critical(traceback.format_exc())
                return HttpResponseBadRequest(fonction_result)
            else:
                return HttpResponse(fonction_result)
        return f
    return decorator

def filtering_type2display(type):
    if type.startswith('date_'):
        return {'date_gt' : '&gt;', 'date_lt' : '&lt;', 'date_gte' : '&gt;=', 'date_lte' : '&lt;='}[type]
    return type

@cp_service_wrapper(data_required = True, requested_fields = ['whattodo',], on_data_missing = u"Erreur, aucun type de sélection choisi")
def whattodochoose(request):
    from querybuilder.qbmodels import QBSelectables#, QBEvents
    from querybuilder.models import QbuilderQuery
    whattodo = request.qb_data.get('whattodo')
    result = {}
    if whattodo == 'count':
        result['selectables'] = [(qbs.__name__,qbs.qbtitle) for qbs in QBSelectables]
        result['display_types'] = [('table',u'Tableau'),('piechart',u'Diagramme circulaire'),('barchart',u'Histogramme'),('gauge',u'Gauge')]
    elif whattodo == 'evolution':
        result['selectables'] = [(qbs.__name__, qbs.qbtitle) for qbs in QBSelectables if qbs().available_date_criteria()]
        result['display_types'] = [('table',u'Tableau'),('linechart',u'Ligne brisée'),]
    #~ elif whattodo in ('event_delta', 'event_delta_evolution'):
        #~ evenements = Evenement.objects.values_list('pk','nom')
        #~ result['event_choices'] = [(e[0],e[1] and e[1] or e[0]) for e in evenements]
        #~ result['display_types'] = [('table',u'Tableau'),]
        #~ if whattodo == 'event_delta_evolution':
            #~ result['display_types'].append(('linechart',u'Ligne brisée'))
    elif whattodo == 'recover_existing':
        result['query_choices'] = list(QbuilderQuery.objects.all().values_list('pk','name'))
    result['extra_choices_possible'] = [
        {'code' : 'borne', 'label': 'Ajouter une borne', 'possibilities' : [
            {'code' : 'min', 'label': 'Min',},
            {'code' : 'max', 'label': 'Max',},
            ]},
        {'code' : 'bla',   'label': 'Hello world',       'possibilities' : [
            {'code' : 'plop', 'label': 'Plop',},
            {'code' : 'plaf', 'label': 'Plaf',},
            ]},
        ]
    return json.dumps(result)

@cp_service_wrapper(data_required = True, requested_fields = ['whattodo','starting_event_choice',], on_data_missing = u"Erreur, aucun type de sélection choisi ou aucun évènement de départ")
def starting_event_choose(request):
    from querybuilder.models import Evenement
    result = {}
    evenements = Evenement.objects.\
        filter(
            end_in_vstats_tat__start_evt__pk = request.qb_data.get('starting_event_choice', None),
            end_in_vstats_tat__temps_reel__gt = datetime.timedelta(days = 0)).\
        distinct().\
        values_list('pk', 'nom')
    #~ evenements = Evenement.objects.exclude(pk = request.qb_data.get('starting_event_choice', None)).values_list('pk','nom')
    result['event_choices'] = [(e[0],e[1] and e[1] or e[0]) for e in evenements]
    return json.dumps(result)


def get_possible_filters(model):
    from querybuilder.qbmodels import get_model_by_name
    result = []
    if not model:
        return result
    if model().available_filters():
        result.append({
            'title' : model.qbtitle,
            'model_name' : model.__name__,
            'filters' : [{'field_name' : k, 'possible_types' : [(type, filtering_type2display(type)) for type in v]} for k, v in model().available_filters().items()]
            })
    for foreign_model in model().available_foreigns():
        foreign_model = get_model_by_name(foreign_model)
        if foreign_model().available_filters():
            result.append({
                'title' : foreign_model.qbtitle,
                'model_name' : foreign_model.__name__,
                'filters' : [{'field_name' : k, 'possible_types' : [(type, filtering_type2display(type)) for type in v]} for k, v in foreign_model().available_filters().items()]
                })
    return result

def get_possible_group_by(model):
    from querybuilder.qbmodels import get_model_by_name
    result = []
    if not model:
        return result
    if model().available_group():
        result.append({
            'title' : model.qbtitle,
            'model_name': model.__name__,
            'fields' : [{'title' : k, 'field' : v} for k, v in model().available_group().items()]
            })
    for foreign_model in model().available_foreigns():
        foreign_model = get_model_by_name(foreign_model)
        if foreign_model().available_group():
            result.append({
                'title' : foreign_model.qbtitle,
                'model_name': foreign_model.__name__,
                'fields' : [{'title' : k, 'field' : v} for k, v in foreign_model().available_group().items()]
                })
    return result
    
@cp_service_wrapper(data_required = True, requested_fields = ['model',], on_data_missing = u"Erreur, aucun modèle sélectionné")
def modelchoose(request):
    from querybuilder.qbmodels import QBSelectables, get_model_by_name
    model = get_model_by_name(request.qb_data.get('model', None))
    result = {}
    if model:
        result = {
            'possible_group_by' : get_possible_group_by(model),
            'possible_filters'  : get_possible_filters(model),
            }
    return json.dumps(result)

@cp_service_wrapper(data_required = True, requested_fields = ['whattodo', 'starting_event_choice', 'ending_event_choice',])
def ending_event_choose(request):
    from qbuilder import Evenement
    result = {
        'possible_group_by' : get_possible_group_by(Evenement),
        'possible_filters'  : get_possible_filters(Evenement),
        }
    return json.dumps(result)
    
@cp_service_wrapper(data_required = True, requested_fields = ['model','filtering_model','filtering_field','filtering_type','filter_id',], on_data_missing = u"Erreur, aucun modèle ou aucun filtre sélectionné")
def filteradd(request):
    from querybuilder.qbmodels import QBSelectables, get_model_by_name
    filtering_model = get_model_by_name(request.qb_data.get('filtering_model', None))
    result = {}
    if filtering_model:
        filtering_model_name=filtering_model.__name__
        filtering_model=filtering_model()
        filtering_type = request.qb_data.get('filtering_type', None)
        filtering_type_display = filtering_type
        filtering_type_type    = 'text'
        if filtering_type.startswith('date_'):
            filtering_type_display = filtering_type2display(filtering_type)
            filtering_type_type = 'date'
        result = {
            'filter_html':render_to_string("querybuilder/qbuilder/filter.html", {
                'filtering_model': filtering_model,
                'filtering_model_name': filtering_model_name,
                'filtering_field': request.qb_data.get('filtering_field', None),
                'filtering_type': filtering_type,
                'filtering_type_display': filtering_type_display,
                'filtering_type_type': filtering_type_type,
                'filter_id': request.qb_data.get('filter_id', None),
                }, context_instance = RequestContext(request))
            }
    return json.dumps(result)

@cp_service_wrapper(data_required = True, requested_fields = ['model','grouping_model','grouping_field','grouping_id',], on_data_missing = u"Erreur, aucun modèle ou aucun filtre sélectionné")
def groupingadd(request):
    from querybuilder.qbmodels import QBSelectables, get_model_by_name
    grouping_model = get_model_by_name(request.qb_data.get('grouping_model', None))
    result = {}
    if grouping_model:
        grouping_model_name=grouping_model.__name__
        grouping_model=grouping_model()
        result = {
            'grouping_html':render_to_string("querybuilder/qbuilder/grouping.html", {
                'grouping_model': grouping_model,
                'grouping_model_name': grouping_model_name,
                'grouping_field': request.qb_data.get('grouping_field', None),
                'grouping_id': request.qb_data.get('grouping_id', None),
                }, context_instance = RequestContext(request))
            }
    return json.dumps(result)

@cp_service_wrapper(data_required = True, requested_fields = ['whattodo', 'extra_id', 'extra_type', 'extra_choice',])
def extrachoiceadd(request):
    logger.debug("extra choice %s", request.qb_data)
    template_context = request.qb_data
    result = {}
    result = {
        'extra_choice_html' : render_to_string("querybuilder/qbuilder/extrachoice.html", template_context, context_instance = RequestContext(request))
        }
    return json.dumps(result)
    
@cp_service_wrapper(data_required = True, on_data_missing = u"Erreur, données manquantes")
def test_query(request):
    # TODO : laurent dit de ne pas utiliser strftime et strptime de datetime car elles ne marchent pas très loin dans le futur ni dans le passé
    # TODO : rajouter les points à zéro quand pas de valeur
    from querybuilder.qbmodels import QBSelectables, get_model_by_name
    from querybuilder.models import QbuilderQuery
    data = request.qb_data
    if data.get('whattodo', 'count') == 'recover_existing':
        existing_query_pk = data.get('chosen_query', None)
        if existing_query_pk:
            try:
                existing_query = QbuilderQuery.objects.get(pk = existing_query_pk)
            except QbuilderQuery.DoesNotExist:
                pass
            else:
                data = json.loads(existing_query.data)
    if data.get('whattodo', 'count') in ('event_delta', 'event_delta_evolution'):
        from qbuilder import TatQueryBuilder as QueryBuilder
    else:
        from qbuilder import QueryBuilder
    class ArretTraitement(Exception):
        pass
    result = {}
    qb = QueryBuilder(data)
    query = qb.build_query()
    all_data = resulting_keys = None
    if query:
        result['sql'] = str(query)
        all_data = qb.grab_data()
        resulting_keys = qb.get_data_keys()
    if all_data and resulting_keys:
        result['data'] = render_to_string("querybuilder/qbuilder/tableau.html", {'result':all_data, 'keys': resulting_keys}, context_instance = RequestContext(request))
        display_type = data.get('display_type_choice', 'table')
        if display_type == 'table':
            result['grid_layout'] = qb.generate_table()
        elif display_type == 'piechart':
            result['pie_layout']  = qb.generate_piechart()
        elif display_type == 'barchart':
            result['bar_layout']  = qb.generate_barchart()
        elif display_type == 'linechart':
            result['line_layout'] = qb.generate_linechart()
        elif display_type == 'gauge':
            result['gauge_layout'] = qb.generate_gauge()
    return json.dumps(result)

@cp_service_wrapper(data_required = True, requested_fields = ['name',])
def save_query(request):
    from querybuilder.models import QbuilderQuery
    data = request.qb_data
    name = data.pop('name', 'anonyme')
    try:
        qbq = QbuilderQuery.objects.create(name = name, data = json.dumps(data))#, owner = request.user)
        return json.dumps({
            'pk' : qbq.pk,
            'name' : name,
            'created' : True,
            })
    except:
        import traceback
        logger.error(traceback.format_exc())
        return json.dumps({
            'pk' : None,
            'name' : name,
            'created' : False,
            'error' : traceback.format_exc(),
            })
    return json.dumps({})
