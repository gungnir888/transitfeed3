# Copyright 2008 Google Inc. All Rights Reserved.
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

"""Unit tests for the kmlwriter module."""
import os
import tempfile
import unittest
import kmlparser
import kmlwriter
from tests import util
import transitfeed
from transitfeed.compat import StringIO
import xml.etree.ElementTree as Et


def stop_name_mapper(x):
    return x.stop_name


def data_path(path):
    """Return the path to a given file in the test data directory.

    Args:
      path: The path relative to the test data directory.

    Returns:
      The absolute path.
    """
    here = os.path.dirname(__file__)
    return os.path.join(here, 'data', path)


def _element_to_string(root):
    """Returns the node as an XML string.

    Args:
      root: The ElementTree.Element instance.

    Returns:
      The XML string.
    """
    output = StringIO()
    Et.ElementTree(root).write(output, 'utf-8')
    return output.getvalue()


class TestKMLStopsRoundtrip(util.TestCase):
    """Checks to see whether all stops are preserved when going to and from KML.
    """

    def setUp(self):
        fd, self.kml_output = tempfile.mkstemp('kml')
        os.close(fd)

    def tearDown(self):
        os.remove(self.kml_output)

    def runTest(self):
        gtfs_input = data_path('good_feed.zip')
        feed1 = transitfeed.Loader(gtfs_input).load()
        kmlwriter.KMLWriter().write(feed1, self.kml_output)
        feed2 = transitfeed.Schedule()
        kmlparser.KMLParser().parse(self.kml_output, feed2)
        stops1 = set(map(stop_name_mapper, feed1.get_stop_list()))
        stops2 = set(map(stop_name_mapper, feed2.get_stop_list()))

        self.assertEqual(stops1, stops2)


class TestKMLGeneratorMethods(util.TestCase):
    """Tests the various KML element creation methods of KMLWriter."""

    def setUp(self):
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = Et.Element('parent')

    def testCreateFolderVisible(self):
        element = self.kmlwriter._create_folder(self.parent, 'folder_name')
        self.assertEqual(_element_to_string(element),
                         '<Folder><name>folder_name</name></Folder>')

    def testCreateFolderNotVisible(self):
        element = self.kmlwriter._create_folder(self.parent, 'folder_name',
                                                visible=False)
        self.assertEqual(_element_to_string(element),
                         '<Folder><name>folder_name</name>'
                         '<visibility>0</visibility></Folder>')

    def testCreateFolderWithDescription(self):
        element = self.kmlwriter._create_folder(self.parent, 'folder_name',
                                                description='folder_desc')
        self.assertEqual(_element_to_string(element),
                         '<Folder><name>folder_name</name>'
                         '<description>folder_desc</description></Folder>')

    def testCreatePlacemark(self):
        element = self.kmlwriter._create_placemark(self.parent, 'abcdef')
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name></Placemark>')

    def testCreatePlacemarkWithStyle(self):
        element = self.kmlwriter._create_placemark(self.parent, 'abcdef',
                                                   style_id='ghijkl')
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name>'
                         '<styleUrl>#ghijkl</styleUrl></Placemark>')

    def testCreatePlacemarkNotVisible(self):
        element = self.kmlwriter._create_placemark(self.parent, 'abcdef',
                                                   visible=False)
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name>'
                         '<visibility>0</visibility></Placemark>')

    def testCreatePlacemarkWithDescription(self):
        element = self.kmlwriter._create_placemark(self.parent, 'abcdef',
                                                   description='ghijkl')
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name>'
                         '<description>ghijkl</description></Placemark>')

    def testCreateLineString(self):
        coord_list = [(2.0, 1.0), (4.0, 3.0), (6.0, 5.0)]
        element = self.kmlwriter._create_line_string(self.parent, coord_list)
        self.assertEqual(_element_to_string(element),
                         '<LineString><tessellate>1</tessellate>'
                         '<coordinates>%f,%f %f,%f %f,%f</coordinates>'
                         '</LineString>' % (2.0, 1.0, 4.0, 3.0, 6.0, 5.0))

    def testCreateLineStringWithAltitude(self):
        coord_list = [(2.0, 1.0, 10), (4.0, 3.0, 20), (6.0, 5.0, 30.0)]
        element = self.kmlwriter._create_line_string(self.parent, coord_list)
        self.assertEqual(_element_to_string(element),
                         '<LineString><tessellate>1</tessellate>'
                         '<altitudeMode>absolute</altitudeMode>'
                         '<coordinates>%f,%f,%f %f,%f,%f %f,%f,%f</coordinates>'
                         '</LineString>' %
                         (2.0, 1.0, 10.0, 4.0, 3.0, 20.0, 6.0, 5.0, 30.0))

    def testCreateLineStringForShape(self):
        shape = transitfeed.Shape('shape')
        shape.add_point(1.0, 1.0)
        shape.add_point(2.0, 4.0)
        shape.add_point(3.0, 9.0)
        element = self.kmlwriter._create_line_string_for_shape(self.parent, shape)
        self.assertEqual(_element_to_string(element),
                         '<LineString><tessellate>1</tessellate>'
                         '<coordinates>%f,%f %f,%f %f,%f</coordinates>'
                         '</LineString>' % (1.0, 1.0, 4.0, 2.0, 9.0, 3.0))


