﻿# -*- coding: utf-8 -*-

from datetime import datetime
from django.db import models
from django.db.models import Sum, Q
from django.core.urlresolvers import reverse
from django.db import transaction
from .statistics_helper import *

# Basic model which provides a field for the creation and the last change timestamp
class BasisModell(models.Model):
    created = models.DateTimeField(auto_now_add = True)
    touched = models.DateTimeField(auto_now = True)

    class Meta:
        abstract = True


# For every event in which subfolder on the ftp the subtitles are supposed to appear and with which file extensions
class Folders_Extensions(BasisModell):
    subfolder = models.CharField(max_length = 10, default = "", blank = True)
    file_extension = models.CharField(max_length = 10, default = "", blank = True)        

    def __str__(self):
        return self.subfolder+","+self.file_extension

    
# Event and its data
class Event(BasisModell):
    schedule_version = models.CharField(max_length = 50, default = "0.0", blank = True)
    acronym = models.CharField(max_length = 20, default = "", blank = True)
    title = models.CharField(max_length = 100, default = "No title yet", blank = True)
    start = models.DateField(default = "1970-01-01", blank = True)
    end = models.DateField(default = "1970-01-01", blank = True)
    timeslot_duration = models.TimeField(default = "00:15", blank = True)
    days = models.PositiveSmallIntegerField(default = 1, blank = True)
    schedule_xml_link = models.URLField()
    city = models.CharField(max_length = 30, default = "", blank = True)
    building = models.CharField(max_length = 30, default = "", blank = True)
    ftp_startfolder = models.CharField(max_length = 100, default = "", blank = True)
    ftp_subfolders_extensions = models.ManyToManyField(Folders_Extensions, default = None, blank = True)
    hashtag = models.CharField(max_length = 10, default = "", blank = True)
    subfolder_to_find_the_filenames = models.CharField(max_length = 20, default = "", blank = True) # To find the right filenames via regex via frab-id
    
    def isDifferent(id, xmlFile):
        with open("data/eventxml/{}.xml".format(id),'rb') as f:
            savedXML = f.read()
            return savedXML == xmlFile.data
    
    
    # Create Entries in Statistics_Event model for any available combination
    def create_statistics_event_entries(self):
        my_subtitles = Subtitle.objects.filter(is_original_lang = True, talk__event = self)
        my_talks = Talk.objects.filter(event = self)
        for any in my_subtitles:
            this = Statistics_Event.objects.get_or_create(event = self, language = any.language)
            # If new created, than also set the flag for recalculate
            if this[1]:
                this[0].recalculate_statistics = True
                this[0].save()
        for any in my_talks:
            this = Statistics_Event.objects.get_or_create(event = self, language = any.orig_language)
            # If new created, also recalculate
            if this[1]:
                this[0].recalculate_statistics = True
                this[0].save()

    @property
    def page_sub_titles(self):
        return [self.acronym]

# Days which belong to an event
class Event_Days(BasisModell):
    event = models.ForeignKey(Event)
    index = models.PositiveSmallIntegerField(default = 0)
    date = models.DateField(default = "1970-01-01", blank = True)
    day_start = models.DateTimeField(default = "1970-01-01 00:00", blank = True)
    day_end = models.DateTimeField(default = "1970-01-01 00:00", blank = True)

    
# "Rooms" in which an event takes place, might also be outside
class Rooms(BasisModell):
    room = models.CharField(max_length = 30, default = "kein Raum")
    building = models.CharField(max_length = 30, default = "")

    def __str__(self):
        return self.room

        
# Different languages and their "codes" in amara or the name in German end English in full names
class Language(BasisModell):
    language_en = models.CharField(max_length = 40, default = "")
    language_de = models.CharField(max_length = 40, default = "", blank = True)
    #lang_short_2 = models.CharField(max_length = 3, default = "", blank = True)#, unique = True) not really used
    lang_amara_short = models.CharField(max_length = 15, default = "", unique = True)
    lang_short_srt = models.CharField(max_length = 15, default = "", blank = True)
    language_native = models.CharField(max_length = 40, default = "", blank = True)
    amara_order = models.PositiveSmallIntegerField(default = 0, blank = True)
    lang_code_media = models.CharField(max_length = 3, default = "", blank = True) # ISO 639-2 to talk to the media.ccc.de API
    lang_code_iso_639_1 = models.CharField(max_length = 10, default = "", blank = True)

    def __str__(self):
        return self.lang_amara_short

        
