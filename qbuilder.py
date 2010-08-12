# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, aliased
from sqlalchemy.sql import func, extract
from sqlalchemy.sql.expression import cast, case, literal_column
from sqlalchemy.types import Interval
sql_connection_string = "postgresql+psycopg2://querybuilder:querybuilder@192.168.1.15/test_querybuilder"

import datetime, time
import logging
import traceback
from querybuilder.models import QbuilderQuery
from django.utils import simplejson as json
logger = logging.getLogger("querybuilder")

def interval_stddev(field):
    """
    Renvoie la fonction SQL de calcul de l'écart type pour un champ de type interval:
    
    justify_hours(
        textcat(
            text(
                stddev(
                    extract(epoch from temps_reel)
                    )
                ),
            text(' seconds')
            )::interval
        )
    
    """
    return func.justify_hours(
            cast(
                func.textcat(
                    func.text(
                        func.stddev(
                            extract('epoch', cast(field, Interval()))
                            )
                        ),
                    func.text(' seconds')
                    ),
                    Interval()
                )
        )

class QBEntity(object):
    qbtitle = u"Un modèle"
    qbdate_criteria = None
    qbfilters = {}
    qbgroup_by = {}
    qbforeigns = {}
    def available_foreigns_old(self, seen_models = []):
        foreigns = self.qbforeigns.copy()
        
        
        
        for foreignmodel, foreignpath in foreigns.items():
            if foreignmodel not in seen_models:
                seen_models.append(foreignmodel)
                his_foreigns = get_model_by_name(foreignmodel)().available_foreigns(seen_models)
                for his_foreignmodel, his_foreignpath in his_foreigns.items():
                    if his_foreignmodel and his_foreignmodel not in foreigns.keys():
                        foreigns[his_foreignmodel] = foreignpath[:].extend(his_foreignpath)
        foreign_models = {}
        for foreign_name, path in foreigns.items():
            if foreign_name:
                foreign_models[get_model_by_name(foreign_name)] = path
        return foreign_models
    
    def available_foreigns(self, seen_models = None):
        from querybuilder.qbmodels import get_model_by_name
        if not seen_models:
            seen_models = [self.__class__.__name__,]
        my_foreign_models = {}
        for key, value in self.qbforeigns.items():
            if key not in seen_models:
                my_foreign_models[key] = value
                
        for foreignmodel, foreignpath in my_foreign_models.items():
            if foreignmodel not in seen_models:
                seen_models.append(foreignmodel)
                his_foreigns = get_model_by_name(foreignmodel)().available_foreigns(seen_models)
                for his_foreignmodel, his_foreignpath in his_foreigns.items():
                    if his_foreignmodel not in my_foreign_models.keys():
                        my_foreign_models[his_foreignmodel] = foreignpath[:].extend(his_foreignpath)
        
        foreign_models = {}
        for foreign_model, foreign_path in my_foreign_models.items():
            foreign_models[foreign_model] = foreign_path
        return foreign_models
    
    
    def available_filters(self):
        return self.qbfilters
    
    def available_group(self):
        return self.qbgroup_by
    
    def available_date_criteria(self):
        return self.qbdate_criteria

def get_granularity(delta, min, max):
    """
    Finds a granularity that will display a number of points between 'min' and 'max'
    for this timedelta
    """
    # available_granularities = ['second','minute','hour','day','week','month','quarter','year','decade','century','millennium']
    found = False
    available_granularities = [
        ('day'       , 1),
        ('week'      , 7),
        ('month'     , 30),
        ('quarter'   , 4 * 30),
        ('year'      , 360),
        ('decade'    , 3600),
        ('century'   , 36000),
        ('millennium', 360000),
        ]
    actual_point_number = None
    current_granularity_index = current_granularity = None
    while (actual_point_number is None or actual_point_number > max):
        if current_granularity_index is None:
            current_granularity_index = 0
        else:
            current_granularity_index += 1
        current_granularity = available_granularities[current_granularity_index]
        actual_point_number = float(delta.days) / current_granularity[1]
    if actual_point_number > min:
        found = True
    if not found:
        # Less than a day, compute delta.seconds
        available_granularities = [
            ('second' , 1),
            ('minute' , 60),
            ('hour'   , 60*60),
            ('day'   , 24*60*60),
            ]
        seconds = delta.seconds + delta.days * 60*60*24
        actual_point_number = None
        current_granularity_index = current_granularity = None
        while (actual_point_number is None or actual_point_number > max):
            logger.debug("apn %s, cgi %s, cg %s", actual_point_number, current_granularity_index, current_granularity)
            if current_granularity_index is None:
                current_granularity_index = 0
            else:
                current_granularity_index += 1
            current_granularity = available_granularities[current_granularity_index]
            actual_point_number = float(seconds) / current_granularity[1]
    if not current_granularity:
        logger.error("Can't comput granularity for delta %s min %s max %s", delta, min, max)
    return current_granularity[0]

