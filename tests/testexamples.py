# Test the examples to make sure they are not broken
import os
import re
import transitfeed
import unittest
import urllib.request
from tests import util


class WikiExample(util.TempDirTestCaseBase):
    # Download example from wiki and run it

    @staticmethod
    def runTest():
        wiki_source = urllib.request.urlopen(
            'https://raw.githubusercontent.com/wiki/google/transitfeed/TransitFeed.md'
        ).read()
        m = re.search(r'```\s*(import transitfeed.*)```', wiki_source, re.DOTALL)
        if not m:
            raise Exception("Failed to find source code on wiki page")
        wiki_code = m.group(1)
        exec(wiki_code)


class ShuttleFromXmlfeed(util.TempDirTestCaseBase):
    def runTest(self):
        self.check_call_with_path(
            [self.GetExamplePath('shuttle_from_xmlfeed.py'),
             '--input', 'file:' + self.GetExamplePath('shuttle_from_xmlfeed.xml'),
             '--output', 'shuttle-YYYYMMDD.zip',
             # save the path of the dated output to tempfilepath
             '--execute', 'echo %(path)s > outputpath'])

        dated_path = open('outputpath').read().strip()
        self.assertTrue(re.match(r'shuttle-20\d\d[01]\d[0123]\d.zip$', dated_path))
        if not os.path.exists(dated_path):
            raise Exception('did not create expected file')


class Table(util.TempDirTestCaseBase):
    def runTest(self):
        self.check_call_with_path(
            [self.GetExamplePath('table.py'),
             '--input', self.GetExamplePath('table.txt'),
             '--output', 'google_transit.zip'])
        if not os.path.exists('google_transit.zip'):
            raise Exception('should have created output')


class SmallBuilder(util.TempDirTestCaseBase):
    def runTest(self):
        self.check_call_with_path(
            [self.GetExamplePath('small_builder.py'),
             '--output', 'google_transit.zip'])
        if not os.path.exists('google_transit.zip'):
            raise Exception('should have created output')


class GoogleRandomQueries(util.TempDirTestCaseBase):
    def testNormalRun(self):
        self.check_call_with_path(
            [self.GetExamplePath('google_random_queries.py'),
             '--output', 'queries.html',
             '--limit', '5',
             self.GetPath('tests', 'data', 'good_feed')])
        if not os.path.exists('queries.html'):
            raise Exception('should have created output')

    def TestInvalidFeedStillWorks(self):
        self.check_call_with_path(
            [self.GetExamplePath('google_random_queries.py'),
             '--output', 'queries.html',
             '--limit', '5',
             self.GetPath('tests', 'data', 'invalid_route_agency')])
        if not os.path.exists('queries.html'):
            raise Exception('should have created output')

    def TestBadArgs(self):
        self.check_call_with_path(
            [self.GetExamplePath('google_random_queries.py'),
             '--output', 'queries.html',
             '--limit', '5'],
            expected_retcode=2)
        if os.path.exists('queries.html'):
            raise Exception('should not have created output')


class FilterUnusedStops(util.TempDirTestCaseBase):
    def testNormalRun(self):
        unused_stop_path = self.GetPath('tests', 'data', 'unused_stop')
        # Make sure original data has an unused stop.
        accumulator = util.RecordingProblemAccumulator(self, "ExpirationDate")
        problem_reporter = transitfeed.ProblemReporter(accumulator)
        transitfeed.Loader(
            unused_stop_path,
            loader_problems=problem_reporter, extra_validation=True).load()
        accumulator.pop_exception("UnusedStop")
        accumulator.assert_no_more_exceptions()

        stdout, stderr = self.check_call_with_path(
            [self.GetExamplePath('filter_unused_stops.py'),
             '--list_removed',
             unused_stop_path, 'output.zip'])
        # Extra stop was listed on stdout
        self.assertNotEqual(stdout.find('Bogus Stop'), -1)

        # Make sure unused stop was removed and another stop still exists.
        schedule = transitfeed.Loader(
            'output.zip', loader_problems=problem_reporter, extra_validation=True).load()
        schedule.get_stop('STAGECOACH')
        accumulator.assert_no_more_exceptions()


if __name__ == '__main__':
    unittest.main()