# Category of the talk, like "ethics"
class Tracks(BasisModell):
    track = models.CharField(max_length = 50, default = "")

    def __str__(self):
        return self.track

        
# How the talk is presented, like a workshop or a talk
class Type_of(BasisModell):
    type = models.CharField(max_length = 20, default = "")

    def __str__(self):
        return self.type

        
# Speaker or Speakers of the Talk
class Speaker(BasisModell):
    frab_id = models.PositiveSmallIntegerField(default = -1)
    name = models.CharField(max_length = 50, default = "")
    doppelgaenger_of = models.ForeignKey('self', on_delete = models.SET_NULL, blank = True, null = True)

    def average_wpm_in_one_talk(self, talk):
        my_statistics = Statistics_Raw_Data.objects.filter(speaker = self, talk = talk)
        words = 0
        time = 0
        for this_statistics in my_statistics:
            if this_statistics.words is not None and this_statistics.time_delta is not None:
                words += this_statistics.words
                time += this_statistics.time_delta
            else:
                return None
        if time == 0:
            return None
        return words * 60.0 / time
    
    def average_spm_in_one_talk(self, talk):
        my_statistics = Statistics_Raw_Data.objects.filter(speaker = self, talk = talk)
        strokes = 0
        time = 0
        for this_statistics in my_statistics:
            if this_statistics.strokes is not None and this_statistics.time_delta is not None:
                strokes += this_statistics.strokes
                time += this_statistics.time_delta
            else:
                return None
        if time == 0:
            return None
        return strokes * 60.0 / time

    @property
    def page_sub_titles(self):
        return ['Speakers', self.name]

