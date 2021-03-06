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

# Unit tests for the frequency module.
from tests import util
import transitfeed


class FrequencyValidationTestCase(util.ValidationTestCase):
    def setUp(self):
        util.ValidationTestCase.setUp(self)
        self.schedule = self.SimpleSchedule()
        trip = transitfeed.Trip()
        trip.route_id = '054C'
        trip.service_id = 'WEEK'
        trip.trip_id = '054C-00'
        trip.trip_headsign = 'via Polish Hill'
        trip.direction_id = '0'
        trip.block_id = None
        trip.shape_id = None
        self.schedule.add_trip_object(trip, self.problems, True)
        self.trip = trip

    def testNonOverlappingPeriods(self):
        headway_period1 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '06:00:00',
                                                 'end_time': '12:00:00',
                                                 'headway_secs': 600,
                                                 })
        headway_period2 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '01:00:00',
                                                 'end_time': '02:00:00',
                                                 'headway_secs': 1200,
                                                 })
        headway_period3 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '04:00:00',
                                                 'end_time': '05:00:00',
                                                 'headway_secs': 1000,
                                                 })
        headway_period4 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '12:00:00',
                                                 'end_time': '19:00:00',
                                                 'headway_secs': 700,
                                                 })

        # expect no problems for non-overlapping periods
        headway_period1.add_to_schedule(self.schedule, self.problems)
        headway_period2.add_to_schedule(self.schedule, self.problems)
        headway_period3.add_to_schedule(self.schedule, self.problems)
        headway_period4.add_to_schedule(self.schedule, self.problems)
        self.trip.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()
        self.trip.clear_frequencies()

    def testOverlappingPeriods(self):
        # overlapping headway periods
        headway_period1 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '00:00:00',
                                                 'end_time': '12:00:00',
                                                 'headway_secs': 600,
                                                 })
        headway_period2 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '06:00:00',
                                                 'end_time': '18:00:00',
                                                 'headway_secs': 1200,
                                                 })
        headway_period1.add_to_schedule(self.schedule, self.problems)
        headway_period2.add_to_schedule(self.schedule, self.problems)
        self.ValidateAndExpectOtherProblem(self.trip)
        self.trip.clear_frequencies()
        self.accumulator.assert_no_more_exceptions()

    def testPeriodWithInvalidTripId(self):
        headway_period1 = transitfeed.Frequency({'trip_id': 'foo',
                                                 'start_time': '00:00:00',
                                                 'end_time': '12:00:00',
                                                 'headway_secs': 600,
                                                 })
        headway_period1.add_to_schedule(self.schedule, self.problems)
        e = self.accumulator.PopException('InvalidValue')
        self.assertEqual('trip_id', e.column_name)
        self.trip.clear_frequencies()

    def testExactTimesStringValueConversion(self):
        # Test that no exact_times converts to 0
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800"})
        frequency.validate_before_add(self.problems)
        self.assertEquals(frequency.get_exact_times(), 0)
        # Test that empty exact_times converts to 0
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": ""})
        frequency.validate_before_add(self.problems)
        self.assertEquals(frequency.get_exact_times(), 0)
        # Test that exact_times "0" converts to 0
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": "0"})
        frequency.validate_before_add(self.problems)
        self.assertEquals(frequency.get_exact_times(), 0)
        # Test that exact_times "1" converts to 1
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": "1"})
        frequency.validate_before_add(self.problems)
        self.assertEquals(frequency.get_exact_times(), 1)
        self.accumulator.assert_no_more_exceptions()

    def testExactTimesAsIntValue(self):
        # Test that exact_times None converts to 0
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": None})
        frequency.validate_before_add(self.problems)
        self.assertEquals(frequency.get_exact_times(), 0)
        # Test that exact_times 0 remains 0
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": 0})
        frequency.validate_before_add(self.problems)
        self.assertEquals(frequency.get_exact_times(), 0)
        # Test that exact_times 1 remains 1
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": 1})
        frequency.validate_before_add(self.problems)
        self.assertEquals(frequency.get_exact_times(), 1)
        self.accumulator.assert_no_more_exceptions()

    def testExactTimesInvalidValues(self):
        # Test that exact_times 15 raises error
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": 15})
        frequency.validate_before_add(self.problems)
        self.accumulator.pop_invalid_value("exact_times")
        self.accumulator.assert_no_more_exceptions()
        # Test that exact_times "yes" raises error
        frequency = transitfeed.Frequency(
            field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                        "end_time": "23:01:00", "headway_secs": "1800",
                        "exact_times": "yes"})
        frequency.validate_before_add(self.problems)
        self.accumulator.pop_invalid_value("exact_times")
        self.accumulator.assert_no_more_exceptions()