class TestRouteKML(util.TestCase):
    """Tests the routes folder KML generation methods of KMLWriter."""

    def setUp(self):
        self.feed = transitfeed.Loader(data_path('flatten_feed')).load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = Et.Element('parent')

    def testCreateRoutePatternsFolderNoPatterns(self):
        folder = self.kmlwriter._create_route_patterns_folder(
            self.parent, self.feed.get_route('route_7'))
        self.assert_(folder is None)

    def testCreateRoutePatternsFolderOnePattern(self):
        folder = self.kmlwriter._create_route_patterns_folder(
            self.parent, self.feed.get_route('route_1'))
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 1)

    def testCreateRoutePatternsFolderTwoPatterns(self):
        folder = self.kmlwriter._create_route_patterns_folder(
            self.parent, self.feed.get_route('route_3'))
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 2)

    def testCreateRoutePatternFolderTwoEqualPatterns(self):
        folder = self.kmlwriter._create_route_patterns_folder(
            self.parent, self.feed.get_route('route_4'))
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 1)

    def testCreateRouteShapesFolderOneTripOneShape(self):
        folder = self.kmlwriter._create_route_shapes_folder(
            self.feed, self.parent, self.feed.get_route('route_1'))
        self.assertEqual(len(folder.findall('Placemark')), 1)

    def testCreateRouteShapesFolderTwoTripsTwoShapes(self):
        folder = self.kmlwriter._create_route_shapes_folder(
            self.feed, self.parent, self.feed.get_route('route_2'))
        self.assertEqual(len(folder.findall('Placemark')), 2)

    def testCreateRouteShapesFolderTwoTripsOneShape(self):
        folder = self.kmlwriter._create_route_shapes_folder(
            self.feed, self.parent, self.feed.get_route('route_3'))
        self.assertEqual(len(folder.findall('Placemark')), 1)

    def testCreateRouteShapesFolderTwoTripsNoShapes(self):
        folder = self.kmlwriter._create_route_shapes_folder(
            self.feed, self.parent, self.feed.get_route('route_4'))
        self.assert_(folder is None)

    def assertRouteFolderContainsTrips(self, tripids, folder):
        """Assert that the route folder contains exactly tripids"""
        actual_tripds = set()
        for placemark in folder.findall('Placemark'):
            actual_tripds.add(placemark.find('name').text)
        self.assertEquals(set(tripids), actual_tripds)

    def testCreateTripsFolderForRouteTwoTrips(self):
        route = self.feed.get_route('route_2')
        folder = self.kmlwriter._create_route_trips_folder(self.parent, route)
        self.assertRouteFolderContainsTrips(['route_2_1', 'route_2_2'], folder)

    def testCreateTripsFolderForRouteDateFilterNone(self):
        self.kmlwriter.date_filter = None
        route = self.feed.get_route('route_8')
        folder = self.kmlwriter._create_route_trips_folder(self.parent, route)
        self.assertRouteFolderContainsTrips(['route_8_1', 'route_8_2'], folder)

    def testCreateTripsFolderForRouteDateFilterSet(self):
        self.kmlwriter.date_filter = '20070604'
        route = self.feed.get_route('route_8')
        folder = self.kmlwriter._create_route_trips_folder(self.parent, route)
        self.assertRouteFolderContainsTrips(['route_8_2'], folder)

    @staticmethod
    def _get_trip_placemark(route_folder, trip_name):
        for trip_placemark in route_folder.findall('Placemark'):
            if trip_placemark.find('name').text == trip_name:
                return trip_placemark

    def testCreateRouteTripsFolderAltitude0(self):
        self.kmlwriter.altitude_per_sec = 0.0
        folder = self.kmlwriter._create_route_trips_folder(
            self.parent, self.feed.get_route('route_4'))
        trip_placemark = self._get_trip_placemark(folder, 'route_4_1')
        self.assertEqual(_element_to_string(trip_placemark.find('LineString')),
                         '<LineString><tessellate>1</tessellate>'
                         '<coordinates>-117.133162,36.425288 '
                         '-116.784582,36.868446 '
                         '-116.817970,36.881080</coordinates></LineString>')

    def testCreateRouteTripsFolderAltitude1(self):
        self.kmlwriter.altitude_per_sec = 0.5
        folder = self.kmlwriter._create_route_trips_folder(
            self.parent, self.feed.get_route('route_4'))
        trip_placemark = self._get_trip_placemark(folder, 'route_4_1')
        self.assertEqual(_element_to_string(trip_placemark.find('LineString')),
                         '<LineString><tessellate>1</tessellate>'
                         '<altitudeMode>absolute</altitudeMode>'
                         '<coordinates>-117.133162,36.425288,3600.000000 '
                         '-116.784582,36.868446,5400.000000 '
                         '-116.817970,36.881080,7200.000000</coordinates>'
                         '</LineString>')

    def testCreateRouteTripsFolderNoTrips(self):
        folder = self.kmlwriter._create_route_trips_folder(
            self.parent, self.feed.get_route('route_7'))
        self.assert_(folder is None)

    def testCreateRoutesFolderNoRoutes(self):
        schedule = transitfeed.Schedule()
        folder = self.kmlwriter._create_routes_folder(schedule, self.parent)
        self.assert_(folder is None)

    def testCreateRoutesFolderNoRoutesWithRouteType(self):
        folder = self.kmlwriter._create_routes_folder(self.feed, self.parent, 999)
        self.assert_(folder is None)

    def _TestCreateRoutesFolder(self, show_trips):
        self.kmlwriter.show_trips = show_trips
        folder = self.kmlwriter._create_routes_folder(self.feed, self.parent)
        self.assertEquals(folder.tag, 'Folder')
        styles = self.parent.findall('Style')
        self.assertEquals(len(styles), len(self.feed.get_route_list()))
        route_folders = folder.findall('Folder')
        self.assertEquals(len(route_folders), len(self.feed.get_route_list()))

    def testCreateRoutesFolder(self):
        self._TestCreateRoutesFolder(False)

    def testCreateRoutesFolderShowTrips(self):
        self._TestCreateRoutesFolder(True)

    def testCreateRoutesFolderWithRouteType(self):
        folder = self.kmlwriter._create_routes_folder(self.feed, self.parent, 1)
        route_folders = folder.findall('Folder')
        self.assertEquals(len(route_folders), 1)