# Talk with all its data
class Talk(BasisModell):
    frab_id_talk = models.PositiveSmallIntegerField(default = -1)
    blacklisted = models.BooleanField(default=False, blank = True)
    day = models.ForeignKey(Event_Days, default = 1, blank = True)
    room = models.ForeignKey(Rooms, default = 15)
    link_to_logo = models.URLField(default = "", blank = True)
    date = models.DateTimeField(default = "1970-01-01 00:00:00+01:00", blank = True)
    start = models.TimeField(default = "11:00" ,blank = True)
    duration = models.TimeField(default = "00:45", blank = True)
    title = models.CharField(max_length = 150, default = "ohne Titel", blank = True)
    subtitle_talk = models.CharField(max_length = 300, default = " ", blank = True) # nicht UT sondern Ergänzung zum Titel
    track = models.ForeignKey(Tracks, default = 40, blank = True)
    event = models.ForeignKey(Event, default = 3, blank = True)
    type_of = models.ForeignKey(Type_of, default = 9, blank = True)
    orig_language = models.ForeignKey(Language, default = 287, blank = True)
    abstract = models.TextField(default = "", blank = True)
    description = models.TextField(default = "", blank = True)
    persons = models.ManyToManyField(Speaker, through = "Talk_Persons", default = None, blank = True) #through="Talk_Persons"
    pad_id = models.CharField(max_length = 30, default = "", blank = True)
    link_to_writable_pad = models.URLField(default = "", blank = True)
    link_to_readable_pad = models.URLField(default = "", blank = True)
    link_to_video_file = models.URLField(max_length = 200, default = "", blank = True)
    amara_key = models.CharField(max_length = 20, default = "", blank = True)
    youtube_key = models.CharField(max_length = 20, blank = True)
    video_duration = models.TimeField(default = "00:00", blank = True)
    slug = models.SlugField(max_length = 200, default = "", blank = True)
    youtube_key_t_1 = models.CharField(max_length = 20, blank = True, default = "")
    youtube_key_t_2 = models.CharField(max_length = 20, blank = True, default = "")
    guid = models.CharField(max_length = 40, blank = True, default = "") # from the Fahrplan
    filename = models.SlugField(max_length = 200, default = "", blank = True) # will be used for a more flexible sftp upload, at the moment only for the subtitles folder in the root-event directory
    time_delta = models.FloatField(blank = True, null = True)   # The duration of the talk in seconds
    words = models.IntegerField(blank = True, null = True)      # Words in the whole subtitles file
    strokes = models.IntegerField(blank = True, null = True)    # Strokes in the whole subtitles file
    average_wpm = models.FloatField(blank = True, null = True)  # Calculated from the words and the time_delta
    average_spm = models.FloatField(blank = True, null = True)  # Calculated from the strokes and the time_delta
    recalculate_talk_statistics = models.BooleanField(default = False)
    speakers_words = models.IntegerField(blank = True, null = True)      # Words in the parts of all speakers
    speakers_strokes = models.IntegerField(blank = True, null = True)    # Strokes in the parts of all speakers
    speakers_time_delta = models.FloatField(blank = True, null = True)   # The duration of the talk in seconds while all speakers speak - the timeslots are in statistics_Raw_Data
    speakers_average_wpm = models.FloatField(blank = True, null = True)  # Calculated from the speakers_words and the speakers_time_delta
    speakers_average_spm = models.FloatField(blank = True, null = True)  # Calculated from the speakers_strokes and the speakers_time_delta
    recalculate_speakers_statistics = models.BooleanField(default = False)

    # Recalculate statistics data over the whole talk
    @transaction.atomic
    def recalculate_whole_talk_statistics(self, force = False):
        # Recalculate statistics data over the whole talk
        # Only if a original subtitle exists which is at least transcribing finished
        my_subtitles = Subtitle.objects.filter(Q(talk = self),
            Q(is_original_lang = True), Q(complete = True) | Q(state_id = 5) | 
            Q(state_id = 7) | Q(state_id = 3) | Q(state_id = 6))
        if my_subtitles.count() == 1:
            # In this case, recalculate the time_delta
            if force or self.recalculate_talk_statistics:
                values = calculate_subtitle(self)
                if values is not None:
                    self.time_delta = values["time_delta"]
                    self.words = values["words"]
                    self.strokes = values["strokes"]
                    self.average_wpm = values["average_wpm"]
                    self.average_spm = values["average_spm"]
                    self.recalculate_talk_statistics = False
                    self.save()
                # Set recalculate flags in the Statistics_Event module
                Statistics_Event.objects.filter(event = self.event).update(recalculate_statistics = True)
                
                
    # Recalculate Speakers in Talk Statistics-Data
    # If any related data in Statistics_Raw_Data exist!
    @transaction.atomic
    def recalculate_speakers_in_talk_statistics(self, force = False):
        if force or self.recalculate_speakers_statistics:
            # Check for all Statistics_Raw_Data with this talk no matter which Speaker
            all_datasets = Statistics_Raw_Data.objects.filter(talk = self)
            # If there is no data available, set everything to Null
            if all_datasets.count() == 0:
                self.speakers_words = None
                self.speakers_strokes = None
                self.speakers_time_delta = None
                self.speakers_average_wpm = None
                self.speakers_average_spm = None
                self.recalculate_speakers_statistics = False
                self.save()
            else:
                # Check if any of these datasets first needs a recalculation
                # If so, first recalculate:
                for any_dataset in all_datasets:
                    if any_dataset.recalculate_statistics:
                        any_dataset.recalculate()
                # Sum up all words of any speaker in this talk
                self.speakers_words = all_datasets.aggregate(Sum("words"))["words__sum"]
                # Sum up all strokes of any speaker in this talk
                self.speakers_strokes = all_datasets.aggregate(Sum("strokes"))["strokes__sum"]
                # Sum up time_delta of any speaker in this talk
                self.speakers_time_delta = all_datasets.aggregate(Sum("time_delta"))["time_delta__sum"]
                # Calculate stuff
                self.speakers_average_wpm = calculate_per_minute(self.speakers_words, self.speakers_time_delta)
                self.speakers_average_spm = calculate_per_minute(self.speakers_strokes, self.speakers_time_delta)
                self.recalculate_speakers_statistics = False
                self.save()

    # Recalculate statistics-data
    @transaction.atomic
    def recalculate(self, force = False):
        self.recalculate_whole_talk_statistics(force)
        self.recalculate_speakers_in_talk_statistics(force)
                
    @property
    def needs_automatic_syncing(self):
        return self.subtitle_set.filter(needs_automatic_syncing = True).count() > 0

    # State of the subtitle or its pad
    @property
    def complete(self):
        return self.subtitle_set.filter(complete = False).count() == 0

    @property
    def last_changed_on_amara(self):
        try:
            changed = self.subtitle_set.filter(is_original_lang = True).get().last_changed_on_amara
            for sub in self.subtitle_set.filter(is_original_lang = False):
                if sub.last_changed_on_amara > changed:
                    changed = sub.last_changed_on_amara
            if changed < self.created:
                return None
            else:
                return changed
        except:
            return None

    def get_absolute_url(self):
        return reverse('www.views.talk', args=[str(self.id)])
 
    @property
    def has_statistics(self):
        """ If there are statistics data available for this talk """
        if self.average_spm is None:
            return False
        elif self.average_spm is None:
            return False
        else:
            return True
    
    @property
    def language_of_original_subtitle(self):
        this_subtitles = Subtitle.objects.filter(talk = self, is_original_lang = True)
        if this_subtitles.count() == 0:
            return none
        elif this_subtitles.count() == 1:
            return this_subtitles[0].language
        
    @property
    def has_original_subtitle(self):
        my_subtitles = Subtitle.objects.filter(talk = self, is_original_lang = True)
        if my_subtitles.count() > 0:
            return True
        else:
            return False
    
    @property
    def has_finished_original_subtitle(self):
        my_subtitles = Subtitle.objects.filter(talk = self, is_original_lang = True, complete = True)
        if my_subtitles.count() > 0:
            return True
        else:
            return False

    @property
    def page_sub_titles(self):
        return self.event.page_sub_titles + [self.title]

