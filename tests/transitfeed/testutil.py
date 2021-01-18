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

# Unit tests for transitfeed/util.py

import datetime
import re
from io import StringIO
from urllib.error import HTTPError, URLError

import tests.util as test_util
from transitfeed import problems
from transitfeed.problems import ProblemReporter
from transitfeed import stop
from transitfeed import util
from transitfeed import version
import unittest
import urllib.request


class ColorLuminanceTestCase(test_util.TestCase):
    def runTest(self):
        self.assertEqual(util.color_luminance('000000'), 0,
                         "ColorLuminance('000000') should be zero")
        self.assertEqual(util.color_luminance('FFFFFF'), 255,
                         "ColorLuminance('FFFFFF') should be 255")
        rgb_msg = "ColorLuminance('RRGGBB') should be 0.299*<Red> + 0.587*<Green> + 0.114*<Blue>"
        decimal_places_tested = 8
        self.assertAlmostEqual(util.color_luminance('640000'), 29.9,
                               decimal_places_tested, rgb_msg)
        self.assertAlmostEqual(util.color_luminance('006400'), 58.7,
                               decimal_places_tested, rgb_msg)
        self.assertAlmostEqual(util.color_luminance('000064'), 11.4,
                               decimal_places_tested, rgb_msg)
        self.assertAlmostEqual(util.color_luminance('1171B3'),
                               0.299 * 17 + 0.587 * 113 + 0.114 * 179,
                               decimal_places_tested, rgb_msg)


class FindUniqueIdTestCase(test_util.TestCase):
    def test_simple(self):
        d = {}
        for i in range(0, 5):
            d[util.find_unique_id(d)] = 1
        k = list(d.keys())
        k.sort()
        self.assertEqual(('0', '1', '2', '3', '4'), tuple(k))

    def test_AvoidCollision(self):
        d = {'1': 1, util.find_unique_id({'1': 1}): 1}
        self.assertEqual(2, len(d))
        self.assertFalse('3' in d, "Ops, next statement should add something to d")
        d['3'] = None
        d[util.find_unique_id(d)] = 1
        self.assertEqual(4, len(d))


class ApproximateDistanceBetweenStopsTestCase(test_util.TestCase):
    def testEquator(self):
        stop1 = stop.Stop(lat=0, lng=100, name='Stop one', stop_id='1')
        stop2 = stop.Stop(lat=0.01, lng=100.01, name='Stop two', stop_id='2')
        self.assertAlmostEqual(
            util.approximate_distance_between_stops(stop1, stop2),
            1570, -1)  # Compare first 3 digits

    def testWhati(self):
        stop1 = stop.Stop(lat=63.1, lng=-117.2, name='whati one', stop_id='1')
        stop2 = stop.Stop(lat=63.102, lng=-117.201, name='whati two', stop_id='2')
        self.assertAlmostEqual(
            util.approximate_distance_between_stops(stop1, stop2),
            228, 0)


class TimeConversionHelpersTestCase(test_util.TestCase):
    def testTimeToSecondsSinceMidnight(self):
        self.assertEqual(util.time_to_seconds_since_midnight("01:02:03"), 3723)
        self.assertEqual(util.time_to_seconds_since_midnight("00:00:00"), 0)
        self.assertEqual(util.time_to_seconds_since_midnight("25:24:23"), 91463)
        try:
            util.time_to_seconds_since_midnight("10:15:00am")
        except problems.Error:
            pass  # expected
        else:
            self.fail("Should have thrown Error")

    def testFormatSecondsSinceMidnight(self):
        self.assertEqual(util.format_seconds_since_midnight(3723), "01:02:03")
        self.assertEqual(util.format_seconds_since_midnight(0), "00:00:00")
        self.assertEqual(util.format_seconds_since_midnight(91463), "25:24:23")

    def testdate_string_to_date_object(self):
        self.assertEqual(util.date_string_to_date_object("20080901"),
                         datetime.date(2008, 9, 1))
        self.assertEqual(util.date_string_to_date_object("20080841"), None)


