﻿from django.conf.urls import patterns, include, url, static
from . import views
from django.core.urlresolvers import reverse_lazy
from django.conf import settings

urlpatterns = patterns('',
        url(r'^$', views.start, name="home"),
        url(r'^hello/$',views.clock),
        url(r'^event/(?P<event_acronym>\w+)/$', views.event, name="event"),
        url(r'^event/(?P<event_acronym>\w+)/day/(?P<day>\d+)$', views.event),
        url(r'^event/(?P<event_acronym>\w+)/day/(?P<day>\d+)/lang/(?P<lang>\w+)$', views.event),
        url(r'^talk/(?P<talk_id>\d+)/$', views.talk, name="talk"),
        url(r'^subtitle/(?P<subtitle_id>\d+)/$', views.updateSubtitle, name="updateSub"),
        url(r'^subtitle/(?P<subtitle_id>\d+)/thanks$', views.addThanks, name="addThanks"),
        url(r'^clock/$',views.clock),
        #url(r'^logo', views.eventLogo),
        #url(r'^', views.eventStatus),
        
)
if settings.DEBUG:
    urlpatterns += patterns('django.contrib.staticfiles.views',
        url(r'^static/(?P<path>.*)$','serve'))
        
