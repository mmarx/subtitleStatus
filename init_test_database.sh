#!/bin/sh

python manage.py migrate
python manage.py createsuperuser --username admin --email root@localhost
python manage.py loaddata 32c3
python import_languages.py
python update_events_xml_schedule_import.py
