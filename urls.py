# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('querybuilder.services',
    (r'whattodochoose','whattodochoose'),
    (r'modelchoose','modelchoose'),
    (r'filteradd','filteradd'),
    (r'groupingadd','groupingadd'),
    (r'extrachoiceadd','extrachoiceadd'),
    (r'test_query','test_query'),
    (r'starting_event_choose','starting_event_choose'),
    (r'ending_event_choose','ending_event_choose'),
    (r'save_query','save_query'),
)

urlpatterns += patterns('querybuilder.views',
    (r'^$','accueil'),
    (r'qbuilder/$','qbuilder'),
)

urlpatterns += patterns('',
    (r'media/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : '/home/gl/src/qbuilder/qbuilder/querybuilder/media'}),
    )