class TestShapesKML(util.TestCase):
    """Tests the shapes folder KML generation methods of KMLWriter."""

    def setUp(self):
        self.flatten_feed = transitfeed.Loader(data_path('flatten_feed')).load()
        self.good_feed = transitfeed.Loader(data_path('good_feed.zip')).load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = Et.Element('parent')

    def testCreateShapesFolderNoShapes(self):
        folder = self.kmlwriter._create_shapes_folder(self.good_feed, self.parent)
        self.assertEquals(folder, None)

    def testCreateShapesFolder(self):
        folder = self.kmlwriter._create_shapes_folder(self.flatten_feed, self.parent)
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 3)
        for placemark in placemarks:
            self.assert_(placemark.find('LineString') is not None)


class TestStopsKML(util.TestCase):
    """Tests the stops folder KML generation methods of KMLWriter."""

    def setUp(self):
        self.feed = transitfeed.Loader(data_path('flatten_feed')).load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = Et.Element('parent')

    def testCreateStopsFolderNoStops(self):
        schedule = transitfeed.Schedule()
        folder = self.kmlwriter._create_stops_folder(schedule, self.parent)
        self.assert_(folder is None)

    def testCreateStopsFolder(self):
        folder = self.kmlwriter._create_stops_folder(self.feed, self.parent)
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), len(self.feed.get_stop_list()))


class TestShapePointsKML(util.TestCase):
    """Tests the shape points folder KML generation methods of KMLWriter."""

    def setUp(self):
        self.flatten_feed = transitfeed.Loader(data_path('flatten_feed')).load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.kmlwriter.shape_points = True
        self.parent = Et.Element('parent')

    def testCreateShapePointsFolder(self):
        folder = self.kmlwriter._create_shapes_folder(self.flatten_feed, self.parent)
        shape_point_folder = folder.find('Folder')
        self.assertEquals(shape_point_folder.find('name').text,
                          'shape_1 Shape Points')
        placemarks = shape_point_folder.findall('Placemark')
        self.assertEquals(len(placemarks), 4)
        for placemark in placemarks:
            self.assert_(placemark.find('Point') is not None)


class FullTests(util.TempDirTestCaseBase):
    def testNormalRun(self):
        self.check_call_with_path(
            [self.GetPath('kmlwriter.py'), self.GetTestDataPath('good_feed.zip'),
             'good_feed.kml'])
        self.assertFalse(os.path.exists('transitfeedcrash.txt'))
        self.assertTrue(os.path.exists('good_feed.kml'))

    def testCommandLineError(self):
        (out, err) = self.check_call_with_path(
            [self.GetPath('kmlwriter.py'), '--bad_flag'], expected_retcode=2)
        self.assertMatchesRegex(r'no such option.*--bad_flag', err)
        self.assertMatchesRegex(r'--showtrips', err)
        self.assertFalse(os.path.exists('transitfeedcrash.txt'))

    def testCrashHandler(self):
        (out, err) = self.check_call_with_path(
            [self.GetPath('kmlwriter.py'), 'IWantMyCrash', 'output.zip'],
            stdin_str="\n", expected_retcode=127)
        self.assertMatchesRegex(r'Yikes', out)
        crashout = open('transitfeedcrash.txt').read()
        self.assertMatchesRegex(r'For testCrashHandler', crashout)


if __name__ == '__main__':
    unittest.main()