class QueryBuilder(object):
    """
    Génère une requête SQL permettant de faire des statistiques.
    Génère également les "paramètres" permettant de demande à DOJO de dessiner les graphes.
    
    Prend en paramètre les "data" qui sont en fait les critères servant à générer les requêtes.
    
    Voici un exemple de "data" complet :
      {
        u'whattodo': u'evolution',                          # Que faire (count ou evolution)
        u'model': u'Demande',                               # Sur quel modele (doit etre déclaré ci dessus)
        u'display_type_choice': u'linechart',               # Quel type d'affichage
        u'model_for_filter_0': u'Testbio',                  # Modèle utiliser pour le filtrage
        u'field_for_filter_0': u'bilan'                     # Champ de ce modèle
        u'type_for_filter_0': u'IN',                        # Type de filtre
        u'value_for_filter_0[]': [u'PLA', u'NF', u'TP'],    # Valeurs du filtre
        u'field_for_grouping_0': u'bilan',                  # Modèle utiliser pour regrouper les données
        u'model_for_grouping_0': u'Testbio',                # Champ de ce modèle
      }
    """
    
    def __init__(self, data):
        self.data = data
        self.model_class = None
        self.model = None
        self.all_data    = []
        self.resulting_keys=[]
        self.query = None
        self.legend = None
        self.start_filter = self.end_filter = self.start_date = self.end_date = None
        self.granularity = self.granularity_criteria = None
        self.filters  = []
        self.group_by = []
        self.joins    = []
        self.select   = []
        self.date_criteria_field = None
        self.extras   = {}
        self.extract_extras_from_data()
        # TODO : paramétrable :
        self.MIN_POINTS = 10
        self.MAX_POINTS  = 200
        self.name_field_to_color = None
        self.field_to_color = None
    
    def add_join(self, models):
        if not isinstance(models, list):
            models = [models,]
        for model in models:
            if model not in self.joins:
                self.joins.append(model)
    
    def extract_extras_from_data(self):
        for key, value in self.data.items():
            if key.startswith('value_for_extra_'):
                extra_nb = key.split('_')[3]
                extra_type = self.data.get('extra_type_%s' % (extra_nb,))
                extra_choice = self.data.get('extra_choice_%s' % (extra_nb,))
                self.extras.setdefault(extra_type, {})[extra_choice] = value
        logger.debug("extras : %s", self.extras)
    
    def prepare_query(self, whattodo):
        if whattodo == 'count':
            return self.prepare_query_count()
        elif whattodo == 'evolution':
            return self.prepare_query_evolution()
    
    def prepare_query_count(self):
        self.name_field_to_color = u"Nombre de %ss" % (self.model_class.__name__,)
        self.field_to_color = func.count(self.model_class.pk.distinct())
        self.select.append(self.field_to_color.label(self.name_field_to_color))
        return True
    
    def prepare_query_evolution(self):
        self.name_field_to_color = u"Nombre de %ss" % (self.model_class.__name__,)
        self.field_to_color = func.count(self.model_class.pk.distinct())
        self.select.append(self.field_to_color.label(self.name_field_to_color))
        # Si on cherche a grapher une evolution dans le temps mais qu'on n'a pas precise de critere de filtrage par date,
        #    on force l'affichage sur un an avec une granularite par mois
        date_criteria_name = self.model.available_date_criteria()
        self.date_criteria_field = getattr(self.model_class, date_criteria_name, None)
        if not date_criteria_name or not self.date_criteria_field:
            return False
        self.end_date     = datetime.datetime.now()
        self.start_date   = self.end_date - datetime.timedelta(days = 365)
        self.start_filter = self.date_criteria_field > self.start_date
        self.end_filter   = self.date_criteria_field < self.end_date
        return True
    
    def generate_display_layout(self, display_type, extra_attributes = {}):
        display_layout = extra_attributes
        if not self.all_data:
            return display_layout
        if display_type == 'table':
            display_layout.update(self.generate_table())
        elif display_type == 'piechart':
            display_layout.update(self.generate_piechart())
        elif display_type == 'barchart':
            display_layout.update(self.generate_barchart())
        elif display_type == 'linechart':
            display_layout.update(self.generate_linechart())
        elif display_type == 'gauge':
            display_layout.update(self.generate_gauge())
        return display_layout
    
    def generate_table(self):
        if not self.resulting_keys:
            self.get_data_keys()
        grid_layout_structure = []
        nb_keys = len(self.resulting_keys)
        for k in [key for key in self.resulting_keys if key != '_classes_']:
            field_layout = {
                "field" : k,
                "name" : k,
                "width" : "%i%%" % (int(100.0/nb_keys)),
                }
            if self.name_field_to_color and k == self.name_field_to_color:
                field_layout["coloring"] = True
            grid_layout_structure.append(field_layout)
        return {'structure' : grid_layout_structure}
        
    def generate_piechart(self):
        if not self.all_data:
            self.grab_data()
        serie_data = []
        for data_line in self.all_data:
            try:
                serie_data.append({
                    'y' : float(data_line[0]),
                    'text' : " _ _ ".join(["%s" % (item,) for item in data_line[1:]]),
                    })
            except (ValueError, KeyError):
                serie_data.append({
                    'y' : 0,
                    'text' : 'error',
                    })
        pie_layout = {
            'piestyle': {
                'type' : 'Pie',
                'font' : 'normal normal bold 12pt Tahoma',
                'fontColor': 'black',
                'labelOffset' : -40,
                },
            'series'  : [{
                'title' : 'Nombre',
                'data'  : serie_data,
                }],
            }
        return pie_layout
    
    def generate_barchart(self):
        if not self.resulting_keys:
            self.get_data_keys()
        nb_keys = len(self.resulting_keys)
        if nb_keys < 2 or nb_keys > 3:
            return None
        bar_layout = {}
        # Supposons que key_0 = nombre, key=1 = heure, key_2 = mois
        # on veut donc voir en axe X les heures
        # en Z les mois
        # en Y le nombre
        # on va donc devoir générer Z séries contenant chacune X valeurs de Y
        series_data = {}
        existing_second_keys = []
        for data_line in self.all_data:
            # si on a 3 clés, on génère une série identifiée par la troisième clé (le mois par exemple)
            # sinon, on génère une série "anonyme"
            if nb_keys == 3:
                ident_serie = data_line[2]
            else:
                ident_serie = self.resulting_keys[0]
            cette_serie = series_data.get(ident_serie, None)
            if not cette_serie:
                cette_serie = {
                    'title' : nb_keys == 3 and "%s (%s : %s)" % (self.resulting_keys[0], self.resulting_keys[2], data_line[2]) or self.resulting_keys[0],
                    'data'  : {},
                    }
            if data_line[1] not in existing_second_keys:
                existing_second_keys.append(data_line[1])
            cette_serie['data'][data_line[1]] = data_line[0]
            series_data[ident_serie] = cette_serie
        existing_second_keys.sort()
        # Maintenant on range ça à la sauce qui va bien pour les barchart :
        # on va se débrouiller pour que chaque série ait une valeur pour chaque "Y"
        final_series = []
        for serie_ident, serie_dict in series_data.items():
            serie_name = serie_dict['title']
            serie_data = serie_dict['data']
            final_series.append({
                'title' : serie_name,
                'data'  : [serie_data.get(key, 0) for key in existing_second_keys],
                'ident' : serie_ident,
                #~ 'styling': {'stroke' :{'color':'red'}, 'fill':'lightpink'},
                })
        final_series.sort(lambda a,b: cmp(a.get('ident',0), b.get('ident',0)))
        bar_layout['series'] = final_series
        bar_layout['x_labels'] = [{'value': index + 1, 'text': key,} for index, key in enumerate(existing_second_keys)]
        return bar_layout
    
    def generate_gauge(self):
        if not self.resulting_keys:
            self.get_data_keys()
        nb_keys = len(self.resulting_keys)
        title_keys = [k for k in self.resulting_keys if k != '_classes_']
        min = int(self.extras.get('borne',{}).get('min', '0'))
        max = int(self.extras.get('borne',{}).get('max', '100'))
        delta = max - min
        # TODO : trouver un moyen plus sympa
        #~ min_interval = int(str(delta/40)[0] + '0' * (len(str(delta/40))-1))
        max_interval = int(str(delta/20)[0] + '0' * (len(str(delta/20))-1))
        min_interval = max_interval / 2.0
        layout = {
            'gauge' : {
                #~ 'id': 'gauge%s' % (self.pk),
                'width': 320,
                'height': 270,
                'radius': 150,
                'cx':160,
                'cy':155,
                'startAngle': -135,
                'endAngle':135,
                #~ 'useRangeStyles': 8,
                'ranges' : [{'low': min, 'high': max, 'color': 'gray'},],
                'minorTicks': {'offset': 110, 'interval': min_interval,  'length': 5,  'color': 'black'},
                'majorTicks': {'offset': 110, 'interval': max_interval, 'length': 10, 'color': 'black'},
                },
            'indicators' : [],
            }
        logger.debug("keys %s", title_keys)
        for data_line in self.all_data:
            logger.debug("data_line %s",data_line)
            try:
                class_column = self.resulting_keys.index('_classes_')
            except ValueError:
                class_column = None
            if class_column and data_line[class_column] is not None:
                color = {
                    'breaks_min_bound' : '#FFD9A8',
                    'breaks_max_bound' : '#FFA8A8',
                    }.get(data_line[class_column], '#A8CAFF')
            else:
                color = '#A8CAFF'
            hover = "<ul>%s</ul>" % ("".join(["<li>%s : %s</li>" % (title_keys[i], data_line[i],) for i in range(len(title_keys))]),)
            try:
                layout['indicators'].append({
                    'value': float(data_line[0]),
                    'title' : "title",
                    'tooltip' : hover,
                    'width' : 5,
                    'color' : color,
                    'length': 140,
                    })
            except (ValueError, KeyError):
                layout['indicators'].append({'value':0, 'title': 'error',})
        return layout
        
    def generate_linechart(self):
        if not self.resulting_keys:
            self.get_data_keys()
        nb_keys = len(self.resulting_keys)
        granularity_to_date_format = {
            'second' : ('%H:%M:%s', 'hh:mm:ss'),
            'minute' : ('%H:%M', 'hh'),
            'hour' : ('%d %H:00', 'dd hh:00'),
            'day' : ('%d/%m/%Y', 'dd/MM/yyyy'),
            'week' : ('Semaine du %d/%m/%Y', 'dd/MM/yyyy'),
            'month' : ('%m/%Y', 'MM/yyyy'),
            'quarter' : ('Trimestre du %m/%Y', 'MM/yyyy'),
            'year' : ('%Y', 'yyyy'),
            'century' : (u'Siècle de %Y', 'yyyy'),
            'millennium' : (u'Millénaire de %Y', 'yyyy'),
            }
        granularity_to_date_selector = {
            'second' : 'hour',
            'minute' : 'hour',
            'hour' : 'hour',
            'day' : 'date',
            'week' : 'date',
            'month' : 'date',
            'quarter' : 'date',
            'year' : 'date',
            'century' : 'date',
            'millennium' : 'date',
            }
        date_format_python, date_format_dojo = granularity_to_date_format.get(self.granularity, ('%d/%m/%Y','dd/MM/yyyy'))
        series_data = {}
        existing_second_keys = []
        labels = []
        first_line = True
        for data_line in self.all_data:
            # si on a 3 clés, on génère une série identifiée par la troisième clé
            # sinon, on génère une série anonyme
            if nb_keys == 3:
                ident_serie = data_line[2]
            else:
                ident_serie = self.resulting_keys[0]
            cette_serie = series_data.get(ident_serie, None)
            if not cette_serie:
                cette_serie = {
                    'title' : nb_keys == 3 and "%s (%s : %s)" % (self.resulting_keys[0], self.resulting_keys[2], data_line[2]) or self.resulting_keys[0],
                    'data'  : {},
                    }
            if data_line[1] not in existing_second_keys:
                existing_second_keys.append(data_line[1])
            labels.append({
                'value' : time.mktime(data_line[1].timetuple()),
                'text'  : data_line[1].strftime(date_format_python),
                })
            cette_serie['data'][data_line[1]] = data_line[0]
            series_data[ident_serie] = cette_serie
        existing_second_keys.sort()
        # Et on réarrange tout ça
        final_series = []
        for serie_ident, serie_dict in series_data.items():
            serie_name = serie_dict['title']
            serie_data = serie_dict['data']
            final_series.append({
                'title' : serie_name,
                'data'  : [{
                    'x' : time.mktime(key.timetuple()),
                    'y' : serie_data.get(key, 0),
                    'tooltip':"%s<br/>%s : %s" % (serie_name, key.strftime(date_format_python), serie_data.get(key, 0)),
                    } for key in existing_second_keys],
                'ident' : serie_ident,
                })
        final_series.sort(lambda a,b : cmp(a.get('ident',0), b.get('ident',0)))
        line_layout = {
            'series' : final_series,
            'labels' : labels,
            'date_formatting' : {'selector' : granularity_to_date_selector.get(self.granularity, 'date'), 'datePattern' : date_format_dojo},
            }
        return line_layout
    
    def prepare_filters_and_grouping(self):
        # pour mettre les filtres/groupes dans l'ordre spécifié par l'utilisateur
        filter_nbs = []
        grouping_nbs = []
        for key, value in self.data.items():
            if key.startswith('value_for_filter_'):
                filter_nb = key.split('_')[3]
                if key.endswith('[]'):
                    filter_nb = filter_nb[:-2]
                filter_nbs.append((int(filter_nb), value))
            elif key.startswith('field_for_grouping_'):
                grouping_nbs.append((int(key.split('_')[3]), value))
            filter_nbs.sort(lambda a,b: cmp(a[0],b[0]))
            grouping_nbs.sort(lambda a,b: cmp(a[0],b[0]))
        return filter_nbs, grouping_nbs
    
    def make_filter(self, field, ftype, value):
        filter = None
        if ftype == 'IN':
            filter = field.in_([v for v in value if v])
        elif ftype == 'date_gt':
            filter = field >  value
        elif ftype == 'date_gte':
            filter = field >= value
        elif ftype == 'date_lt':
            filter = field <  value
        elif ftype == 'date_lte':
            filter = field <= value
        elif ftype == '=':
            filter = field == value
        elif ftype == '!=':
            filter = field != value
        elif ftype == '>':
            filter = field >  value
        elif ftype == '>=':
            filter = field >= value
        elif ftype == '<':
            filter = field <  value
        elif ftype == '<=':
            filter = field <= value
        return filter

    def get_join_path(self, from_model, to_model):
        from querybuilder.qbmodels import get_model_by_name
        final_path = []
        foreigns = from_model().available_foreigns()
        join_path = foreigns.get(to_model.__name__, None)
        if join_path:
            final_path = [get_model_by_name(model_name) for model_name in join_path]
        final_path.append(to_model)
        return final_path

    def generate_filters(self, filter_nbs):
        from querybuilder.qbmodels import get_model_by_name
        model = self.model_class()
        whattodo = self.data.get('whattodo', None)
        for filter_nb, value in filter_nbs:
            foreign_model = foreignkey_to_model = foreignfield = filter_type = None
            this_filter = None
            foreign_model       = get_model_by_name(self.data.get('model_for_filter_%s' % (filter_nb,), None))
            foreignfield        = getattr(foreign_model, self.data.get('field_for_filter_%s' % (filter_nb,), None), None)
            filter_type         = self.data.get('type_for_filter_%s'  % (filter_nb,), None)
            if foreignfield and filter_type:
                this_filter = self.make_filter(foreignfield, filter_type, value)
                if this_filter is not None:
                    if whattodo == 'evolution' and foreignfield == getattr(self.model_class, model.available_date_criteria(), None) and filter_type in ('date_gt', 'date_gte'):
                        self.start_date   = datetime.datetime.strptime(value, '%Y-%m-%d')
                        self.start_filter = this_filter
                    elif whattodo == 'evolution' and foreignfield == getattr(self.model_class, model.available_date_criteria(), None) and filter_type in ('date_lt', 'date_lte'):
                        self.end_date   = datetime.datetime.strptime(value, '%Y-%m-%d')
                        self.end_filter = this_filter
                    else:
                        self.filters.append(this_filter)
                        if not isinstance(self.model, foreign_model):
                            self.add_join(self.get_join_path(self.model_class, foreign_model))

    def make_grouping(self, grouping_info, model, field):
        group_type, group_args, group_name = grouping_info
        grouping = None
        if group_type == "extract":
            subfield, field_name = group_args
            real_field = getattr(model, field_name, None)
            if real_field:
                grouping = extract(subfield, real_field).label(group_name)
            else:
                logger.error("Invalid grouping %s (%s %s)", grouping_info, model, field)
        elif group_type == "func":
            logger.error("Grouping by func not implemented yet")
        else:
            logger.error("Unknown grouping type %s", group_type)
        return grouping

    def generate_groupings(self, grouping_nbs):
        from querybuilder.qbmodels import get_model_by_name
        for grouping_nb, value in grouping_nbs:
            this_grouping = foreignkey_to_model = None
            foreign_model = get_model_by_name(self.data.get('model_for_grouping_%s' % (grouping_nb,), None))
            foreignfield_name  = self.data.get('field_for_grouping_%s' % (grouping_nb,), None)
            foreignfield = getattr(foreign_model, foreignfield_name, None)
            if foreign_model:
                if foreignfield:
                    this_grouping = foreignfield
                else:
                    grouping_info = foreign_model().available_group().get(foreignfield_name, None)
                    if grouping_info:
                        this_grouping = self.make_grouping(grouping_info[1], foreign_model, foreignfield_name)
                if this_grouping is not None:
                    self.group_by.append(this_grouping)
                    self.select.append(this_grouping)
                    if not isinstance(self.model, foreign_model):
                        self.add_join(self.get_join_path(self.model_class, foreign_model))

    def build_query(self):
        from querybuilder.qbmodels import get_model_by_name
        result = {}
        data = self.data
        logger.debug("data %s", data)
        self.model_class = get_model_by_name(data.get('model', None))
        class ArretTraitement(Exception):
            pass

        display_type = data.get('display_type_choice', 'table')
        whattodo     = data.get('whattodo', None)
        try:
            if not self.model_class or not whattodo:
                raise ArretTraitement
            self.model = self.model_class()
            if not self.prepare_query(whattodo):
                raise ArretTraitement
            filter_nbs, grouping_nbs = self.prepare_filters_and_grouping()
            self.generate_filters(filter_nbs)
            self.generate_groupings(grouping_nbs)
            
            # SQLALCHEMY PART
            # TODO : lire settings
            session = sessionmaker(bind = create_engine(sql_connection_string))()
            if self.granularity_criteria is None and whattodo == 'evolution':
                date_delta = self.end_date - self.start_date
                self.granularity = get_granularity(date_delta, self.MIN_POINTS, self.MAX_POINTS)#'month'
                self.granularity_criteria = func.date_trunc(self.granularity, self.date_criteria_field).label("Date")
            if self.granularity_criteria is not None:
                self.select.insert(1,self.granularity_criteria)
                self.group_by.insert(0,self.granularity_criteria)
            if self.extras:
                borne_max = self.extras.get('borne', {}).get('max', None)
                classes_case = []
                if borne_max and self.field_to_color is not None:
                    classes_case.append((self.field_to_color > borne_max, literal_column("'breaks_max_bound'",String)))
                borne_min = self.extras.get('borne', {}).get('min', None)
                if borne_min and self.field_to_color is not None:
                    classes_case.append((self.field_to_color < borne_min, literal_column("'breaks_min_bound'",String)))
                self.select.append(case(classes_case).label("_classes_"))
            #~ logger.debug("select %s",self.select)
            self.query = session.query(*self.select)
            #~ logger.debug("start_filter %s", self.start_filter)
            if self.start_filter is not None:
                self.filters.append(self.start_filter)
            #~ logger.debug("end_filter %s", self.end_filter)
            if self.end_filter is not None:
                self.filters.append(self.end_filter)
            #~ self.joins = list(set(self.joins))
            logger.debug("joins %s",self.joins)
            if self.joins:
                self.query = self.query.join(*self.joins)
            #~ logger.debug("filters %s",self.filters)
            for filter in self.filters:
                self.query = self.query.filter(filter)#.filter(model_class.date_demande > '2010-01-01').filter(model_class.date_demande < '2010-02-01')
            #~ logger.debug("group_by %s",self.group_by)
            if self.group_by:
                self.query = self.query.group_by(*self.group_by)
            
            # Mandatory Limit
            if self.query:
                self.query = self.query.limit(1000) # TODO : rendre paramétrable
                # Result processing
                logger.debug("query %s", self.query)
        except ArretTraitement:
            logger.error(traceback.format_exc())
        except:
            raise
        return self.query
        
    def grab_data(self):
        if not self.query:
            self.build_query()
        if self.query:
            self.all_data = self.query.all()
        return self.all_data
    
    def get_data_keys(self):
        if not self.all_data:
            self.grab_data()
        if self.all_data:
            self.resulting_keys = self.all_data[0].keys()
        return self.resulting_keys

    def get_content(self):
        # TODO : voir ce qu'on pourrait y mettre
        return ""
        
    def get_javascript(self):
        if not self.all_data:
            return u""
        display_type = self.data.get('display_type_choice', 'table')
        display_layout_extra = {
            'hide_legend' : self.data.get('hide_legend', True),
            'resize' : {'width': 350, 'height': 200},
            }
        display_layout = json.dumps(self.generate_display_layout(display_type, extra_attributes = display_layout_extra))
        js_dict = {'display_type' : display_type, 'layout' : display_layout, 'pk' : self.pk}
        display_type2js = {
            'table'     : "generate_%(display_type)s(%(layout)s, 'indicateur-tat-content-%(pk)s', '%(pk)s', 'resultingDataTable-%(pk)s', true);",
            'linechart' : "generate_%(display_type)s(%(layout)s, 'indicateur-tat-content-%(pk)s', '%(pk)s', true);",
            'barchart'  : "generate_%(display_type)s(%(layout)s, 'indicateur-tat-content-%(pk)s', '%(pk)s', true);",
            'piechart'  : "generate_%(display_type)s(%(layout)s, 'indicateur-tat-content-%(pk)s', '%(pk)s', true);",
            'gauge'     : "generate_%(display_type)s(%(layout)s, 'indicateur-tat-content-%(pk)s', '%(pk)s', true);",
            }
        if display_type not in display_type2js:
            return "alert('unknown display type %s');" % (display_type,)
        return display_type2js[display_type] % js_dict


