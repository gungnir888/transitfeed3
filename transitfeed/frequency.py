# Copyright (C) 2010 Google Inc.
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
from . import util


class Frequency(GtfsObjectBase):
    """This class represents a period of a trip during which the vehicle travels
    at regular intervals (rather than specifying exact times for each stop)."""

    REQUIRED_FIELD_NAMES = [
        'trip_id',
        'start_time',
        'end_time',
        'headway_secs'
    ]
    FIELD_NAMES = REQUIRED_FIELD_NAMES + ['exact_times']
    _TABLE_NAME = "frequencies"
    exact_times = None

    def __init__(self, field_dict=None):
        self._schedule = None
        if field_dict:
            if isinstance(field_dict, self.__class__):
                for k, v in field_dict.items():
                    self.__dict__[k] = v
            else:
                self.__dict__.update(field_dict)

    def get_start_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time

    def get_trip_id(self):
        return self.trip_id

    def get_headway_secs(self):
        return self.headway_secs

    def get_exact_times(self):
        return self.exact_times

    def validate_exact_times(self, problems):
        if util.is_empty(self.exact_times):
            self.exact_times = 0
            return
        try:
            self.exact_times = int(self.exact_times)
        except (ValueError, TypeError):
            problems.InvalidValue(
                'exact_times', self.exact_times,
                'Should be 0 (no fixed schedule) or 1 (fixed and '
                'regular schedule, shortcut for a repetitive '
                'stop_times file).'
            )
            del self.exact_times
            return
        if self.exact_times not in (0, 1):
            problems.InvalidValue(
                'exact_times', self.exact_times,
                'Should be 0 (no fixed schedule) or 1 (fixed and '
                'regular schedule, shortcut for a repetitive '
                'stop_times file).'
            )

    def validate_before_add(self, problems):
        self.validate_exact_times(problems)
        return True

    def validate_after_add(self, problems):
        return

    def validate(self, loader_problems=None):
        return

    def add_to_schedule(self, schedule=None, problems=None):
        if schedule is None:
            return
        self._schedule = schedule
        try:
            trip = schedule.get_trip(self.trip_id)
        except KeyError:
            problems.InvalidValue('trip_id', self.trip_id)
            return
        trip.add_frequency_object(self, problems)
