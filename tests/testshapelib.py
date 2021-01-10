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

"""Tests for transitfeed.shapelib.py"""

__author__ = 'chris.harrelson.code@gmail.com (Chris Harrelson)'

import math
from transitfeed import shapelib
from transitfeed.shapelib import Point
from transitfeed.shapelib import Poly
from transitfeed.shapelib import PolyCollection
from transitfeed.shapelib import PolyGraph
import unittest
from tests import util


def formatPoint(p, precision=12):
    formatString = "(%%.%df, %%.%df, %%.%df)" % (precision, precision, precision)
    return formatString % (p.x, p.y, p.z)


def formatPoints(points):
    return "[%s]" % ", ".join([formatPoint(p, precision=4) for p in points])


class ShapeLibTestBase(util.TestCase):
    def assertApproxEq(self, a, b):
        self.assertAlmostEqual(a, b, 8)

    def assertPointApproxEq(self, a, b):
        try:
            self.assertApproxEq(a.x, b.x)
            self.assertApproxEq(a.y, b.y)
            self.assertApproxEq(a.z, b.z)
        except AssertionError:
            print('ERROR: %s != %s' % (formatPoint(a), formatPoint(b)))
            raise

    def assertPointsApproxEq(self, points1, points2):
        try:
            self.assertEqual(len(points1), len(points2))
        except AssertionError:
            print("ERROR: %s != %s" % (formatPoints(points1), formatPoints(points2)))
            raise
        for i in xrange(len(points1)):
            try:
                self.assertPointApproxEq(points1[i], points2[i])
            except AssertionError:
                print('ERROR: points not equal in position %d\n%s != %s'
                      % (i, formatPoints(points1), formatPoints(points2)))
                raise


class TestPoints(ShapeLibTestBase):
    def testPoints(self):
        p = Point(1, 1, 1)

        self.assertApproxEq(p.dot_prod(p), 3)

        self.assertApproxEq(p.norm2(), math.sqrt(3))

        self.assertPointApproxEq(Point(1.5, 1.5, 1.5),
                                 p.times(1.5))

        norm = 1.7320508075688772
        self.assertPointApproxEq(p.normalize(),
                                 Point(1 / norm,
                                       1 / norm,
                                       1 / norm))

        p2 = Point(1, 0, 0)
        self.assertPointApproxEq(p2, p2.normalize())

    def testCrossProd(self):
        p1 = Point(1, 0, 0).normalize()
        p2 = Point(0, 1, 0).normalize()
        p1_cross_p2 = p1.cross_prod(p2)
        self.assertApproxEq(p1_cross_p2.x, 0)
        self.assertApproxEq(p1_cross_p2.y, 0)
        self.assertApproxEq(p1_cross_p2.z, 1)

    def testRobustCrossProd(self):
        p1 = Point(1, 0, 0)
        p2 = Point(1, 0, 0)
        self.assertPointApproxEq(Point(0, 0, 0),
                                 p1.cross_prod(p2))
        # only needs to be an arbitrary vector perpendicular to (1, 0, 0)
        self.assertPointApproxEq(
            Point(0.000000000000000, -0.998598452020993, 0.052925717957113),
            p1.robust_cross_prod(p2))

    def testS2LatLong(self):
        point = Point.from_lat_lng(30, 40)
        self.assertPointApproxEq(Point(0.663413948169,
                                       0.556670399226,
                                       0.5), point)
        (lat, lng) = point.to_lat_lng()
        self.assertApproxEq(30, lat)
        self.assertApproxEq(40, lng)

    def testOrtho(self):
        point = Point(1, 1, 1)
        ortho = point.ortho()
        self.assertApproxEq(ortho.dot_prod(point), 0)

    def testAngle(self):
        point1 = Point(1, 1, 0).normalize()
        point2 = Point(0, 1, 0)
        self.assertApproxEq(45, point1.angle(point2) * 360 / (2 * math.pi))
        self.assertApproxEq(point1.angle(point2), point2.angle(point1))

    def testGetDistanceMeters(self):
        point1 = Point.from_lat_lng(40.536895, -74.203033)
        point2 = Point.from_lat_lng(40.575239, -74.112825)
        self.assertApproxEq(8732.623770873237,
                            point1.get_distance_meters(point2))


class TestClosestPoint(ShapeLibTestBase):
    def testGetClosestPoint(self):
        x = Point(1, 1, 0).normalize()
        a = Point(1, 0, 0)
        b = Point(0, 1, 0)

        closest = shapelib.get_closest_point(x, a, b)
        self.assertApproxEq(0.707106781187, closest.x)
        self.assertApproxEq(0.707106781187, closest.y)
        self.assertApproxEq(0.0, closest.z)


