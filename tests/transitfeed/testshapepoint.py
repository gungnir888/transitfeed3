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

# Unit tests for the shapepoint module.
from tests import util
import transitfeed


class ShapeValidationTestCase(util.ValidationTestCase):
    def ExpectFailedAdd(self, shape, lat, lon, dist, column_name, value):
        self.ExpectInvalidValueInClosure(
            column_name, value,
            lambda: shape.add_point(lat, lon, dist, self.problems))

    def runTest(self):
        shape = transitfeed.Shape('TEST')
        repr(shape)  # shouldn't crash
        self.ValidateAndExpectOtherProblem(shape)  # no points!

        self.ExpectFailedAdd(shape, 36.905019, -116.763207, -1,
                             'shape_dist_traveled', -1)

        shape.add_point(36.915760, -116.751709, 0, self.problems)
        shape.add_point(36.905018, -116.763206, 5, self.problems)
        shape.validate(self.problems)

        shape.shape_id = None
        self.ValidateAndExpectMissingValue(shape, 'shape_id')
        shape.shape_id = 'TEST'

        self.ExpectFailedAdd(shape, 91, -116.751709, 6, 'shape_pt_lat', 91)
        self.ExpectFailedAdd(shape, -91, -116.751709, 6, 'shape_pt_lat', -91)

        self.ExpectFailedAdd(shape, 36.915760, -181, 6, 'shape_pt_lon', -181)
        self.ExpectFailedAdd(shape, 36.915760, 181, 6, 'shape_pt_lon', 181)

        self.ExpectFailedAdd(shape, 0.5, -0.5, 6, 'shape_pt_lat', 0.5)
        self.ExpectFailedAdd(shape, 0, 0, 6, 'shape_pt_lat', 0)

        # distance decreasing is bad, but staying the same is OK
        shape.add_point(36.905019, -116.763206, 4, self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('Each subsequent point', e.format_problem())
        self.assertMatchesRegex('distance was 5.000000.', e.format_problem())
        self.accumulator.assert_no_more_exceptions()

        shape.add_point(36.925019, -116.764206, 6, self.problems)
        self.accumulator.assert_no_more_exceptions()

        shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 6, 8)
        shape.add_shape_point_object_unsorted(shapepoint, self.problems)
        shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 5, 10)
        shape.add_shape_point_object_unsorted(shapepoint, self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('Each subsequent point', e.format_problem())
        self.assertMatchesRegex('distance was 8.000000.', e.format_problem())
        self.accumulator.assert_no_more_exceptions()

        shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 6, 11)
        shape.add_shape_point_object_unsorted(shapepoint, self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('The sequence number 6 occurs ', e.format_problem())
        self.assertMatchesRegex('once in shape TEST.', e.format_problem())
        self.accumulator.assert_no_more_exceptions()


class ShapePointValidationTestCase(util.ValidationTestCase):
    def runTest(self):
        shapepoint = transitfeed.ShapePoint('', 36.915720, -116.7156, 0, 0)
        self.ExpectMissingValueInClosure('shape_id',
                                         lambda: shapepoint.parse_attributes(self.problems))

        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '00', '0')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.pop_exception('InvalidNonNegativeIntegerValue')
        self.assertMatchesRegex('not have a leading zero', e.format_problem())
        self.accumulator.assert_no_more_exceptions()

        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', -1, '0')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('Value should be a number', e.format_problem())
        self.accumulator.assert_no_more_exceptions()

        shapepoint = transitfeed.ShapePoint('T', '0.1', '0.1', '1', '0')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('too close to 0, 0,', e.format_problem())
        self.accumulator.assert_no_more_exceptions()

        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '0', '')
        shapepoint.parse_attributes(self.problems)
        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '0', '-1')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.pop_exception('InvalidValue')
        self.assertMatchesRegex('Invalid value -1.0', e.format_problem())
        self.assertMatchesRegex('should be a positive number', e.format_problem())
        self.accumulator.assert_no_more_exceptions()