# States for every subtitle like "complete" or "needs sync"
class States(BasisModell):
    state_de = models.CharField(max_length = 100)
    state_en = models.CharField(max_length = 100)
    def __str__(self):
        return self.state_en

        
# Infos to a subtitle in one language
class Subtitle(BasisModell):
    talk = models.ForeignKey(Talk)
    language = models.ForeignKey(Language)#, to_field = "lang_amara_short")
    is_original_lang = models.BooleanField(default = False) # Read from Amara, not from the Fahrplan!
    revision = models.PositiveSmallIntegerField(default = 0)
    complete = models.BooleanField(default = False)
    state = models.ForeignKey(States, default = 1, blank = True)
    time_processed_transcribing = models.TimeField(default = "00:00", blank = True, verbose_name="")
    time_processed_syncing = models.TimeField(default = "00:00", blank = True, verbose_name="")
    time_quality_check_done = models.TimeField(default = "00:00", blank = True, verbose_name="")
    time_processed_translating = models.TimeField(default = "00:00", blank = True, verbose_name="")
    needs_automatic_syncing = models.BooleanField(default = False)
    blocked = models.BooleanField(default = False)
    needs_sync_to_ftp = models.BooleanField(default = False)
    needs_removal_from_ftp = models.BooleanField(default = False)
    tweet = models.BooleanField(default = False)
    needs_sync_to_YT = models.BooleanField(default = False)
    needs_removal_from_YT = models.BooleanField(default = False)
    tweet_autosync_done = models.BooleanField(default = False)
    #comment = models.TextField(default = "")
    last_changed_on_amara = models.DateTimeField(default = datetime.min, blank = True)

    def _still_in_progress(self, timestamp, state, original_language=True):
        if original_language != self.is_original_lang:
            return False

        return ((timestamp < self.talk.video_duration) or
                (self.state_id == state and timestamp <= self.talk.video_duration))

    @property
    def transcription_in_progress(self):
        return self._still_in_progress(self.time_processed_transcribing, state=2)

    @property
    def syncing_in_progress(self):
        return self._still_in_progress(self.time_processed_syncing, state=5)

    @property
    def quality_check_in_progress(self):
        return self._still_in_progress(self.time_quality_check_done, state=7)

    @property
    def translation_in_progress(self):
        return self._still_in_progress(self.time_processed_translating, state=11, original_language=False)

    @property
    def language_short(self):
        # Workaround because of Klingon / Orignal
        lang = self.language.lang_short_srt
        return self.language.lang_short_srt


# Links from the Fahrplan
class Links(BasisModell):
    talk = models.ForeignKey(Talk, blank = True)
    url = models.URLField(blank = True)
    title = models.CharField(max_length = 200, default = "Link title", blank = True)