class TestPoly(ShapeLibTestBase):
    def testGetClosestPointShape(self):
        poly = Poly()

        poly.add_point(Point(1, 1, 0).normalize())
        self.assertPointApproxEq(Point(
            0.707106781187, 0.707106781187, 0), poly.get_point(0))

        point = Point(0, 1, 1).normalize()
        self.assertPointApproxEq(Point(1, 1, 0).normalize(),
                                 poly.get_closest_point(point)[0])

        poly.add_point(Point(0, 1, 1).normalize())

        self.assertPointApproxEq(
            Point(0, 1, 1).normalize(),
            poly.get_closest_point(point)[0])

    def testCutAtClosestPoint(self):
        poly = Poly()
        poly.add_point(Point(0, 1, 0).normalize())
        poly.add_point(Point(0, 0.5, 0.5).normalize())
        poly.add_point(Point(0, 0, 1).normalize())

        (before, after) = \
            poly.cut_at_closest_point(Point(0, 0.3, 0.7).normalize())

        self.assert_(2 == before.get_num_points())
        self.assert_(2 == before.get_num_points())
        self.assertPointApproxEq(
            Point(0, 0.707106781187, 0.707106781187), before.get_point(1))

        self.assertPointApproxEq(
            Point(0, 0.393919298579, 0.919145030018), after.get_point(0))

        poly = Poly()
        poly.add_point(Point.from_lat_lng(40.527035999999995, -74.191265999999999))
        poly.add_point(Point.from_lat_lng(40.526859999999999, -74.191140000000004))
        poly.add_point(Point.from_lat_lng(40.524681000000001, -74.189579999999992))
        poly.add_point(Point.from_lat_lng(40.523128999999997, -74.188467000000003))
        poly.add_point(Point.from_lat_lng(40.523054999999999, -74.188676000000001))
        pattern = Poly()
        pattern.add_point(Point.from_lat_lng(40.52713,
                                             -74.191146000000003))
        self.assertApproxEq(14.564268281551, pattern.greedy_poly_match_dist(poly))

    def testMergePolys(self):
        poly1 = Poly(name="Foo")
        poly1.add_point(Point(0, 1, 0).normalize())
        poly1.add_point(Point(0, 0.5, 0.5).normalize())
        poly1.add_point(Point(0, 0, 1).normalize())
        poly1.add_point(Point(1, 1, 1).normalize())

        poly2 = Poly()
        poly3 = Poly(name="Bar")
        poly3.add_point(Point(1, 1, 1).normalize())
        poly3.add_point(Point(2, 0.5, 0.5).normalize())

        merged1 = Poly.merge_polys([poly1, poly2])
        self.assertPointsApproxEq(poly1.get_points(), merged1.get_points())
        self.assertEqual("Foo;", merged1.get_name())

        merged2 = Poly.merge_polys([poly2, poly3])
        self.assertPointsApproxEq(poly3.get_points(), merged2.get_points())
        self.assertEqual(";Bar", merged2.get_name())

        merged3 = Poly.merge_polys([poly1, poly2, poly3], merge_point_threshold=0)
        mergedPoints = poly1.get_points()[:]
        mergedPoints.append(poly3.get_point(-1))
        self.assertPointsApproxEq(mergedPoints, merged3.get_points())
        self.assertEqual("Foo;;Bar", merged3.get_name())

        merged4 = Poly.merge_polys([poly2])
        self.assertEqual("", merged4.get_name())
        self.assertEqual(0, merged4.get_num_points())

        # test merging two nearby points
        newPoint = poly1.get_point(-1).plus(Point(0.000001, 0, 0)).normalize()
        poly1.add_point(newPoint)
        distance = poly1.get_point(-1).get_distance_meters(poly3.get_point(0))
        self.assertTrue(distance <= 10)
        self.assertTrue(distance > 5)

        merged5 = Poly.merge_polys([poly1, poly2, poly3], merge_point_threshold=10)
        mergedPoints = poly1.get_points()[:]
        mergedPoints.append(poly3.get_point(-1))
        self.assertPointsApproxEq(mergedPoints, merged5.get_points())
        self.assertEqual("Foo;;Bar", merged5.get_name())

        merged6 = Poly.merge_polys([poly1, poly2, poly3], merge_point_threshold=5)
        mergedPoints = poly1.get_points()[:]
        mergedPoints += poly3.get_points()
        self.assertPointsApproxEq(mergedPoints, merged6.get_points())
        self.assertEqual("Foo;;Bar", merged6.get_name())

    def testReversed(self):
        p1 = Point(1, 0, 0).normalize()
        p2 = Point(0, 0.5, 0.5).normalize()
        p3 = Point(0.3, 0.8, 0.5).normalize()
        poly1 = Poly([p1, p2, p3])
        self.assertPointsApproxEq([p3, p2, p1], poly1.reversed().get_points())

    def testLengthMeters(self):
        p1 = Point(1, 0, 0).normalize()
        p2 = Point(0, 0.5, 0.5).normalize()
        p3 = Point(0.3, 0.8, 0.5).normalize()
        poly0 = Poly([p1])
        poly1 = Poly([p1, p2])
        poly2 = Poly([p1, p2, p3])
        try:
            poly0.length_meters()
            self.fail("Should have thrown AssertionError")
        except AssertionError:
            pass

        p1_p2 = p1.get_distance_meters(p2)
        p2_p3 = p2.get_distance_meters(p3)
        self.assertEqual(p1_p2, poly1.length_meters())
        self.assertEqual(p1_p2 + p2_p3, poly2.length_meters())
        self.assertEqual(p1_p2 + p2_p3, poly2.reversed().length_meters())


