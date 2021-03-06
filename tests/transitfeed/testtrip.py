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

# Unit tests for the trip module.
from io import StringIO
from tests import util
import transitfeed


class DuplicateStopSequenceTestCase(util.TestCase):
    def runTest(self):
        accumulator = util.RecordingProblemAccumulator(
            self, ("ExpirationDate", "NoServiceExceptions"))
        problems = transitfeed.ProblemReporter(accumulator)
        schedule = transitfeed.Schedule(problem_reporter=problems)
        schedule.load(util.data_path('duplicate_stop_sequence'),
                      extra_validation=True)
        e = accumulator.pop_exception('InvalidValue')
        self.assertEqual('stop_sequence', e.column_name)
        self.assertEqual(10, e.value)
        accumulator.assert_no_more_exceptions()


class MissingEndpointTimesTestCase(util.TestCase):
    def runTest(self):
        accumulator = util.RecordingProblemAccumulator(
            self, ('ExpirationDate', 'NoServiceExceptions'))
        problems = transitfeed.ProblemReporter(accumulator)
        schedule = transitfeed.Schedule(problem_reporter=problems)
        schedule.load(util.data_path('missing_endpoint_times'),
                      extra_validation=True)
        e = accumulator.pop_invalid_value('arrival_time')
        self.assertEqual('', e.value)
        e = accumulator.pop_invalid_value('departure_time')
        self.assertEqual('', e.value)


class TripMemoryZipTestCase(util.MemoryZipTestCase):
    def assertLoadAndCheckExtraValues(self, schedule_file):
        """Load file-like schedule_file and check for extra trip columns."""
        load_problems = util.get_test_failure_problem_reporter(
            self, ("ExpirationDate", "UnrecognizedColumn"))
        loaded_schedule = transitfeed.Loader(schedule_file,
                                             loader_problems=load_problems,
                                             extra_validation=True).load()
        self.assertEqual("foo", loaded_schedule.get_trip("AB1")["t_foo"])
        self.assertEqual("", loaded_schedule.get_trip("AB2")["t_foo"])
        self.assertEqual("", loaded_schedule.get_trip("AB1")["n_foo"])
        self.assertEqual("bar", loaded_schedule.get_trip("AB2")["n_foo"])
        # Uncomment the following lines to print the string in testExtraFileColumn
        # print repr(zipfile.ZipFile(schedule_file).read("trips.txt"))
        # self.fail()

    def testExtraObjectAttribute(self):
        """Extra columns added to an object are preserved when writing."""
        schedule = self.MakeLoaderAndLoad()
        # Add an attribute to an existing trip
        trip1 = schedule.get_trip("AB1")
        trip1.t_foo = "foo"
        # Make a copy of trip_id=AB1 and add an attribute before AddTripObject
        trip2 = transitfeed.Trip(field_dict=trip1)
        trip2.trip_id = "AB2"
        trip2.t_foo = ""
        trip2.n_foo = "bar"
        schedule.add_trip_object(trip2)
        trip2.add_stop_time(stop=schedule.get_stop("BULLFROG"), stop_time="09:00:00")
        trip2.add_stop_time(stop=schedule.get_stop("STAGECOACH"), stop_time="09:30:00")
        saved_schedule_file = StringIO()
        schedule.write_google_transit_feed(saved_schedule_file)
        self.accumulator.assert_no_more_exceptions()

        self.assertLoadAndCheckExtraValues(saved_schedule_file)

    def testExtraFileColumn(self):
        """Extra columns loaded from a file are preserved when writing."""
        # Uncomment the code in assertLoadAndCheckExtraValues to generate this
        # string.
        self.SetArchiveContents(
            "trips.txt",
            "route_id,service_id,trip_id,t_foo,n_foo\n"
            "AB,FULLW,AB1,foo,\n"
            "AB,FULLW,AB2,,bar\n")
        self.AppendToArchiveContents(
            "stop_times.txt",
            "AB2,09:00:00,09:00:00,BULLFROG,1\n"
            "AB2,09:30:00,09:30:00,STAGECOACH,2\n")
        load1_problems = util.get_test_failure_problem_reporter(
            self, ("ExpirationDate", "UnrecognizedColumn"))
        schedule = self.MakeLoaderAndLoad(loader_problems=load1_problems)
        saved_schedule_file = StringIO()
        schedule.write_google_transit_feed(saved_schedule_file)

        self.assertLoadAndCheckExtraValues(saved_schedule_file)


