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

# Unit tests for the loader module.
import re
from io import StringIO
import tempfile
from tests import util
import transitfeed
import zipfile
import zlib


class UnrecognizedColumnRecorder(transitfeed.ProblemReporter):
    """Keeps track of unrecognized column errors."""

    def __init__(self, test_case):
        super().__init__(accumulator=None)
        self.accumulator = util.RecordingProblemAccumulator(
            test_case, ignore_types=("ExpirationDate",)
        )
        self.column_errors = []

    def unrecognized_column(self, file_name, column_name, context=None, problem_type=transitfeed.TYPE_WARNING):
        self.column_errors.append((file_name, column_name))


# ensure that there are no exceptions when attempting to load
# (so that the validator won't crash)
class NoExceptionTestCase(util.RedirectStdOutTestCaseBase):

    @staticmethod
    def runTest():
        for feed in util.get_data_path_contents():
            loader = transitfeed.Loader(util.data_path(feed),
                                        loader_problems=transitfeed.ProblemReporter(),
                                        extra_validation=True)
            schedule = loader.load()
            schedule.validate()


class EndOfLineCheckerTestCase(util.TestCase):
    def setUp(self):
        self.accumulator = util.RecordingProblemAccumulator(self, "ExpirationDate")
        self.problems = transitfeed.ProblemReporter(self.accumulator)

    def RunEndOfLineChecker(self, end_of_line_checker):
        # Iterating using for calls end_of_line_checker.next() until a
        # StopIteration is raised. EndOfLineChecker does the final check for a mix
        # of CR LF and LF ends just before raising StopIteration.
        for line in end_of_line_checker:
            pass

    def testInvalidLineEnd(self):
        f = transitfeed.EndOfLineChecker(StringIO("line1\r\r\nline2"),
                                         "<StringIO>",
                                         self.problems)
        self.RunEndOfLineChecker(f)
        e = self.accumulator.pop_exception("InvalidLineEnd")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 1)
        self.assertEqual(e.bad_line_end, r"\r\r\n")
        self.accumulator.assert_no_more_exceptions()

    def testInvalidLineEndToo(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1\nline2\r\nline3\r\r\r\n"),
            "<StringIO>", self.problems)
        self.RunEndOfLineChecker(f)
        e = self.accumulator.pop_exception("InvalidLineEnd")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 3)
        self.assertEqual(e.bad_line_end, r"\r\r\r\n")
        e = self.accumulator.pop_exception("OtherProblem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertTrue(e.description.find("consistent line end") != -1)
        self.accumulator.assert_no_more_exceptions()

    def testEmbeddedCr(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1\rline1b"),
            "<StringIO>", self.problems)
        self.RunEndOfLineChecker(f)
        e = self.accumulator.pop_exception("OtherProblem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 1)
        self.assertEqual(e.format_problem(),
                         "Line contains ASCII Carriage Return 0x0D, \\r")
        self.accumulator.assert_no_more_exceptions()

    def testEmbeddedUtf8NextLine(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1b\xc2\x85"),
            "<StringIO>", self.problems)
        self.RunEndOfLineChecker(f)
        e = self.accumulator.pop_exception("OtherProblem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 1)
        self.assertEqual(e.format_problem(),
                         "Line contains Unicode NEXT LINE SEPARATOR U+0085")
        self.accumulator.assert_no_more_exceptions()

    def testEndOfLineMix(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1\nline2\r\nline3\nline4"),
            "<StringIO>", self.problems)
        self.RunEndOfLineChecker(f)
        e = self.accumulator.pop_exception("OtherProblem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.format_problem(),
                         "Found 1 CR LF \"\\r\\n\" line end (line 2) and "
                         "2 LF \"\\n\" line ends (lines 1, 3). A file must use a "
                         "consistent line end.")
        self.accumulator.assert_no_more_exceptions()

    def testEndOfLineManyMix(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("1\n2\n3\n4\n5\n6\n7\r\n8\r\n9\r\n10\r\n11\r\n"),
            "<StringIO>", self.problems)
        self.RunEndOfLineChecker(f)
        e = self.accumulator.pop_exception("OtherProblem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.format_problem(),
                         "Found 5 CR LF \"\\r\\n\" line ends (lines 7, 8, 9, 10, "
                         "11) and 6 LF \"\\n\" line ends (lines 1, 2, 3, 4, 5, "
                         "...). A file must use a consistent line end.")
        self.accumulator.assert_no_more_exceptions()

    def testLoad(self):
        loader = transitfeed.Loader(
            util.data_path("bad_eol.zip"),
            loader_problems=self.problems,
            extra_validation=True)
        loader.load()

        e = self.accumulator.pop_exception("OtherProblem")
        self.assertEqual(e.file_name, "calendar.txt")
        self.assertTrue(re.search(
            r"Found 1 CR LF.* \(line 2\) and 2 LF .*\(lines 1, 3\)",
            e.format_problem()))

        e = self.accumulator.pop_exception("InvalidLineEnd")
        self.assertEqual(e.file_name, "routes.txt")
        self.assertEqual(e.row_num, 5)
        self.assertTrue(e.format_problem().find(r"\r\r\n") != -1)

        e = self.accumulator.pop_exception("OtherProblem")
        self.assertEqual(e.file_name, "trips.txt")
        self.assertEqual(e.row_num, 1)
        self.assertTrue(re.search(
            r"contains ASCII Form Feed",
            e.format_problem()))
        # TODO(Tom): avoid this duplicate error for the same issue
        e = self.accumulator.pop_exception("CsvSyntax")
        self.assertEqual(e.row_num, 1)
        self.assertTrue(re.search(
            r"header row should not contain any space char",
            e.format_problem()))

        self.accumulator.assert_no_more_exceptions()


class LoadFromZipTestCase(util.TestCase):
    def runTest(self):
        loader = transitfeed.Loader(
            util.data_path('good_feed.zip'),
            loader_problems=util.get_test_failure_problem_reporter(self),
            extra_validation=True)
        loader.load()

        # now try using Schedule.Load
        schedule = transitfeed.Schedule(
            problem_reporter=util.ExceptionProblemReporterNoExpiration())
        schedule.load(util.data_path('good_feed.zip'), extra_validation=True)


class LoadAndRewriteFromZipTestCase(util.TestCase):

    @staticmethod
    def runTest():
        schedule = transitfeed.Schedule(
            problem_reporter=util.ExceptionProblemReporterNoExpiration())
        schedule.load(util.data_path('good_feed.zip'), extra_validation=True)

        # Finally see if write crashes
        schedule.write_google_transit_feed(tempfile.TemporaryFile())


class BasicMemoryZipTestCase(util.MemoryZipTestCase):
    def runTest(self):
        self.MakeLoaderAndLoad()
        self.accumulator.assert_no_more_exceptions()


class ZipCompressionTestCase(util.MemoryZipTestCase):
    def runTest(self):
        schedule = self.MakeLoaderAndLoad()
        self.zip.close()
        write_output = StringIO()
        schedule.write_google_transit_feed(write_output)
        recompressed_zip = zlib.compress(write_output.getvalue().encode())
        write_size = len(write_output.getvalue())
        recompressed_zip_size = len(recompressed_zip)
        # If zlib can compress write_output it probably wasn't compressed
        self.assertFalse(
            recompressed_zip_size < write_size * 0.60,
            "Are you sure WriteGoogleTransitFeed wrote a compressed zip? "
            "Orginial size: %d  recompressed: %d" %
            (write_size, recompressed_zip_size))


class LoadUnknownFileInZipTestCase(util.MemoryZipTestCase):
    def runTest(self):
        self.SetArchiveContents(
            "stpos.txt",
            "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
            "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
            "STATION,Airport,36.868446,-116.784582,1,\n"
            "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
            "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
        self.MakeLoaderAndLoad()
        e = self.accumulator.PopException('UnknownFile')
        self.assertEquals('stpos.txt', e.file_name)
        self.accumulator.assert_no_more_exceptions()


class TabDelimitedTestCase(util.MemoryZipTestCase):
    def runTest(self):
        # Create an extremely corrupt file by replacing each comma with a tab,
        # ignoring csv quoting.
        for arc_name in self.GetArchiveNames():
            contents = self.GetArchiveContents(arc_name)
            self.SetArchiveContents(arc_name, contents.replace(",", "\t"))
        self.MakeLoaderAndLoad()
        # Don't call self.accumulator.assert_no_more_exceptions() because there are
        # lots of problems but I only care that the validator doesn't crash. In the
        # magical future the validator will stop when the csv is obviously hosed.


class LoadFromDirectoryTestCase(util.TestCase):
    def runTest(self):
        loader = transitfeed.Loader(
            util.data_path('good_feed'),
            loader_problems=util.get_test_failure_problem_reporter(self),
            extra_validation=True)
        loader.load()


class LoadUnknownFeedTestCase(util.TestCase):
    def runTest(self):
        feed_name = util.data_path('unknown_feed')
        loader = transitfeed.Loader(
            feed_name,
            loader_problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True)
        try:
            loader.load()
            self.fail('FeedNotFound exception expected')
        except transitfeed.FeedNotFound as e:
            self.assertEqual(feed_name, e.feed_name)


class LoadUnknownFormatTestCase(util.TestCase):
    def runTest(self):
        feed_name = util.data_path('unknown_format.zip')
        loader = transitfeed.Loader(
            feed_name,
            loader_problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True)
        try:
            loader.load()
            self.fail('UnknownFormat exception expected')
        except transitfeed.UnknownFormat as e:
            self.assertEqual(feed_name, e.feed_name)


class LoadUnrecognizedColumnsTestCase(util.TestCase):
    def runTest(self):
        problems = UnrecognizedColumnRecorder(self)
        loader = transitfeed.Loader(util.data_path('unrecognized_columns'),
                                    loader_problems=problems)
        loader.load()
        found_errors = set(problems.column_errors)
        expected_errors = {('agency.txt', 'agency_lange'), ('stops.txt', 'stop_uri'),
                           ('routes.txt', 'Route_Text_Color'), ('calendar.txt', 'leap_day'),
                           ('calendar_dates.txt', 'leap_day'), ('trips.txt', 'sharpe_id'),
                           ('stop_times.txt', 'shapedisttraveled'), ('stop_times.txt', 'drop_off_time'),
                           ('fare_attributes.txt', 'transfer_time'), ('fare_rules.txt', 'source_id'),
                           ('frequencies.txt', 'superfluous'), ('transfers.txt', 'to_stop')}

        # Now make sure we got the unrecognized column errors that we expected.
        not_expected = found_errors.difference(expected_errors)
        self.failIf(bool(not_expected), 'unexpected errors: %s' % str(not_expected))
        not_found = expected_errors.difference(found_errors)
        self.failIf(bool(not_found), 'expected but not found: %s' % str(not_found))


class LoadExtraCellValidationTestCase(util.LoadTestCase):
    """Check that the validation detects too many cells in a row."""

    def runTest(self):
        self.load('extra_row_cells')
        e = self.accumulator.PopException("OtherProblem")
        self.assertEquals("routes.txt", e.file_name)
        self.assertEquals(4, e.row_num)
        self.accumulator.assert_no_more_exceptions()


class LoadMissingCellValidationTestCase(util.LoadTestCase):
    """Check that the validation detects missing cells in a row."""

    def runTest(self):
        self.load('missing_row_cells')
        e = self.accumulator.PopException("OtherProblem")
        self.assertEquals("routes.txt", e.file_name)
        self.assertEquals(4, e.row_num)
        self.accumulator.assert_no_more_exceptions()


class LoadUnknownFileTestCase(util.TestCase):
    """Check that the validation detects unknown files."""

    def runTest(self):
        feed_name = util.data_path('unknown_file')
        self.accumulator = util.RecordingProblemAccumulator(self, "ExpirationDate")
        self.problems = transitfeed.ProblemReporter(self.accumulator)
        loader = transitfeed.Loader(
            feed_name,
            loader_problems=self.problems,
            extra_validation=True)
        loader.load()
        e = self.accumulator.PopException('UnknownFile')
        self.assertEqual('frecuencias.txt', e.file_name)
        self.accumulator.assert_no_more_exceptions()


class LoadMissingAgencyTestCase(util.LoadTestCase):
    def runTest(self):
        self.ExpectMissingFile('missing_agency', 'agency.txt')


class LoadMissingStopsTestCase(util.LoadTestCase):
    def runTest(self):
        self.ExpectMissingFile('missing_stops', 'stops.txt')


class LoadMissingRoutesTestCase(util.LoadTestCase):
    def runTest(self):
        self.ExpectMissingFile('missing_routes', 'routes.txt')


class LoadMissingTripsTestCase(util.LoadTestCase):
    def runTest(self):
        self.ExpectMissingFile('missing_trips', 'trips.txt')


class LoadMissingStopTimesTestCase(util.LoadTestCase):
    def runTest(self):
        self.ExpectMissingFile('missing_stop_times', 'stop_times.txt')


class LoadMissingCalendarTestCase(util.LoadTestCase):
    def runTest(self):
        self.ExpectMissingFile('missing_calendar', 'calendar.txt')


class EmptyFileTestCase(util.TestCase):
    def runTest(self):
        loader = transitfeed.Loader(
            util.data_path('empty_file'),
            loader_problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True
        )
        try:
            loader.load()
            self.fail('EmptyFile exception expected')
        except transitfeed.EmptyFile as e:
            self.assertEqual('agency.txt', e.file_name)


class MissingColumnTestCase(util.TestCase):
    def runTest(self):
        loader = transitfeed.Loader(
            util.data_path('missing_column'),
            loader_problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True)
        try:
            loader.load()
            self.fail('MissingColumn exception expected')
        except transitfeed.MissingColumn as e:
            self.assertEqual('agency.txt', e.file_name)
            self.assertEqual('agency_name', e.column_name)


class LoadUTF8BOMTestCase(util.TestCase):
    def runTest(self):
        loader = transitfeed.Loader(
            util.data_path('utf8bom'),
            loader_problems=util.get_test_failure_problem_reporter(self),
            extra_validation=True)
        loader.load()


class LoadUTF16TestCase(util.TestCase):
    def runTest(self):
        # utf16 generated by `recode utf8..utf16 *'
        accumulator = transitfeed.ExceptionProblemAccumulator()
        problem_reporter = transitfeed.ProblemReporter(accumulator)
        loader = transitfeed.Loader(
            util.data_path('utf16'),
            loader_problems=problem_reporter,
            extra_validation=True)
        try:
            loader.load()
            # TODO: make sure processing proceeds beyond the problem
            self.fail('FileFormat exception expected')
        except transitfeed.FileFormat as e:
            # make sure these don't raise an exception
            self.assertTrue(re.search(r'encoded in utf-16', e.format_problem()))
            e.format_context()


class BadUtf8TestCase(util.LoadTestCase):
    def runTest(self):
        self.load('bad_utf8')
        self.accumulator.PopException("UnrecognizedColumn")
        self.accumulator.pop_invalid_value("agency_name", "agency.txt")
        self.accumulator.pop_invalid_value("route_long_name", "routes.txt")
        self.accumulator.pop_invalid_value("route_short_name", "routes.txt")
        self.accumulator.pop_invalid_value("stop_headsign", "stop_times.txt")
        self.accumulator.pop_invalid_value("stop_name", "stops.txt")
        self.accumulator.pop_invalid_value("trip_headsign", "trips.txt")
        self.accumulator.assert_no_more_exceptions()


class LoadNullTestCase(util.TestCase):
    def runTest(self):
        accumulator = transitfeed.ExceptionProblemAccumulator()
        problem_reporter = transitfeed.ProblemReporter(accumulator)
        loader = transitfeed.Loader(
            util.data_path('contains_null'),
            loader_problems=problem_reporter,
            extra_validation=True)
        try:
            loader.load()
            self.fail('FileFormat exception expected')
        except transitfeed.FileFormat as e:
            self.assertTrue(re.search(r'contains a null', e.format_problem()))
            # make sure these don't raise an exception
            e.format_context()


class CsvDictTestCase(util.TestCase):
    def setUp(self):
        self.accumulator = util.RecordingProblemAccumulator(self)
        self.problems = transitfeed.ProblemReporter(self.accumulator)
        self.zip = zipfile.ZipFile(StringIO(), 'a')
        self.loader = transitfeed.Loader(
            loader_problems=self.problems,
            zip_content=self.zip)

    def tearDown(self):
        self.accumulator.tear_down_assert_no_more_exceptions()

    def testEmptyFile(self):
        self.zip.writestr("test.txt", "")
        results = list(self.loader._read_csv_dict("test.txt", [], [], []))
        self.assertEquals([], results)
        self.accumulator.PopException("EmptyFile")
        self.accumulator.assert_no_more_exceptions()

    def testHeaderOnly(self):
        self.zip.writestr("test.txt", "test_id,test_name")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.assert_no_more_exceptions()

    def testHeaderAndNewLineOnly(self):
        self.zip.writestr("test.txt", "test_id,test_name\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.assert_no_more_exceptions()

    def testHeaderWithSpaceBefore(self):
        self.zip.writestr("test.txt", " test_id, test_name\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.assert_no_more_exceptions()

    def testHeaderWithSpaceBeforeAfter(self):
        self.zip.writestr("test.txt", "test_id , test_name\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.PopException("CsvSyntax")
        self.accumulator.assert_no_more_exceptions()

    def testHeaderQuoted(self):
        self.zip.writestr("test.txt", "\"test_id\", \"test_name\"\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.assert_no_more_exceptions()

    def testHeaderSpaceAfterQuoted(self):
        self.zip.writestr("test.txt", "\"test_id\" , \"test_name\"\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.PopException("CsvSyntax")
        self.accumulator.assert_no_more_exceptions()

    def testHeaderSpaceInQuotesAfterValue(self):
        self.zip.writestr("test.txt", "\"test_id \",\"test_name\"\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.PopException("CsvSyntax")
        self.accumulator.assert_no_more_exceptions()

    def testHeaderSpaceInQuotesBeforeValue(self):
        self.zip.writestr("test.txt", "\"test_id\",\" test_name\"\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.PopException("CsvSyntax")
        self.accumulator.assert_no_more_exceptions()

    def testHeaderEmptyColumnName(self):
        self.zip.writestr("test.txt", 'test_id,test_name,\n')
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.PopException("CsvSyntax")
        self.accumulator.assert_no_more_exceptions()

    def testHeaderAllUnknownColumnNames(self):
        self.zip.writestr("test.txt", 'id,nam\n')
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("CsvSyntax")
        self.assertTrue(e.format_problem().find("missing the header") != -1)
        self.accumulator.assert_no_more_exceptions()

    def testFieldWithSpaces(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1 , my name\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 2,
                            ["test_id", "test_name"], ["id1", "my name"])],
                          results)
        self.accumulator.assert_no_more_exceptions()

    def testFieldWithOnlySpaces(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1,  \n")  # spaces are skipped to yield empty field
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": ""}, 2,
                            ["test_id", "test_name"], ["id1", ""])], results)
        self.accumulator.assert_no_more_exceptions()

    def testQuotedFieldWithSpaces(self):
        self.zip.writestr("test.txt",
                          'test_id,"test_name",test_size\n'
                          '"id1" , "my name" , "234 "\n')
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name",
                                                   "test_size"], [], []))
        self.assertEquals(
            [({"test_id": "id1", "test_name": "my name", "test_size": "234"}, 2,
              ["test_id", "test_name", "test_size"], ["id1", "my name", "234"])],
            results)
        self.accumulator.assert_no_more_exceptions()

    def testQuotedFieldWithCommas(self):
        self.zip.writestr("test.txt",
                          'id,name1,name2\n'
                          '"1", "brown, tom", "brown, ""tom"""\n')
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["id", "name1", "name2"], [], []))
        self.assertEquals(
            [({"id": "1", "name1": "brown, tom", "name2": "brown, \"tom\""}, 2,
              ["id", "name1", "name2"], ["1", "brown, tom", "brown, \"tom\""])],
            results)
        self.accumulator.assert_no_more_exceptions()

    def testUnknownColumn(self):
        # A small typo (omitting '_' in a header name) is detected
        self.zip.writestr("test.txt", "test_id,testname\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("UnrecognizedColumn")
        self.assertEquals("testname", e.column_name)
        self.accumulator.assert_no_more_exceptions()

    def testDeprecatedColumn(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_new"],
                                                  ["test_id"],
                                                  [("test_old", "test_new")]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue("test_new" in e.reason)
        self.accumulator.assert_no_more_exceptions()

    def testDeprecatedColumnWithoutNewColumn(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_new"],
                                                  ["test_id"],
                                                  [("test_old", None)]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue(not e.reason or "use the new column" not in e.reason)
        self.accumulator.assert_no_more_exceptions()

    def testDeprecatedValuesBeingRead(self):
        self.zip.writestr("test.txt",
                          "test_id,test_old\n"
                          "1,old_value1\n"
                          "2,old_value2\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_new"],
                                                  ["test_id"],
                                                  [("test_old", "test_new")]))
        self.assertEquals(2, len(results))
        self.assertEquals('old_value1', results[0][0]['test_old'])
        self.assertEquals('old_value2', results[1][0]['test_old'])
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals('test_old', e.column_name)
        self.accumulator.assert_no_more_exceptions()

    def testMissingRequiredColumn(self):
        self.zip.writestr("test.txt", "test_id,test_size\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_size"],
                                                  ["test_name"], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("MissingColumn")
        self.assertEquals("test_name", e.column_name)
        self.accumulator.assert_no_more_exceptions()

    def testRequiredNotInAllCols(self):
        self.zip.writestr("test.txt", "test_id,test_name,test_size\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_size"],
                                                  ["test_name"], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("UnrecognizedColumn")
        self.assertEquals("test_name", e.column_name)
        self.accumulator.assert_no_more_exceptions()

    def testBlankLine(self):
        # line_num is increased for an empty line
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "\n"
                          "id1,my name\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 3,
                            ["test_id", "test_name"], ["id1", "my name"])], results)
        self.accumulator.assert_no_more_exceptions()

    def testExtraComma(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1,my name,\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 2,
                            ["test_id", "test_name"], ["id1", "my name"])],
                          results)
        e = self.accumulator.PopException("OtherProblem")
        self.assertTrue(e.format_problem().find("too many cells") != -1)
        self.accumulator.assert_no_more_exceptions()

    def testMissingComma(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1 my name\n")
        results = list(self.loader._read_csv_dict("test.txt",
                                                  ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1 my name"}, 2,
                            ["test_id", "test_name"], ["id1 my name"])], results)
        e = self.accumulator.PopException("OtherProblem")
        self.assertTrue(e.format_problem().find("missing cells") != -1)
        self.accumulator.assert_no_more_exceptions()

    def testDetectsDuplicateHeaders(self):
        self.zip.writestr(
            "transfers.txt",
            "from_stop_id,from_stop_id,to_stop_id,transfer_type,min_transfer_time,"
            "min_transfer_time,min_transfer_time,min_transfer_time,unknown,"
            "unknown\n"
            "BEATTY_AIRPORT,BEATTY_AIRPORT,BULLFROG,3,,2,,,,\n"
            "BULLFROG,BULLFROG,BEATTY_AIRPORT,2,1200,1,,,,\n")

        list(self.loader._read_csv_dict("transfers.txt",
                                        transitfeed.Transfer.FIELD_NAMES,
                                        transitfeed.Transfer.REQUIRED_FIELD_NAMES,
                                        transitfeed.Transfer.DEPRECATED_FIELD_NAMES))

        self.accumulator.pop_duplicate_column("transfers.txt", "from_stop_id", 2)
        self.accumulator.pop_duplicate_column("transfers.txt", "min_transfer_time", 4)
        self.accumulator.pop_duplicate_column("transfers.txt", "unknown", 2)
        e = self.accumulator.PopException("UnrecognizedColumn")
        self.assertEquals("unknown", e.column_name)
        self.accumulator.assert_no_more_exceptions()