class TatQueryBuilder(QueryBuilder):
    def prepare_query(self, whattodo):
        result = False
        if whattodo == 'event_delta':
            result = self.prepare_query_event_delta()
        if whattodo == 'event_delta_evolution':
            result = self.prepare_query_event_delta_evolution()
        self.filters.append(self.model_class.temps_reel > datetime.timedelta(days = 0))
        if 'starting_event_choice' in self.data:
            self.filters.append(self.model_class.start_evt == self.data.get('starting_event_choice'))
            #~ self.select.append(self.model_class.start)
            #~ self.group_by.append(self.model_class.start)
        if 'ending_event_choice' in self.data:
            self.filters.append(self.model_class.end_evt == self.data.get('ending_event_choice'))
            #~ self.select.append(self.model_class.end)
            #~ self.group_by.append(self.model_class.end)
        return result
    
    def prepare_query_event_delta_evolution(self):
        self.select.append(extract('epoch', cast(self.model_class.temps_reel, Interval())).label(u"Temps"))
        self.select.append(self.model_class.end_date.label(u"Date (de fin)"))
        return True

    def prepare_query_event_delta(self):
        self.select.append(func.count(self.model_class.pk.distinct()).label(u"Nombre d'évènements"))
        self.select.append(func.max(self.model_class.temps_reel).label(u"Temps max"))
        self.select.append(func.min(self.model_class.temps_reel).label(u"Temps min"))
        self.select.append(func.avg(self.model_class.temps_reel).label(u"Temps moyen"))
        self.select.append(interval_stddev(self.model_class.temps_reel).label(u"Ecart type"))
        return True
    
    def build_query(self):
        result = {}
        data = self.data
        logger.debug("data %s", data)
        self.model_class = Evenement
        class ArretTraitement(Exception):
            pass
        
        display_type = data.get('display_type_choice', 'table')
        whattodo     = data.get('whattodo', 'event_delta')
        try:
            if not self.model_class or not whattodo:
                raise ArretTraitement
            self.model = self.model_class()
            if not self.prepare_query(whattodo):
                raise ArretTraitement
            filter_nbs, grouping_nbs = self.prepare_filters_and_grouping()
            self.generate_filters(filter_nbs)
            self.generate_groupings(grouping_nbs)
            
            # SQLALCHEMY PART
            # TODO : lire settings
            session = sessionmaker(bind = create_engine(sql_connection_string))()
            if self.granularity_criteria is None and whattodo == 'evolution':
                date_delta = self.end_date - self.start_date
                self.granularity = get_granularity(date_delta, self.MIN_POINTS, self.MAX_POINTS)#'month'
                self.granularity_criteria = func.date_trunc(self.granularity, self.date_criteria_field).label("Date")
            if self.granularity_criteria is not None:
                self.select.insert(1,self.granularity_criteria)
                self.group_by.insert(0,self.granularity_criteria)
            #~ logger.debug("select %s",self.select)
            self.query = session.query(*self.select)
            #~ logger.debug("start_filter %s", self.start_filter)
            if self.start_filter is not None:
                self.filters.append(self.start_filter)
            #~ logger.debug("end_filter %s", self.end_filter)
            if self.end_filter is not None:
                self.filters.append(self.end_filter)
            #~ logger.debug("joins %s",self.joins)
            if self.joins:
                self.query = self.query.join(*self.joins)
            #~ logger.debug("filters %s",self.filters)
            for filter in self.filters:
                self.query = self.query.filter(filter)#.filter(model_class.date_demande > '2010-01-01').filter(model_class.date_demande < '2010-02-01')
            #~ logger.debug("group_by %s",self.group_by)
            if self.group_by:
                self.query = self.query.group_by(*self.group_by)
            
            # Mandatory Limit
            if self.query:
                self.query = self.query.limit(1000) # TODO : rendre paramétrable
                # Result processing
                logger.debug("query %s", self.query)            
        except ArretTraitement:
            logger.error(traceback.format_exc())
        except:
            raise
        return self.query
    

def LoadQueryBuilder(existing_query_pk):
    mapping = {
        'event_delta' : TatQueryBuilder,
        'event_delta_evolution' : TatQueryBuilder,
        }
    qbuilder = None
    try:
        qbq = QbuilderQuery.objects.get(pk = existing_query_pk)
    except QbuilderQuery.DoesNotExist:
        logger.error('Pas de QbuilderQuery #%s dans la base', existing_query_pk)
    else:
        data = json.loads(qbq.data)
        qbuilder = mapping.get(data.get('whattodo', None), QueryBuilder)(data)
        qbuilder.pk = existing_query_pk
        qbuilder.title = qbq.name
        qbuilder.get_data_keys()
    return qbuilder