# Statistics about Speakers and their words per minute and strokes per minute
# These datasets have to be collected by "hand", they can not be auto created
# speaker, talk, start and end need to be entered manually
class Statistics_Raw_Data(BasisModell):
    speaker = models.ForeignKey(Speaker)
    talk = models.ForeignKey(Talk)
    start = models.TimeField(blank = True, null = True)
    end = models.TimeField(blank = True, null = True)
    time_delta = models.FloatField(blank = True, null = True) # only seconds!
    words = models.IntegerField(blank = True, null = True)
    strokes = models.IntegerField(blank = True, null = True)
    recalculate_statistics = models.BooleanField(default = False)
    
    # Recalculate statistics-data
    @transaction.atomic
    def recalculate(self, force = False):
        # Only calculate if it is forced or if the recalculate flag
        # is set to true
        if force or self.recalculate_statistics:
            values = calculate_subtitle(self.talk, self.start, self.end)
            if values is not None:
                self.time_delta = values["time_delta"]
                self.words = values["words"]
                self.strokes = values["strokes"]
                self.recalculate_statistics = False
                self.save()
                # Set recalculate flags in the connected Statistics_Event module
                Talk.objects.filter(id = self.talk_id).update(recalculate_speakers_statistics = True)
                # Set recalculate flag in the connected Talk_Persons Statistics
                Talk_Persons.objects.filter(talk = self.talk, speaker = self.speaker).update(recalculate_statistics = True)
                # Set recalculate flag in the connected Statistics_Speaker module and also create the database entry
                # Get or create the related Statistics_Speaker database entry.
                # The necessary language is not the language of the talk but the language of the related is_orignal subtitle!
                this_speaker, created = Statistics_Speaker.objects.get_or_create(speaker = self.speaker, language = self.talk.language_of_original_subtitle)
                this_speaker.recalculate_statistics = True
                this_speaker.save()

                
# Speakers can have different Statistic values for different languages they spoke during talks
# This is calculated from the Statistics_Raw_Data which only counts the actual time the speaker speaks
# The subtitle must be finished or in review
class Statistics_Speaker(BasisModell):
    speaker = models.ForeignKey(Speaker)
    language = models.ForeignKey(Language)
    words = models.IntegerField(blank = True, null = True)      # All words from this speaker in this language summed up
    strokes = models.IntegerField(blank = True, null = True)    # All strokes from this speaker in this language summed up
    time_delta = models.FloatField(blank = True, null = True)   # Summed up time deltas from this speaker in this language
    average_wpm = models.FloatField(blank = True, null = True)  # Calculated from words and time delta
    average_spm = models.FloatField(blank = True, null = True)  # Caluclated from strokes and time_delta
    recalculate_statistics = models.BooleanField(default = False)
    
    # Recalculate statistics-data
    @transaction.atomic
    def recalculate(self, force = False):
        # Recalculate absolutely everything
        if force or self.recalculate_statistics:
            # All timeslots form Statistics_Raw_Data which has the same speaker and via the talk also the same language
            # All Subtitles which are the orignal language and the right language
            my_subtitles = Subtitle.objects.filter(is_original_lang = True, language = self.language)
            # Use temporary values
            words = strokes = time_delta = 0            
            # Iterate over all these subtitles and get the right talk_id, then check if it has the right speaker
            for any in my_subtitles:
                talk_persons = Talk_Persons.objects.filter(speaker = self.speaker, talk = any.talk)
                # Just to be careful, first check if anything needs a recalculation first
                for any2 in talk_persons:
                    any2.recalculate()
                # Only sum up if there is something to sum up
                if talk_persons.count() > 0:
                    # Do not add up if None
                    temp = talk_persons.aggregate(Sum("words"))["words__sum"]
                    if temp is not None:
                        words += temp
                    temp = talk_persons.aggregate(Sum("strokes"))["strokes__sum"]
                    if temp is not None:
                        strokes += temp
                    temp = talk_persons.aggregate(Sum("time_delta"))["time_delta__sum"]
                    if temp is not None:
                        time_delta += temp
            # If really everything was none:
            if (words or strokes or time_delta) is None:
                self.words = self.strokes = self.time_delta = self.average_wpm = self.average_spm = None
            else:
                self.words = words
                self.strokes = strokes
                self.time_delta = time_delta
                self.average_wpm = calculate_per_minute(self.words, self.time_delta)
                self.average_spm = calculate_per_minute(self.strokes, self.time_delta)
            self.recalculate_statistics = False
            self.save()

            
