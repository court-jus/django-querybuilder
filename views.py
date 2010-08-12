# -*- coding: utf-8 -*-

from django.shortcuts               import render_to_response, get_object_or_404
from django.http                    import HttpResponse, HttpResponseRedirect
from django.template                import RequestContext
from django.core.urlresolvers       import reverse
from django.core.paginator          import Paginator, InvalidPage, EmptyPage
from django.conf                    import settings
from django.db.models               import Count, Avg, Min, Max
from django.utils.safestring import mark_safe

from django.contrib.auth.models     import User

from querybuilder.qbuilder import LoadQueryBuilder
import querybuilder.models

import datetime
import traceback
import os
import urllib
import time

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter, date2num, num2date
from matplotlib.ticker import FuncFormatter, LogLocator
from matplotlib.patches import Rectangle
from matplotlib.font_manager import FontProperties

import logging
logger = logging.getLogger("querybuilder")

def render_to_response_wrapper(request, dict = {}, help_file = 'index.rst', template = 'index.html', active_tab = 'accueil'):
    help = ''
    dict.update({'active_tab':active_tab})
    return render_to_response('querybuilder/' + template,dict,context_instance = RequestContext(request,"TAT"))

def accueil(request):
    indicateurs = [LoadQueryBuilder(pk) for pk in querybuilder.models.QbuilderQuery.objects.values_list('pk', flat = True)]
    dict = {'indicateurs' : indicateurs,
            'colonnes' : 3,
        }
    return render_to_response_wrapper(request, dict = dict)

def qbuilder(request):
    return render_to_response_wrapper(request, template = 'qbuilder.html', active_tab = 'qbuilder')