class TestCollection(ShapeLibTestBase):
    def testPolyMatch(self):
        poly = Poly()
        poly.add_point(Point(0, 1, 0).normalize())
        poly.add_point(Point(0, 0.5, 0.5).normalize())
        poly.add_point(Point(0, 0, 1).normalize())

        collection = PolyCollection()
        collection.add_poly(poly)
        match = collection.find_matching_polys(Point(0, 1, 0),
                                               Point(0, 0, 1))
        self.assert_(len(match) == 1 and match[0] == poly)

        match = collection.find_matching_polys(Point(0, 1, 0),
                                               Point(0, 1, 0))
        self.assert_(len(match) == 0)

        poly = Poly()
        poly.add_point(Point.from_lat_lng(45.585212, -122.586136))
        poly.add_point(Point.from_lat_lng(45.586654, -122.587595))
        collection = PolyCollection()
        collection.add_poly(poly)

        match = collection.find_matching_polys(
            Point.from_lat_lng(45.585212, -122.586136),
            Point.from_lat_lng(45.586654, -122.587595))
        self.assert_(len(match) == 1 and match[0] == poly)

        match = collection.find_matching_polys(
            Point.from_lat_lng(45.585219, -122.586136),
            Point.from_lat_lng(45.586654, -122.587595))
        self.assert_(len(match) == 1 and match[0] == poly)

        self.assertApproxEq(0.0, poly.greedy_poly_match_dist(poly))

        match = collection.find_matching_polys(
            Point.from_lat_lng(45.587212, -122.586136),
            Point.from_lat_lng(45.586654, -122.587595))
        self.assert_(len(match) == 0)


class TestGraph(ShapeLibTestBase):
    def testReconstructPath(self):
        p1 = Point(1, 0, 0).normalize()
        p2 = Point(0, 0.5, 0.5).normalize()
        p3 = Point(0.3, 0.8, 0.5).normalize()
        poly1 = Poly([p1, p2])
        poly2 = Poly([p3, p2])
        came_from = {
            p2: (p1, poly1),
            p3: (p2, poly2)
        }

        graph = PolyGraph()
        reconstructed1 = graph._reconstruct_path(came_from, p1)
        self.assertEqual(0, reconstructed1.get_num_points())

        reconstructed2 = graph._reconstruct_path(came_from, p2)
        self.assertPointsApproxEq([p1, p2], reconstructed2.get_points())

        reconstructed3 = graph._reconstruct_path(came_from, p3)
        self.assertPointsApproxEq([p1, p2, p3], reconstructed3.get_points())

    def testShortestPath(self):
        p1 = Point(1, 0, 0).normalize()
        p2 = Point(0, 0.5, 0.5).normalize()
        p3 = Point(0.3, 0.8, 0.5).normalize()
        p4 = Point(0.7, 0.7, 0.5).normalize()
        poly1 = Poly([p1, p2, p3], "poly1")
        poly2 = Poly([p4, p3], "poly2")
        poly3 = Poly([p4, p1], "poly3")
        graph = PolyGraph()
        graph.add_poly(poly1)
        graph.add_poly(poly2)
        graph.add_poly(poly3)
        path = graph.shortest_path(p1, p4)
        self.assert_(path is not None)
        self.assertPointsApproxEq([p1, p4], path.get_points())

        path = graph.shortest_path(p1, p3)
        self.assert_(path is not None)
        self.assertPointsApproxEq([p1, p4, p3], path.get_points())

        path = graph.shortest_path(p3, p1)
        self.assert_(path is not None)
        self.assertPointsApproxEq([p3, p4, p1], path.get_points())

    def testFindShortestMultiPointPath(self):
        p1 = Point(1, 0, 0).normalize()
        p2 = Point(0.5, 0.5, 0).normalize()
        p3 = Point(0.5, 0.5, 0.1).normalize()
        p4 = Point(0, 1, 0).normalize()
        poly1 = Poly([p1, p2, p3], "poly1")
        poly2 = Poly([p4, p3], "poly2")
        poly3 = Poly([p4, p1], "poly3")
        graph = PolyGraph()
        graph.add_poly(poly1)
        graph.add_poly(poly2)
        graph.add_poly(poly3)
        path = graph.find_shortest_multi_point_path([p1, p3, p4])
        self.assert_(path is not None)
        self.assertPointsApproxEq([p1, p2, p3, p4], path.get_points())


if __name__ == '__main__':
    unittest.main()