# Every Event can have different Statistic values for different languages
# The statistics applies to whole talk-time, not only the speakers time, it
# includes breaks, and Q&A and other stuff
class Statistics_Event(BasisModell):
    event = models.ForeignKey(Event)
    language = models.ForeignKey(Language)
    words = models.IntegerField(blank = True, null = True)  # Summed up from finished / in review whole talks, not only speakers time
    strokes = models.IntegerField(blank = True, null = True)    # Calculated from finished / in review whole talks, not only speakers time
    time_delta = models.FloatField(blank = True, null = True)   # Seconds of all talks from this event which are in review or finished
    average_wpm = models.FloatField(blank = True, null = True)  # Calculated from words and time_delta
    average_spm = models.FloatField(blank = True, null = True)  # Calculated from strokes and time_delta
    recalculate_statistics = models.BooleanField(default = False)
    
    # Recalculate statistics-data
    @transaction.atomic
    def recalculate(self, force = False):
        if force or self.recalculate_statistics:
            # Find all Subtitles connected with this event and this language
            my_subtitles = Subtitle.objects.filter(talk__event = self.event, language = self.language, is_original_lang = True)
            # If nothing is found
            if my_subtitles.count() == 0:
                self.words = None
                self.strokes = None
                self.time_delta = None
                self.average_wpm = None
                self.average_spm = None
            else:
                self.words = my_subtitles.aggregate(Sum("talk__words"))["talk__words__sum"]
                self.strokes = my_subtitles.aggregate(Sum("talk__strokes"))["talk__strokes__sum"]
                self.time_delta = my_subtitles.aggregate(Sum("talk__time_delta"))["talk__time_delta__sum"]
                # If there is not really a finished subtitle in the language
                if (self.words or self.strokes or self.time_delta) is None:
                    self.words = self.strokes = self.time_delta = self.average_wpm = self.average_spm = None
                else:
                    self.average_wpm = calculate_per_minute(self.words, self.time_delta)
                    self.average_spm = calculate_per_minute(self.strokes, self.time_delta)
            self.recalculate_statistics = False
            self.save()

    

# m:n Connection between Talks and Speakers and their Statistics data
class Talk_Persons(BasisModell):
    talk = models.ForeignKey(Talk)
    speaker = models.ForeignKey(Speaker)
    words = models.IntegerField(blank = True, null = True)      # All words from this speaker in this talk summed up
    strokes = models.IntegerField(blank = True, null = True)    # All strokes from this speaker in this talk summed up
    time_delta = models.FloatField(blank = True, null = True)   # Summed up time deltas from this speaker in this talk
    average_wpm = models.FloatField(blank = True, null = True)  # Calculated from words and time delta
    average_spm = models.FloatField(blank = True, null = True)  # Caluclated from strokes and time_delta
    recalculate_statistics = models.BooleanField(default = False)
    
    # Recalculate statistics-data
    @transaction.atomic
    def recalculate(self, force = False):
        # Recalculate absolutely everything
        if force or self.recalculate_statistics:
            # Get statistics_raw for this speaker and this talk and sum it up
            raw_data = Statistics_Raw_Data.objects.filter(talk = self.talk, speaker = self.speaker)
            # If for some reason something needs a recalculation
            for any in raw_data:
                any.recalculate()
            if raw_data.count() == 0:
                self.words = self.strokes = self.time_delta = self.average_wpm = self.average_spm = None
            else:
                self.words = raw_data.aggregate(Sum("words"))["words__sum"]
                self.strokes = raw_data.aggregate(Sum("strokes"))["strokes__sum"]
                self.time_delta = raw_data.aggregate(Sum("time_delta"))["time_delta__sum"]
                if (self.words or self.strokes or self.time_delta) is None:
                    self.words = self.strokes = self.time_delta = self.average_wpm = self.average_spm = None
                else:
                    self.average_wpm = calculate_per_minute(self.words, self.time_delta)
                    self.average_spm = calculate_per_minute(self.strokes, self.time_delta)  
            self.recalculate_statistics = False
            self.save()
    
    @property
    def has_statistics(self):
        if self.average_wpm is not None and self.average_spm is not None:
            return True
        else:
            return False
        