class ReadCsvTestCase(util.TestCase):
    def setUp(self):
        self.accumulator = util.RecordingProblemAccumulator(self)
        self.problems = transitfeed.ProblemReporter(self.accumulator)
        self.zip = zipfile.ZipFile(StringIO(), 'a')
        self.loader = transitfeed.Loader(
            loader_problems=self.problems,
            zip_content=self.zip)

    def tearDown(self):
        self.accumulator.tear_down_assert_no_more_exceptions()

    def testDetectsDuplicateHeaders(self):
        self.zip.writestr(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date,end_date,end_date,tuesday,unknown,unknown\n"
            "FULLW,1,1,1,1,1,1,1,20070101,20101231,,,,,\n")

        list(self.loader._read_csv("calendar.txt",
                                   transitfeed.ServicePeriod.FIELD_NAMES,
                                   transitfeed.ServicePeriod.REQUIRED_FIELD_NAMES,
                                   transitfeed.ServicePeriod.DEPRECATED_FIELD_NAMES
                                   ))

        self.accumulator.pop_duplicate_column("calendar.txt", "end_date", 3)
        self.accumulator.pop_duplicate_column("calendar.txt", "tuesday", 2)
        self.accumulator.pop_duplicate_column("calendar.txt", "unknown", 2)
        e = self.accumulator.PopException("UnrecognizedColumn")
        self.assertEquals("unknown", e.column_name)
        self.accumulator.assert_no_more_exceptions()

    def testDeprecatedColumn(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._read_csv("test.txt",
                                             ["test_id", "test_new"],
                                             ["test_id"],
                                             [("test_old", "test_new")]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue("test_new" in e.reason)
        self.accumulator.assert_no_more_exceptions()

    def testDeprecatedColumnWithoutNewColumn(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._read_csv("test.txt",
                                             ["test_id", "test_new"],
                                             ["test_id"],
                                             [("test_old", None)]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue(not e.reason or "use the new column" not in e.reason)
        self.accumulator.assert_no_more_exceptions()


class BasicParsingTestCase(util.TestCase):
    """Checks that we're getting the number of child objects that we expect."""

    def assertLoadedCorrectly(self, schedule):
        """Check that the good_feed looks correct"""
        self.assertEqual(1, len(schedule._agencies))
        self.assertEqual(5, len(schedule.routes))
        self.assertEqual(2, len(schedule.service_periods))
        self.assertEqual(10, len(schedule.stops))
        self.assertEqual(11, len(schedule.trips))
        self.assertEqual(0, len(schedule.fare_zones))

    def assertLoadedStopTimesCorrectly(self, schedule):
        self.assertEqual(5, len(schedule.get_trip('CITY1').get_stop_times()))
        self.assertEqual('to airport', schedule.get_trip('STBA').get_stop_times()[0].stop_headsign)
        self.assertEqual(2, schedule.get_trip('CITY1').get_stop_times()[1].pickup_type)
        self.assertEqual(3, schedule.get_trip('CITY1').get_stop_times()[1].drop_off_type)

    def test_MemoryDb(self):
        loader = transitfeed.Loader(
            util.data_path('good_feed.zip'),
            loader_problems=util.get_test_failure_problem_reporter(self),
            extra_validation=True,
            memory_db=True)
        schedule = loader.load()
        self.assertLoadedCorrectly(schedule)
        self.assertLoadedStopTimesCorrectly(schedule)

    def test_TemporaryFile(self):
        loader = transitfeed.Loader(
            util.data_path('good_feed.zip'),
            loader_problems=util.get_test_failure_problem_reporter(self),
            extra_validation=True,
            memory_db=False)
        schedule = loader.load()
        self.assertLoadedCorrectly(schedule)
        self.assertLoadedStopTimesCorrectly(schedule)

    def test_NoLoadStopTimes(self):
        problems = util.get_test_failure_problem_reporter(
            self, ignore_types=("ExpirationDate", "UnusedStop", "OtherProblem"))
        loader = transitfeed.Loader(
            util.data_path('good_feed.zip'),
            loader_problems=problems,
            extra_validation=True,
            load_stop_times=False)
        schedule = loader.load()
        self.assertLoadedCorrectly(schedule)
        self.assertEqual(0, len(schedule.get_trip('CITY1').get_stop_times()))


class UndefinedStopAgencyTestCase(util.LoadTestCase):
    def runTest(self):
        self.ExpectInvalidValue('undefined_stop', 'stop_id')
