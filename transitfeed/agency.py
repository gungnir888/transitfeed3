# Copyright (C) 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .gtfsobjectbase import GtfsObjectBase
from .problems import default_problem_reporter
from . import util


class Agency(GtfsObjectBase):
    """Represents an agency in a schedule.

    Callers may assign arbitrary values to instance attributes. __init__ makes no
    attempt at validating the attributes. Call validate() to check that
    attributes are valid and the agency object is consistent with itself.

    Attributes:
      All attributes are strings.
    """
    REQUIRED_FIELD_NAMES = [
        'agency_name',
        'agency_url',
        'agency_timezone'
    ]
    FIELD_NAMES = REQUIRED_FIELD_NAMES + [
        'agency_id',
        'agency_lang',
        'agency_phone',
        'agency_fare_url',
        'agency_email'
    ]
    DEPRECATED_FIELD_NAMES = [
        ('agency_ticket_url', 'agency_fare_url')
    ]
    _TABLE_NAME = 'agency'

    def __init__(self, name=None, url=None, timezone=None, idd=None, email=None,
                 field_dict=None, lang=None, **kwargs):
        """Initialize a new Agency object.

        Args:
          field_dict: A dictionary mapping attribute name to unicode string
          name: a string, ignored when field_dict is present
          url: a string, ignored when field_dict is present
          timezone: a string, ignored when field_dict is present
          idd: a string, ignored when field_dict is present
          kwargs: arbitrary keyword arguments may be used to add attributes to the
            new object, ignored when field_dict is present
        """
        self._schedule = None

        if not field_dict:
            if name:
                kwargs['agency_name'] = name
            if url:
                kwargs['agency_url'] = url
            if timezone:
                kwargs['agency_timezone'] = timezone
            if idd:
                kwargs['agency_id'] = id
            if lang:
                kwargs['agency_lang'] = lang
            if email:
                kwargs['agency_email'] = email
            field_dict = kwargs

        self.__dict__.update(field_dict)

    def validate_agency_url(self, problems):
        return util.validate_url(self.agency_url, 'agency_url', problems)

    def validate_agency_lang(self, problems):
        return util.validate_language_code(self.agency_lang, 'agency_lang',
                                               problems)

    def validate_agency_timezone(self, problems):
        return util.validate_timezone(self.agency_timezone, 'agency_timezone',
                                          problems)

    def validate_agency_fare_url(self, problems):
        return util.validate_url(
            self.agency_fare_url, 'agency_fare_url', problems)

    def validate_agency_email(self, problems):
        return util.validate_email(self.agency_email, 'agency_email', problems)

    def validate(self, problems=default_problem_reporter):
        """Validate attribute values and this object's internal consistency.

        Returns:
          True iff all validation checks passed.
        """
        found_problem = False
        found_problem = ((not util.validate_required_fields_are_not_empty(
            self, self.REQUIRED_FIELD_NAMES, problems))
                         or found_problem)
        found_problem = self.validate_agency_url(problems) or found_problem
        found_problem = self.validate_agency_lang(problems) or found_problem
        found_problem = self.validate_agency_timezone(problems) or found_problem
        found_problem = self.validate_agency_fare_url(problems) or found_problem
        found_problem = self.validate_agency_email(problems) or found_problem

        return not found_problem

    def validate_before_add(self, problems):
        return True

    def validate_after_add(self, problems):
        self.validate(problems)

    def add_to_schedule(self, schedule, problems):
        schedule.add_agency_object(self, problems)
