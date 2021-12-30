from . import models

from django_filters import FilterSet, ChoiceFilter, ModelChoiceFilter
from django_filters.widgets import LinkWidget


class ButtonGroupWidget(LinkWidget):
    def option_string(self):
        return '<li><a%(attrs)s href="?%(query_string)s"><button class="btn btn-default" type="button">%(label)s</button></a></li>'


def make_talk_filter(event, *args, **kwargs):
    rooms = [(room.id, room.room) for room in models.Rooms.objects.filter(talk__event__pk=event.id).distinct()]
    languages = [(lang.id, lang.display_name) for lang in models.Language.objects.filter(talk__event__pk=event.id).distinct()]
    states = [(status.id, status.state_en) for status in models.States.objects.all()]

    class TalkFilter(FilterSet):
        day = ModelChoiceFilter(queryset=event.event_days_set.all(), widget=ButtonGroupWidget(attrs={'class': 'btn-group', 'role': 'group'}))
        room = ChoiceFilter(choices=rooms, widget=ButtonGroupWidget(attrs={'class': 'btn-group', 'role': 'group'}))
        orig_language = ChoiceFilter(choices=languages, widget=LinkWidget)
        id = ChoiceFilter(choices=states, lookup_expr='original_language_status')

        class Meta:
            model = models.Talk
            fields = ()

    return TalkFilter(*args, **kwargs)