class TripValidationTestCase(util.ValidationTestCase):
    def runTest(self):
        trip = transitfeed.Trip()
        repr(trip)  # shouldn't crash

        schedule = self.SimpleSchedule()
        trip = transitfeed.Trip()
        repr(trip)  # shouldn't crash

        trip = transitfeed.Trip()
        trip.trip_headsign = '\xBA\xDF\x0D'  # Not valid ascii or utf8
        repr(trip)  # shouldn't crash

        trip.route_id = '054C'
        trip.service_id = 'WEEK'
        trip.trip_id = '054C-00'
        trip.trip_headsign = 'via Polish Hill'
        trip.trip_short_name = 'X12'
        trip.direction_id = '0'
        trip.block_id = None
        trip.shape_id = None
        trip.bikes_allowed = '1'
        trip.wheelchair_accessible = '2'
        trip.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()
        repr(trip)  # shouldn't crash

        # missing route ID
        trip.route_id = None
        self.ValidateAndExpectMissingValue(trip, 'route_id')
        trip.route_id = '054C'

        # missing service ID
        trip.service_id = None
        self.ValidateAndExpectMissingValue(trip, 'service_id')
        trip.service_id = 'WEEK'

        # missing trip ID
        trip.trip_id = None
        self.ValidateAndExpectMissingValue(trip, 'trip_id')
        trip.trip_id = '054C-00'

        # invalid direction ID
        trip.direction_id = 'NORTH'
        self.ValidateAndExpectInvalidValue(trip, 'direction_id')
        trip.direction_id = '0'

        # invalid bikes_allowed
        trip.bikes_allowed = '3'
        self.ValidateAndExpectInvalidValue(trip, 'bikes_allowed')
        trip.bikes_allowed = None

        # invalid wheelchair_accessible
        trip.wheelchair_accessible = '3'
        self.ValidateAndExpectInvalidValue(trip, 'wheelchair_accessible')
        trip.wheelchair_accessible = None

        # AddTripObject validates that route_id, service_id, .... are found in the
        # schedule. The Validate calls made by self.Expect... above can't make this
        # check because trip is not in a schedule.
        trip.route_id = '054C-notfound'
        schedule.add_trip_object(trip, self.problems, True)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertEqual('route_id', e.column_name)
        self.accumulator.assert_no_more_exceptions()
        trip.route_id = '054C'

        # Make sure calling Trip.Validate validates that route_id and service_id
        # are found in the schedule.
        trip.service_id = 'WEEK-notfound'
        trip.validate(self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertEqual('service_id', e.column_name)
        self.accumulator.assert_no_more_exceptions()
        trip.service_id = 'WEEK'

        trip.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()

        # expect no problems for non-overlapping periods
        trip.add_frequency("06:00:00", "12:00:00", 600)
        trip.add_frequency("01:00:00", "02:00:00", 1200)
        trip.add_frequency("04:00:00", "05:00:00", 1000)
        trip.add_frequency("12:00:00", "19:00:00", 700)
        trip.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()
        trip.clear_frequencies()

        # overlapping headway periods
        trip.add_frequency("00:00:00", "12:00:00", 600)
        trip.add_frequency("06:00:00", "18:00:00", 1200)
        self.ValidateAndExpectOtherProblem(trip)
        trip.clear_frequencies()
        trip.add_frequency("12:00:00", "20:00:00", 600)
        trip.add_frequency("06:00:00", "18:00:00", 1200)
        self.ValidateAndExpectOtherProblem(trip)
        trip.clear_frequencies()
        trip.add_frequency("06:00:00", "12:00:00", 600)
        trip.add_frequency("00:00:00", "25:00:00", 1200)
        self.ValidateAndExpectOtherProblem(trip)
        trip.clear_frequencies()
        trip.add_frequency("00:00:00", "20:00:00", 600)
        trip.add_frequency("06:00:00", "18:00:00", 1200)
        self.ValidateAndExpectOtherProblem(trip)
        trip.clear_frequencies()
        self.accumulator.assert_no_more_exceptions()


class TripSequenceValidationTestCase(util.ValidationTestCase):
    def runTest(self):
        schedule = self.SimpleSchedule()
        # Make a new trip without any stop times
        trip = schedule.get_route("054C").add_trip(trip_id="054C-00")
        stop1 = schedule.get_stop('stop1')
        stop2 = schedule.get_stop('stop2')
        stop3 = schedule.get_stop('stop3')
        stoptime1 = transitfeed.StopTime(self.problems, stop1,
                                         stop_time='12:00:00', stop_sequence=1)
        stoptime2 = transitfeed.StopTime(self.problems, stop2,
                                         stop_time='11:30:00', stop_sequence=2)
        stoptime3 = transitfeed.StopTime(self.problems, stop3,
                                         stop_time='12:15:00', stop_sequence=3)
        trip._add_stop_time_object_unordered(stoptime1, schedule)
        trip._add_stop_time_object_unordered(stoptime2, schedule)
        trip._add_stop_time_object_unordered(stoptime3, schedule)
        trip.validate(self.problems)
        e = self.accumulator.pop_exception('OtherProblem')
        self.assertTrue(e.format_problem().find('Timetravel detected') != -1)
        self.assertTrue(e.format_problem().find('number 2 in trip 054C-00') != -1)
        self.accumulator.assert_no_more_exceptions()


class TripServiceIDValidationTestCase(util.ValidationTestCase):
    def runTest(self):
        schedule = self.SimpleSchedule()
        trip1 = transitfeed.Trip()
        trip1.route_id = "054C"
        trip1.service_id = "WEEKDAY"
        trip1.trip_id = "054C_WEEK"
        self.ExpectInvalidValueInClosure(column_name="service_id",
                                         value="WEEKDAY",
                                         c=lambda: schedule.add_trip_object(trip1,
                                                                            validate=True))


class TripDistanceFromStopToShapeValidationTestCase(util.ValidationTestCase):
    def runTest(self):
        schedule = self.SimpleSchedule()
        stop1 = schedule.stops["stop1"]
        stop2 = schedule.stops["stop2"]
        stop3 = schedule.stops["stop3"]

        # Set shape_dist_traveled
        trip = schedule.trips["CITY1"]
        trip.clear_stop_times()
        trip.add_stop_time(stop1, stop_time="12:00:00", shape_dist_traveled=0)
        trip.add_stop_time(stop2, stop_time="12:00:45", shape_dist_traveled=500)
        trip.add_stop_time(stop3, stop_time="12:02:30", shape_dist_traveled=1500)
        trip.shape_id = "shape1"

        # Add a valid shape for the trip to the current schedule.
        shape = transitfeed.Shape("shape1")
        shape.add_point(48.2, 1.00, 0)
        shape.add_point(48.2, 1.01, 500)
        shape.add_point(48.2, 1.03, 1500)
        shape.max_distance = 1500
        schedule.add_shape_object(shape)

        # The schedule should validate with no problems.
        self.ExpectNoProblems(schedule)

        # Delete a stop latitude. This should not crash validation.
        stop1.stop_lat = None
        self.ValidateAndExpectMissingValue(schedule, "stop_lat")


class TripHasStopTimeValidationTestCase(util.ValidationTestCase):
    def runTest(self):
        schedule = self.SimpleSchedule()
        trip = schedule.get_route("054C").add_trip(trip_id="054C-00")

        # We should get an OtherProblem here because the trip has no stops.
        self.ValidateAndExpectOtherProblem(schedule)

        # It should trigger a TYPE_ERROR if there are frequencies for the trip
        # but no stops
        trip.add_frequency("01:00:00", "12:00:00", 600)
        schedule.validate(self.problems)
        self.accumulator.pop_exception('OtherProblem')  # pop first warning
        e = self.accumulator.pop_exception('OtherProblem')  # pop frequency error
        self.assertTrue(e.format_problem().find('Frequencies defined, but') != -1)
        self.assertTrue(e.format_problem().find('given in trip 054C-00') != -1)
        self.assertEquals(transitfeed.TYPE_ERROR, e.type)
        self.accumulator.assert_no_more_exceptions()
        trip.clear_frequencies()

        # Add a stop, but with only one stop passengers have nowhere to exit!
        stop = transitfeed.Stop(36.425288, -117.133162, "Demo Stop 1", "STOP1")
        schedule.add_stop_object(stop)
        trip.add_stop_time(stop, arrival_time="5:11:00", departure_time="5:12:00")
        self.ValidateAndExpectOtherProblem(schedule)

        # Add another stop, and then validation should be happy.
        stop = transitfeed.Stop(36.424288, -117.133142, "Demo Stop 2", "STOP2")
        schedule.add_stop_object(stop)
        trip.add_stop_time(stop, arrival_time="5:15:00", departure_time="5:16:00")
        schedule.validate(self.problems)

        trip.add_stop_time(stop, stop_time="05:20:00")
        trip.add_stop_time(stop, stop_time="05:22:00")

        # Last stop must always have a time
        trip.add_stop_time(stop, arrival_secs=None, departure_secs=None)
        self.ExpectInvalidValueInClosure(
            'arrival_time', c=lambda: trip.get_end_time(loader_problems=self.problems))


class ShapeDistTraveledOfStopTimeValidationTestCase(util.ValidationTestCase):
    def runTest(self):
        schedule = self.SimpleSchedule()

        shape = transitfeed.Shape("shape_1")
        shape.add_point(36.425288, -117.133162, 0)
        shape.add_point(36.424288, -117.133142, 1)
        schedule.add_shape_object(shape)

        trip = schedule.get_route("054C").add_trip(trip_id="054C-00")
        trip.shape_id = "shape_1"

        stop = transitfeed.Stop(36.425288, -117.133162, "Demo Stop 1", "STOP1")
        schedule.add_stop_object(stop)
        trip.add_stop_time(stop, arrival_time="5:11:00", departure_time="5:12:00",
                           stop_sequence=0, shape_dist_traveled=0)
        stop = transitfeed.Stop(36.424288, -117.133142, "Demo Stop 2", "STOP2")
        schedule.add_stop_object(stop)
        trip.add_stop_time(stop, arrival_time="5:15:00", departure_time="5:16:00",
                           stop_sequence=1, shape_dist_traveled=1)

        stop = transitfeed.Stop(36.423288, -117.133122, "Demo Stop 3", "STOP3")
        schedule.add_stop_object(stop)
        trip.add_stop_time(stop, arrival_time="5:18:00", departure_time="5:19:00",
                           stop_sequence=2, shape_dist_traveled=2)
        self.accumulator.assert_no_more_exceptions()
        schedule.validate(self.problems)
        e = self.accumulator.pop_exception('OtherProblem')
        self.assertMatchesRegex('shape_dist_traveled=2', e.format_problem())
        self.accumulator.assert_no_more_exceptions()

        # Error if the distance decreases.
        shape.add_point(36.421288, -117.133132, 2)
        stop = transitfeed.Stop(36.421288, -117.133122, "Demo Stop 4", "STOP4")
        schedule.add_stop_object(stop)
        stoptime = transitfeed.StopTime(self.problems, stop,
                                        arrival_time="5:29:00",
                                        departure_time="5:29:00", stop_sequence=3,
                                        shape_dist_traveled=1.7)
        trip.add_stop_time_object(stoptime, schedule=schedule)
        self.accumulator.assert_no_more_exceptions()
        schedule.validate(self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('stop STOP4 has', e.format_problem())
        self.assertMatchesRegex('shape_dist_traveled=1.7', e.format_problem())
        self.assertMatchesRegex('distance was 2.0.', e.format_problem())
        self.assertEqual(e.type, transitfeed.TYPE_ERROR)
        self.accumulator.assert_no_more_exceptions()

        # Warning if distance remains the same between two stop_times
        stoptime.shape_dist_traveled = 2.0
        trip.replace_stop_time_object(stoptime, schedule=schedule)
        schedule.validate(self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('stop STOP4 has', e.format_problem())
        self.assertMatchesRegex('shape_dist_traveled=2.0', e.format_problem())
        self.assertMatchesRegex('distance was 2.0.', e.format_problem())
        self.assertEqual(e.type, transitfeed.TYPE_WARNING)
        self.accumulator.assert_no_more_exceptions()


class StopMatchWithShapeTestCase(util.ValidationTestCase):
    def runTest(self):
        schedule = self.SimpleSchedule()

        shape = transitfeed.Shape("shape_1")
        shape.add_point(36.425288, -117.133162, 0)
        shape.add_point(36.424288, -117.143142, 1)
        schedule.add_shape_object(shape)

        trip = schedule.get_route("054C").add_trip(trip_id="054C-00")
        trip.shape_id = "shape_1"

        # Stop 1 is only 600 meters away from shape, which is allowed.
        stop = transitfeed.Stop(36.425288, -117.139162, "Demo Stop 1", "STOP1")
        schedule.add_stop_object(stop)
        trip.add_stop_time(stop, arrival_time="5:11:00", departure_time="5:12:00",
                           stop_sequence=0, shape_dist_traveled=0)
        # Stop 2 is more than 1000 meters away from shape, which is not allowed.
        stop = transitfeed.Stop(36.424288, -117.158142, "Demo Stop 2", "STOP2")
        schedule.add_stop_object(stop)
        trip.add_stop_time(stop, arrival_time="5:15:00", departure_time="5:16:00",
                           stop_sequence=1, shape_dist_traveled=1)

        schedule.validate(self.problems)
        e = self.accumulator.pop_exception('StopTooFarFromShapeWithDistTraveled')
        self.assertTrue(e.format_problem().find('Demo Stop 2') != -1)
        self.assertTrue(e.format_problem().find('1344 meters away') != -1)
        self.accumulator.assert_no_more_exceptions()


class TripAddStopTimeObjectTestCase(util.ValidationTestCase):
    def runTest(self):
        schedule = transitfeed.Schedule(problem_reporter=self.problems)
        schedule.add_agency("\xc8\x8b Fly Agency", "http://iflyagency.com",
                            "America/Los_Angeles")
        schedule.get_default_service_period().set_date_has_service('20070101')
        stop1 = schedule.add_stop(lng=140, lat=48.2, name="Stop 1")
        stop2 = schedule.add_stop(lng=140.001, lat=48.201, name="Stop 2")
        route = schedule.add_route("B", "Beta", "Bus")
        trip = route.add_trip(schedule, "bus trip")
        trip.add_stop_time_object(transitfeed.StopTime(self.problems, stop1,
                                                       arrival_secs=10,
                                                       departure_secs=10),
                                  schedule=schedule, loader_problems=self.problems)
        trip.add_stop_time_object(transitfeed.StopTime(self.problems, stop2,
                                                       arrival_secs=20,
                                                       departure_secs=20),
                                  schedule=schedule, loader_problems=self.problems)
        # TODO: Factor out checks or use mock problems object
        self.ExpectOtherProblemInClosure(lambda:
                                         trip.add_stop_time_object(transitfeed.StopTime(self.problems, stop1,
                                                                                        arrival_secs=15,
                                                                                        departure_secs=15),
                                                                   schedule=schedule, loader_problems=self.problems))
        trip.add_stop_time_object(transitfeed.StopTime(self.problems, stop1),
                                  schedule=schedule, loader_problems=self.problems)
        self.ExpectOtherProblemInClosure(lambda:
                                         trip.add_stop_time_object(transitfeed.StopTime(self.problems, stop1,
                                                                                        arrival_secs=15,
                                                                                        departure_secs=15),
                                                                   schedule=schedule, loader_problems=self.problems))
        trip.add_stop_time_object(transitfeed.StopTime(self.problems, stop1,
                                                       arrival_secs=30,
                                                       departure_secs=30),
                                  schedule=schedule, loader_problems=self.problems)
        self.accumulator.assert_no_more_exceptions()


class TripReplaceStopTimeObjectTestCase(util.TestCase):
    def runTest(self):
        schedule = transitfeed.Schedule()
        schedule.add_agency("\xc8\x8b Fly Agency", "http://iflyagency.com", "America/Los_Angeles")
        schedule.get_default_service_period().set_date_has_service('20070101')
        stop1 = schedule.add_stop(lng=140, lat=48.2, name="Stop 1")
        route = schedule.add_route("B", "Beta", "Bus")
        trip = route.add_trip(schedule, "bus trip")
        stoptime = transitfeed.StopTime(transitfeed.default_problem_reporter, stop1,
                                        arrival_secs=10,
                                        departure_secs=10)
        trip.add_stop_time_object(stoptime, schedule=schedule)
        stoptime.departure_secs = 20
        trip.replace_stop_time_object(stoptime, schedule=schedule)
        stoptimes = trip.get_stop_times()
        self.assertEqual(len(stoptimes), 1)
        self.assertEqual(stoptimes[0].departure_secs, 20)

        unknown_stop = schedule.add_stop(lng=140, lat=48.2, name="unknown")
        unknown_stoptime = transitfeed.StopTime(
            transitfeed.default_problem_reporter, unknown_stop,
            arrival_secs=10,
            departure_secs=10)
        unknown_stoptime.stop_sequence = 5
        # Attempting to replace a non-existent StopTime raises an error
        self.assertRaises(transitfeed.Error, trip.ReplaceStopTimeObject,
                          unknown_stoptime, schedule=schedule)


class SingleTripTestCase(util.TestCase):
    def setUp(self):
        schedule = transitfeed.Schedule(
            problem_reporter=util.ExceptionProblemReporterNoExpiration())
        schedule.new_default_agency(agency_name="Test Agency",
                                    agency_url="http://example.com",
                                    agency_timezone="America/Los_Angeles")
        route = schedule.add_route(short_name="54C", long_name="Polish Hill",
                                   route_type=3)

        service_period = schedule.get_default_service_period()
        service_period.set_date_has_service("20070101")

        trip = route.add_trip(schedule, 'via Polish Hill')

        stop1 = schedule.add_stop(36.425288, -117.133162, "Demo Stop 1")
        stop2 = schedule.add_stop(36.424288, -117.133142, "Demo Stop 2")

        self.schedule = schedule
        self.trip = trip
        self.stop1 = stop1
        self.stop2 = stop2


class TripStopTimeAccessorsTestCase(SingleTripTestCase):
    def runTest(self):
        self.trip.add_stop_time(
            self.stop1, arrival_time="5:11:00", departure_time="5:12:00")
        self.trip.add_stop_time(
            self.stop2, arrival_time="5:15:00", departure_time="5:16:00")

        # Add some more stop times and test GetEndTime does the correct thing
        self.assertEqual(transitfeed.format_seconds_since_midnight(
            self.trip.get_start_time()), "05:11:00")
        self.assertEqual(transitfeed.format_seconds_since_midnight(
            self.trip.get_end_time()), "05:16:00")

        self.trip.add_stop_time(self.stop1, stop_time="05:20:00")
        self.assertEqual(
            transitfeed.format_seconds_since_midnight(self.trip.get_end_time()),
            "05:20:00")

        self.trip.add_stop_time(self.stop2, stop_time="05:22:00")
        self.assertEqual(
            transitfeed.format_seconds_since_midnight(self.trip.get_end_time()),
            "05:22:00")


class TripGetStopTimesTestCase(SingleTripTestCase):
    def runTest(self):
        self.trip.add_stop_time(
            self.stop1,
            arrival_time="5:11:00",
            departure_time="5:12:00",
            stop_headsign='Stop Headsign',
            pickup_type=1,
            drop_off_type=2,
            shape_dist_traveled=100,
            timepoint=1)
        self.trip.add_stop_time(
            self.stop2, arrival_time="5:15:00", departure_time="5:16:00")

        stop_times = self.trip.get_stop_times()
        self.assertEquals(2, len(stop_times))
        st = stop_times[0]
        self.assertEquals(self.stop1.stop_id, st.stop_id)
        self.assertEquals('05:11:00', st.arrival_time)
        self.assertEquals('05:12:00', st.departure_time)
        self.assertEquals(u'Stop Headsign', st.stop_headsign)
        self.assertEquals(1, st.pickup_type)
        self.assertEquals(2, st.drop_off_type)
        self.assertEquals(100.0, st.shape_dist_traveled)
        self.assertEquals(1, st.timepoint)

        st = stop_times[1]
        self.assertEquals(self.stop2.stop_id, st.stop_id)
        self.assertEquals('05:15:00', st.arrival_time)
        self.assertEquals('05:16:00', st.departure_time)

        tuples = self.trip.get_stop_times_tuples()
        self.assertEquals(2, len(tuples))
        self.assertEqual(
            (self.trip.trip_id, "05:11:00", "05:12:00", self.stop1.stop_id,
             1, u'Stop Headsign', 1, 2, 100.0, 1),
            tuples[0])
        self.assertEqual(
            (self.trip.trip_id, "05:15:00", "05:16:00", self.stop2.stop_id,
             2, '', '', '', '', ''),
            tuples[1])


class TripClearStopTimesTestCase(util.TestCase):
    def runTest(self):
        schedule = transitfeed.Schedule(
            problem_reporter=util.ExceptionProblemReporterNoExpiration())
        schedule.new_default_agency(agency_name="Test Agency",
                                    agency_timezone="America/Los_Angeles")
        route = schedule.add_route(short_name="54C", long_name="Hill", route_type=3)
        schedule.get_default_service_period().set_date_has_service("20070101")
        stop1 = schedule.add_stop(36, -117.1, "Demo Stop 1")
        stop2 = schedule.add_stop(36, -117.2, "Demo Stop 2")
        stop3 = schedule.add_stop(36, -117.3, "Demo Stop 3")

        trip = route.add_trip(schedule, "via Polish Hill")
        trip.clear_stop_times()
        self.assertFalse(trip.get_stop_times())
        trip.add_stop_time(stop1, stop_time="5:11:00")
        self.assertTrue(trip.get_stop_times())
        trip.clear_stop_times()
        self.assertFalse(trip.get_stop_times())
        trip.add_stop_time(stop3, stop_time="4:00:00")  # Can insert earlier time
        trip.add_stop_time(stop2, stop_time="4:15:00")
        trip.add_stop_time(stop1, stop_time="4:21:00")
        old_stop_times = trip.get_stop_times()
        self.assertTrue(old_stop_times)
        trip.clear_stop_times()
        self.assertFalse(trip.get_stop_times())
        for st in old_stop_times:
            trip.add_stop_time_object(st)
        self.assertEqual(trip.get_start_time(), 4 * 3600)
        self.assertEqual(trip.get_end_time(), 4 * 3600 + 21 * 60)


class InvalidRouteAgencyTestCase(util.LoadTestCase):
    def runTest(self):
        self.load('invalid_route_agency')
        self.accumulator.pop_invalid_value("agency_id", "routes.txt")
        self.accumulator.pop_invalid_value("route_id", "trips.txt")
        self.accumulator.assert_no_more_exceptions()


class InvalidAgencyIdsTestCase(util.LoadTestCase):
    def runTest(self):
        self.load('invalid_agency_ids')
        self.accumulator.pop_exception('OtherProblem')
        self.accumulator.assert_no_more_exceptions()


class AddStopTimeParametersTestCase(util.TestCase):
    def runTest(self):
        problem_reporter = util.get_test_failure_problem_reporter(self)
        schedule = transitfeed.Schedule(problem_reporter=problem_reporter)
        route = schedule.add_route(short_name="10", long_name="", route_type="Bus")
        stop = schedule.add_stop(40, -128, "My stop")
        # Stop must be added to schedule so that the call
        # AddStopTime -> AddStopTimeObject -> GetStopTimes -> GetStop can work
        trip = transitfeed.Trip()
        trip.route_id = route.route_id
        trip.service_id = schedule.get_default_service_period().service_id
        trip.trip_id = "SAMPLE_TRIP"
        schedule.add_trip_object(trip)

        # First stop must have time
        trip.add_stop_time(stop, arrival_secs=300, departure_secs=360)
        trip.add_stop_time(stop)
        trip.add_stop_time(stop, arrival_time="00:07:00", departure_time="00:07:30")
        trip.validate(problem_reporter)


class AddFrequencyValidationTestCase(util.ValidationTestCase):
    def ExpectInvalidValue(self, start_time, end_time, headway,
                           column_name, value):
        try:
            trip = transitfeed.Trip()
            trip.add_frequency(start_time, end_time, headway)
            self.fail("Expected InvalidValue error on %s" % column_name)
        except transitfeed.InvalidValue as e:
            self.assertEqual(column_name, e.column_name)
            self.assertEqual(value, e.value)
            self.assertEqual(0, len(trip.get_frequency_tuples()))

    def ExpectMissingValue(self, start_time, end_time, headway, column_name):
        trip = transitfeed.Trip()
        try:
            trip.add_frequency(start_time, end_time, headway)
            self.fail("Expected MissingValue error on %s" % column_name)
        except transitfeed.MissingValue as e:
            self.assertEqual(column_name, e.column_name)
            self.assertEqual(0, len(trip.get_frequency_tuples()))

    def runTest(self):
        # these should work fine
        trip = transitfeed.Trip()
        trip.trip_id = "SAMPLE_ID"
        trip.add_frequency(0, 50, 1200)
        trip.add_frequency("01:00:00", "02:00:00", "600")
        trip.add_frequency(u"02:00:00", u"03:00:00", u"1800")
        headways = trip.get_frequency_tuples()
        self.assertEqual(3, len(headways))
        self.assertEqual((0, 50, 1200, 0), headways[0])
        self.assertEqual((3600, 7200, 600, 0), headways[1])
        self.assertEqual((7200, 10800, 1800, 0), headways[2])
        self.assertEqual([("SAMPLE_ID", "00:00:00", "00:00:50", "1200", "0"),
                          ("SAMPLE_ID", "01:00:00", "02:00:00", "600", "0"),
                          ("SAMPLE_ID", "02:00:00", "03:00:00", "1800", "0")],
                         trip.get_frequency_output_tuples())

        # now test invalid input
        self.ExpectMissingValue(None, 50, 1200, "start_time")
        self.ExpectMissingValue("", 50, 1200, "start_time")
        self.ExpectInvalidValue("midnight", 50, 1200, "start_time",
                                "midnight")
        self.ExpectInvalidValue(-50, 50, 1200, "start_time", -50)
        self.ExpectMissingValue(0, None, 1200, "end_time")
        self.ExpectMissingValue(0, "", 1200, "end_time")
        self.ExpectInvalidValue(0, "noon", 1200, "end_time", "noon")
        self.ExpectInvalidValue(0, -50, 1200, "end_time", -50)
        self.ExpectMissingValue(0, 600, 0, "headway_secs")
        self.ExpectMissingValue(0, 600, None, "headway_secs")
        self.ExpectMissingValue(0, 600, "", "headway_secs")
        self.ExpectInvalidValue(0, 600, "test", "headway_secs", "test")
        self.ExpectInvalidValue(0, 600, -60, "headway_secs", -60)
        self.ExpectInvalidValue(0, 0, 1200, "end_time", 0)
        self.ExpectInvalidValue("12:00:00", "06:00:00", 1200, "end_time",
                                21600)


class GetTripTimeTestCase(util.TestCase):
    """Test for GetStopTimeTrips and GetTimeInterpolatedStops"""

    def setUp(self):
        problems = util.get_test_failure_problem_reporter(self)
        schedule = transitfeed.Schedule(problem_reporter=problems)
        self.schedule = schedule
        schedule.add_agency("Agency", "http://iflyagency.com",
                            "America/Los_Angeles")
        service_period = schedule.get_default_service_period()
        service_period.set_date_has_service('20070101')
        self.stop1 = schedule.add_stop(lng=140.01, lat=0, name="140.01,0")
        self.stop2 = schedule.add_stop(lng=140.02, lat=0, name="140.02,0")
        self.stop3 = schedule.add_stop(lng=140.03, lat=0, name="140.03,0")
        self.stop4 = schedule.add_stop(lng=140.04, lat=0, name="140.04,0")
        self.stop5 = schedule.add_stop(lng=140.05, lat=0, name="140.05,0")
        self.route1 = schedule.add_route("1", "One", "Bus")

        self.trip1 = self.route1.add_trip(schedule, "trip 1", trip_id='trip1')
        self.trip1.add_stop_time(self.stop1, schedule=schedule, departure_secs=100,
                                 arrival_secs=100)
        self.trip1.add_stop_time(self.stop2, schedule=schedule)
        self.trip1.add_stop_time(self.stop3, schedule=schedule)
        # loop back to stop2 to test that interpolated stops work ok even when
        # a stop between timepoints is further from the timepoint than the
        # preceding
        self.trip1.add_stop_time(self.stop2, schedule=schedule)
        self.trip1.add_stop_time(self.stop4, schedule=schedule, departure_secs=400,
                                 arrival_secs=400)

        self.trip2 = self.route1.add_trip(schedule, "trip 2", trip_id='trip2')
        self.trip2.add_stop_time(self.stop2, schedule=schedule, departure_secs=500,
                                 arrival_secs=500)
        self.trip2.AddStopTime(self.stop3, schedule=schedule, departure_secs=600,
                               arrival_secs=600)
        self.trip2.AddStopTime(self.stop4, schedule=schedule, departure_secs=700,
                               arrival_secs=700)
        self.trip2.AddStopTime(self.stop3, schedule=schedule, departure_secs=800,
                               arrival_secs=800)

        self.trip3 = self.route1.add_trip(schedule, "trip 3", trip_id='trip3')

    def testGetTimeInterpolatedStops(self):
        rv = self.trip1.get_time_interpolated_stops()
        self.assertEqual(5, len(rv))
        (secs, stoptimes, istimepoints) = tuple(zip(*rv))

        self.assertEqual((100, 160, 220, 280, 400), secs)
        self.assertEqual(("140.01,0", "140.02,0", "140.03,0", "140.02,0", "140.04,0"),
                         tuple([st.stop.stop_name for st in stoptimes]))
        self.assertEqual((True, False, False, False, True), istimepoints)

        self.assertEqual([], self.trip3.get_time_interpolated_stops())

    def testGetTimeInterpolatedStopsUntimedEnd(self):
        self.trip2.AddStopTime(self.stop3, schedule=self.schedule)
        self.assertRaises(ValueError, self.trip2.GetTimeInterpolatedStops)

    def testGetTimeInterpolatedStopsUntimedStart(self):
        # Temporarily replace the problem reporter so that adding the first
        # StopTime without a time doesn't throw an exception.
        old_problems = self.schedule.problem_reporter
        self.schedule.problem_reporter = util.get_test_failure_problem_reporter(
            self, ("OtherProblem",))
        self.trip3.AddStopTime(self.stop3, schedule=self.schedule)
        self.schedule.problem_reporter = old_problems
        self.trip3.AddStopTime(self.stop2, schedule=self.schedule,
                               departure_secs=500, arrival_secs=500)
        self.assertRaises(ValueError, self.trip3.GetTimeInterpolatedStops)

    def testGetTimeInterpolatedStopsSingleStopTime(self):
        self.trip3.AddStopTime(self.stop3, schedule=self.schedule,
                               departure_secs=500, arrival_secs=500)
        rv = self.trip3.get_time_interpolated_stops()
        self.assertEqual(1, len(rv))
        self.assertEqual(500, rv[0][0])
        self.assertEqual(True, rv[0][2])

    def testGetStopTimeTrips(self):
        stopa = self.schedule.get_nearest_stops(lon=140.03, lat=0)[0]
        self.assertEqual("140.03,0", stopa.stop_name)  # Got stop3?
        rv = stopa.get_stop_time_trips(self.schedule)
        self.assertEqual(3, len(rv))
        (secs, trip_index, istimepoints) = tuple(zip(*rv))
        self.assertEqual((220, 600, 800), secs)
        self.assertEqual(("trip1", "trip2", "trip2"), tuple([ti[0].trip_id for ti in trip_index]))
        self.assertEqual((2, 1, 3), tuple([ti[1] for ti in trip_index]))
        self.assertEqual((False, True, True), istimepoints)

    def testStopTripIndex(self):
        trip_index = self.stop3.trip_index
        trip_ids = [t.trip_id for t, i in trip_index]
        self.assertEqual(["trip1", "trip2", "trip2"], trip_ids)
        self.assertEqual([2, 1, 3], [i for t, i in trip_index])

    def testGetTrips(self):
        self.assertEqual(
            set([t.trip_id for t in self.stop1.get_trips(self.schedule)]),
            {self.trip1.trip_id})
        self.assertEqual(
            set([t.trip_id for t in self.stop2.get_trips(self.schedule)]),
            {self.trip1.trip_id, self.trip2.trip_id})
        self.assertEqual(
            set([t.trip_id for t in self.stop3.get_trips(self.schedule)]),
            {self.trip1.trip_id, self.trip2.trip_id})
        self.assertEqual(
            set([t.trip_id for t in self.stop4.get_trips(self.schedule)]),
            {self.trip1.trip_id, self.trip2.trip_id})
        self.assertEqual(
            set([t.trip_id for t in self.stop5.get_trips(self.schedule)]),
            set())


class GetFrequencyTimesTestCase(util.TestCase):
    """Test for GetFrequencyStartTimes and GetFrequencyStopTimes"""

    def setUp(self):
        problems = util.get_test_failure_problem_reporter(self)
        schedule = transitfeed.Schedule(problem_reporter=problems)
        self.schedule = schedule
        schedule.add_agency("Agency", "http://iflyagency.com",
                            "America/Los_Angeles")
        service_period = schedule.get_default_service_period()
        service_period.set_start_date("20080101")
        service_period.set_end_date("20090101")
        service_period.set_weekday_service(True)
        self.stop1 = schedule.add_stop(lng=140.01, lat=0, name="140.01,0")
        self.stop2 = schedule.add_stop(lng=140.02, lat=0, name="140.02,0")
        self.stop3 = schedule.add_stop(lng=140.03, lat=0, name="140.03,0")
        self.stop4 = schedule.add_stop(lng=140.04, lat=0, name="140.04,0")
        self.stop5 = schedule.add_stop(lng=140.05, lat=0, name="140.05,0")
        self.route1 = schedule.add_route("1", "One", "Bus")

        self.trip1 = self.route1.add_trip(schedule, "trip 1", trip_id="trip1")
        # add different types of stop times
        self.trip1.AddStopTime(self.stop1, arrival_time="17:00:00",
                               departure_time="17:01:00")  # both arrival and departure time
        self.trip1.AddStopTime(self.stop2, schedule=schedule)  # non timed
        self.trip1.AddStopTime(self.stop3, stop_time="17:45:00")  # only stop_time

        # add headways starting before the trip
        self.trip1.add_frequency("16:00:00", "18:00:00", 1800)  # each 30 min
        self.trip1.add_frequency("18:00:00", "20:00:00", 2700)  # each 45 min

    def testGetFrequencyStartTimes(self):
        start_times = self.trip1.get_frequency_start_times()
        self.assertEqual(
            ["16:00:00", "16:30:00", "17:00:00", "17:30:00",
             "18:00:00", "18:45:00", "19:30:00"],
            [transitfeed.format_seconds_since_midnight(secs) for secs in start_times])
        # GetHeadwayStartTimes is deprecated, but should still return the same
        # result as GetFrequencyStartTimes
        self.assertEqual(start_times,
                         self.trip1.get_frequency_start_times())

    def testGetFrequencyStopTimes(self):
        stoptimes_list = self.trip1.get_frequency_stop_times()
        arrival_secs = []
        departure_secs = []
        for stoptimes in stoptimes_list:
            arrival_secs.append([st.arrival_secs for st in stoptimes])
            departure_secs.append([st.departure_secs for st in stoptimes])

        # GetHeadwayStopTimes is deprecated, but should still return the same
        # result as GetFrequencyStopTimes
        # StopTimes are instantiated as they're read from the DB so they can't be
        # compared directly, but checking {arrival,departure}_secs should be enough
        # to catch most errors.
        self.trip1.get_frequency_stop_times()
        headway_arrival_secs = []
        headway_departure_secs = []
        for stoptimes in stoptimes_list:
            headway_arrival_secs.append([st.arrival_secs for st in stoptimes])
            headway_departure_secs.append([st.departure_secs for st in stoptimes])
        self.assertEqual(arrival_secs, headway_arrival_secs)
        self.assertEqual(departure_secs, headway_departure_secs)

        self.assertEqual(([57600, None, 60300], [59400, None, 62100], [61200, None, 63900],
                          [63000, None, 65700], [64800, None, 67500], [67500, None, 70200],
                          [70200, None, 72900]),
                         tuple(arrival_secs))
        self.assertEqual(([57660, None, 60300], [59460, None, 62100], [61260, None, 63900],
                          [63060, None, 65700], [64860, None, 67500], [67560, None, 70200],
                          [70260, None, 72900]),
                         tuple(departure_secs))

        # test if stoptimes are created with same parameters than the ones from the original trip
        stoptimes = self.trip1.get_stop_times()
        for stoptimes_clone in stoptimes_list:
            self.assertEqual(len(stoptimes_clone), len(stoptimes))
            for st_clone, st in zip(stoptimes_clone, stoptimes):
                for name in st.__slots__:
                    if name not in ('arrival_secs', 'departure_secs'):
                        self.assertEqual(getattr(st, name), getattr(st_clone, name))