class ValidationUtilsTestCase(test_util.TestCase):
    def testIsValidURL(self):
        self.assertTrue(util.is_valid_url("http://www.example.com"))
        self.assertFalse(util.is_valid_url("ftp://www.example.com"))
        self.assertFalse(util.is_valid_url(""))

    def testValidateURL(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems_in_test = ProblemReporter(accumulator)
        self.assertTrue(util.validate_url("", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertTrue(util.validate_url("http://www.example.com", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertFalse(util.validate_url("ftp://www.example.com", "col", problems_in_test))
        accumulator.pop_invalid_value("col")
        accumulator.assert_no_more_exceptions()

    def testIsValidHexColor(self):
        self.assertTrue(util.is_valid_hex_color("33FF00"))
        self.assertFalse(util.is_valid_hex_color("blue"))
        self.assertFalse(util.is_valid_hex_color(""))

    def testIsValidLanguageCode(self):
        self.assertTrue(util.is_valid_language_code("de"))
        self.assertFalse(util.is_valid_language_code("Swiss German"))
        self.assertFalse(util.is_valid_language_code(""))

    def testValidateLanguageCode(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems_in_test = ProblemReporter(accumulator)
        self.assertTrue(util.validate_language_code("", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertTrue(util.validate_language_code("de", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertFalse(util.validate_language_code("Swiss German", "col", problems_in_test))
        accumulator.pop_invalid_value("col")
        accumulator.assert_no_more_exceptions()

    def testIsValidTimezone(self):
        self.assertTrue(util.is_valid_timezone("America/Los_Angeles"))
        self.assertFalse(util.is_valid_timezone("Switzerland/Wil"))
        self.assertFalse(util.is_valid_timezone(""))

    def testValidateTimezone(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems_in_test = ProblemReporter(accumulator)
        self.assertTrue(util.validate_timezone("", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertTrue(util.validate_timezone("America/Los_Angeles", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertFalse(util.validate_timezone("Switzerland/Wil", "col", problems_in_test))
        accumulator.pop_invalid_value("col")
        accumulator.assert_no_more_exceptions()

    def testis_valid_date(self):
        self.assertTrue(util.is_valid_date("20100801"))
        self.assertFalse(util.is_valid_date("20100732"))
        self.assertFalse(util.is_valid_date(""))

    def testvalidate_date(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems_in_test = ProblemReporter(accumulator)
        self.assertTrue(util.validate_date("", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertTrue(util.validate_date("20100801", "col", problems_in_test))
        accumulator.assert_no_more_exceptions()
        self.assertFalse(util.validate_date("20100732", "col", problems_in_test))
        accumulator.pop_invalid_value("col")
        accumulator.assert_no_more_exceptions()


class FloatStringToFloatTestCase(test_util.TestCase):
    def runTest(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems_in_test = ProblemReporter(accumulator)

        self.assertAlmostEqual(0, util.float_string_to_float("0", problems_in_test))
        self.assertAlmostEqual(0, util.float_string_to_float(u"0", problems_in_test))
        self.assertAlmostEqual(1, util.float_string_to_float("1", problems_in_test))
        self.assertAlmostEqual(1, util.float_string_to_float("1.00000", problems_in_test))
        self.assertAlmostEqual(1.5, util.float_string_to_float("1.500", problems_in_test))
        self.assertAlmostEqual(-2, util.float_string_to_float("-2.0", problems_in_test))
        self.assertAlmostEqual(-2.5, util.float_string_to_float("-2.5", problems_in_test))
        self.assertRaises(ValueError, util.float_string_to_float, ".", problems_in_test)
        self.assertRaises(ValueError, util.float_string_to_float, "0x20", problems_in_test)
        self.assertRaises(ValueError, util.float_string_to_float, "-0x20", problems_in_test)
        self.assertRaises(ValueError, util.float_string_to_float, "0b10", problems_in_test)

        # These should issue a warning, but otherwise parse successfully
        self.assertAlmostEqual(0.001, util.float_string_to_float("1E-3", problems_in_test))
        accumulator.pop_exception("InvalidFloatValue")
        self.assertAlmostEqual(0.001, util.float_string_to_float(".001", problems_in_test))
        accumulator.pop_exception("InvalidFloatValue")
        self.assertAlmostEqual(-0.001, util.float_string_to_float("-.001", problems_in_test))
        accumulator.pop_exception("InvalidFloatValue")
        self.assertAlmostEqual(0, util.float_string_to_float("0.", problems_in_test))
        accumulator.pop_exception("InvalidFloatValue")
        accumulator.assert_no_more_exceptions()


class NonNegIntStringToIntTestCase(test_util.TestCase):
    def runTest(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems_in_test = ProblemReporter(accumulator)

        self.assertEqual(0, util.non_neg_int_string_to_int("0", problems_in_test))
        self.assertEqual(0, util.non_neg_int_string_to_int(u"0", problems_in_test))
        self.assertEqual(1, util.non_neg_int_string_to_int("1", problems_in_test))
        self.assertEqual(2, util.non_neg_int_string_to_int("2", problems_in_test))
        self.assertEqual(10, util.non_neg_int_string_to_int("10", problems_in_test))
        self.assertEqual(1234567890123456789, util.non_neg_int_string_to_int("1234567890123456789", problems_in_test))
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "", problems_in_test)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "-1", problems_in_test)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "0x1", problems_in_test)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "1.0", problems_in_test)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "1e1", problems_in_test)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "0x20", problems_in_test)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "0b10", problems_in_test)
        self.assertRaises(TypeError, util.non_neg_int_string_to_int, 1, problems_in_test)
        self.assertRaises(TypeError, util.non_neg_int_string_to_int, None, problems_in_test)

        # These should issue a warning, but otherwise parse successfully
        self.assertEqual(1, util.non_neg_int_string_to_int("+1", problems_in_test))
        accumulator.PopException("InvalidNonNegativeIntegerValue")
        self.assertEqual(1, util.non_neg_int_string_to_int("01", problems_in_test))
        accumulator.PopException("InvalidNonNegativeIntegerValue")
        self.assertEqual(0, util.non_neg_int_string_to_int("00", problems_in_test))
        accumulator.PopException("InvalidNonNegativeIntegerValue")
        accumulator.assert_no_more_exceptions()


class CheckVersionTestCase(test_util.TempDirTestCaseBase):
    def setUp(self):
        self.orig_urlopen = urllib.request.urlopen
        self.mock = MockURLOpen()
        self.accumulator = test_util.RecordingProblemAccumulator(self)
        self.problems = ProblemReporter(self.accumulator)

    def tearDown(self):
        self.mock = None
        urllib.request.urlopen = self.orig_urlopen

    def testAssignedDifferentVersion(self):
        util.check_version(self.problems, '100.100.100')
        e = self.accumulator.PopException('NewVersionAvailable')
        self.assertEqual(e.version, '100.100.100')
        self.assertEqual(e.url, 'https://github.com/google/transitfeed')
        self.accumulator.assert_no_more_exceptions()

    def testAssignedSameVersion(self):
        util.check_version(self.problems, version.__version__)
        self.accumulator.assert_no_more_exceptions()

    def testGetCorrectReturns(self):
        urllib.request.urlopen = self.mock.mocked_connect_success
        util.check_version(self.problems)
        self.accumulator.PopException('NewVersionAvailable')

    def testPageNotFound(self):
        urllib.request.urlopen = self.mock.mocked_page_not_found
        util.check_version(self.problems)
        e = self.accumulator.PopException('OtherProblem')
        self.assertTrue(re.search(r'we failed to reach', e.description))
        self.assertTrue(re.search(r'Reason: Not Found \[404\]', e.description))

    def testConnectionTimeOut(self):
        urllib.request.urlopen = self.mock.mocked_connection_time_out
        util.check_version(self.problems)
        e = self.accumulator.PopException('OtherProblem')
        self.assertTrue(re.search(r'we failed to reach', e.description))
        self.assertTrue(re.search(r'Reason: Connection timed', e.description))

    def testGetAddrInfoFailed(self):
        urllib.request.urlopen = self.mock.mocked_get_addr_info_failed
        util.check_version(self.problems)
        e = self.accumulator.PopException('OtherProblem')
        self.assertTrue(re.search(r'we failed to reach', e.description))
        self.assertTrue(re.search(r'Reason: Getaddrinfo failed', e.description))

    def testEmptyIsReturned(self):
        urllib.request.urlopen = self.mock.mocked_empty_is_returned
        util.check_version(self.problems)
        e = self.accumulator.PopException('OtherProblem')
        self.assertTrue(re.search(r'we had trouble parsing', e.description))


class MockURLOpen:
    """Pretend to be a urllib.request.urlopen suitable for testing."""

    def mocked_connect_success(self, request):
        return StringIO('latest_version=100.0.1')

    def mocked_page_not_found(self, request):
        raise HTTPError(request.get_full_url(), 404, 'Not Found',
                        request.header_items(), None)

    def mocked_connection_time_out(self, request):
        raise URLError('Connection timed out')

    def mocked_get_addr_info_failed(self, request):
        raise URLError('Getaddrinfo failed')

    def mocked_empty_is_returned(self, request):
        return StringIO()


if __name__ == '__main__':
    unittest.main()
