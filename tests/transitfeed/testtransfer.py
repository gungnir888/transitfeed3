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

# Unit tests for the transfer module.
from io import StringIO
import transitfeed
from tests import util


class TransferObjectTestCase(util.ValidationTestCase):
    def testValidation(self):
        # Totally bogus data shouldn't cause a crash
        transfer = transitfeed.Transfer(field_dict={"ignored": "foo"})
        self.assertEquals(0, transfer.transfer_type)

        transfer = transitfeed.Transfer(from_stop_id="S1", to_stop_id="S2",
                                        transfer_type="1")
        self.assertEquals("S1", transfer.from_stop_id)
        self.assertEquals("S2", transfer.to_stop_id)
        self.assertEquals(1, transfer.transfer_type)
        self.assertEquals(None, transfer.min_transfer_time)
        # references to other tables aren't checked without schedule so this
        # validates even though from_stop_id and to_stop_id are invalid.
        transfer.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()
        self.assertEquals("S1", transfer.from_stop_id)
        self.assertEquals("S2", transfer.to_stop_id)
        self.assertEquals(1, transfer.transfer_type)
        self.assertEquals(None, transfer.min_transfer_time)
        self.accumulator.assert_no_more_exceptions()

        transfer = transitfeed.Transfer(
            field_dict={
                "from_stop_id": "S1",
                "to_stop_id": "S2",
                "transfer_type": "2",
                "min_transfer_time": "2"
            }
        )
        self.assertEquals("S1", transfer.from_stop_id)
        self.assertEquals("S2", transfer.to_stop_id)
        self.assertEquals(2, transfer.transfer_type)
        self.assertEquals(2, transfer.min_transfer_time)
        transfer.validate(self.problems)
        self.assertEquals("S1", transfer.from_stop_id)
        self.assertEquals("S2", transfer.to_stop_id)
        self.assertEquals(2, transfer.transfer_type)
        self.assertEquals(2, transfer.min_transfer_time)
        self.accumulator.assert_no_more_exceptions()

        transfer = transitfeed.Transfer(
            field_dict={
                "from_stop_id": "S1",
                "to_stop_id": "S2",
                "transfer_type": "-4",
                "min_transfer_time": "2"
            }
        )
        self.assertEquals("S1", transfer.from_stop_id)
        self.assertEquals("S2", transfer.to_stop_id)
        self.assertEquals("-4", transfer.transfer_type)
        self.assertEquals(2, transfer.min_transfer_time)
        transfer.validate(self.problems)
        self.accumulator.pop_invalid_value("transfer_type")
        self.accumulator.PopException(
            "MinimumTransferTimeSetWithInvalidTransferType")
        self.assertEquals("S1", transfer.from_stop_id)
        self.assertEquals("S2", transfer.to_stop_id)
        self.assertEquals("-4", transfer.transfer_type)
        self.assertEquals(2, transfer.min_transfer_time)

        transfer = transitfeed.Transfer(
            field_dict={
                "from_stop_id": "S1",
                "to_stop_id": "S2",
                "transfer_type": "",
                "min_transfer_time": "-1"
            }
        )
        self.assertEquals(0, transfer.transfer_type)
        transfer.validate(self.problems)
        # It's negative *and* transfer_type is not 2
        self.accumulator.PopException(
            "MinimumTransferTimeSetWithInvalidTransferType")
        self.accumulator.pop_invalid_value("min_transfer_time")

        # Non-integer min_transfer_time with transfer_type == 2
        transfer = transitfeed.Transfer(
            field_dict={
                "from_stop_id": "S1",
                "to_stop_id": "S2",
                "transfer_type": "2",
                "min_transfer_time": "foo"
            }
        )
        self.assertEquals("foo", transfer.min_transfer_time)
        transfer.validate(self.problems)
        self.accumulator.pop_invalid_value("min_transfer_time")

        # Non-integer min_transfer_time with transfer_type != 2
        transfer = transitfeed.Transfer(
            field_dict={
                "from_stop_id": "S1",
                "to_stop_id": "S2",
                "transfer_type": "1",
                "min_transfer_time": "foo"
            }
        )
        self.assertEquals("foo", transfer.min_transfer_time)
        transfer.validate(self.problems)
        # It's not an integer *and* transfer_type is not 2
        self.accumulator.PopException(
            "MinimumTransferTimeSetWithInvalidTransferType")
        self.accumulator.pop_invalid_value("min_transfer_time")

        # Fractional min_transfer_time with transfer_type == 2
        transfer = transitfeed.Transfer(
            field_dict={
                "from_stop_id": "S1",
                "to_stop_id": "S2",
                "transfer_type": "2",
                "min_transfer_time": "2.5"
            }
        )
        self.assertEquals("2.5", transfer.min_transfer_time)
        transfer.validate(self.problems)
        self.accumulator.pop_invalid_value("min_transfer_time")

        # Fractional min_transfer_time with transfer_type != 2
        transfer = transitfeed.Transfer(
            field_dict={
                "from_stop_id": "S1",
                "to_stop_id": "S2",
                "transfer_type": "1",
                "min_transfer_time": "2.5"
            }
        )
        self.assertEquals("2.5", transfer.min_transfer_time)
        transfer.validate(self.problems)
        # It's not an integer *and* transfer_type is not 2
        self.accumulator.PopException(
            "MinimumTransferTimeSetWithInvalidTransferType")
        self.accumulator.pop_invalid_value("min_transfer_time")

        # simple successes
        transfer = transitfeed.Transfer()
        transfer.from_stop_id = "S1"
        transfer.to_stop_id = "S2"
        transfer.transfer_type = 0
        repr(transfer)  # shouldn't crash
        transfer.validate(self.problems)
        transfer.transfer_type = 3
        transfer.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()

        # transfer_type is out of range
        transfer.transfer_type = 4
        self.ValidateAndExpectInvalidValue(transfer, "transfer_type")
        transfer.transfer_type = -1
        self.ValidateAndExpectInvalidValue(transfer, "transfer_type")
        transfer.transfer_type = "text"
        self.ValidateAndExpectInvalidValue(transfer, "transfer_type")
        transfer.transfer_type = 2

        # invalid min_transfer_time
        transfer.min_transfer_time = -1
        self.ValidateAndExpectInvalidValue(transfer, "min_transfer_time")
        transfer.min_transfer_time = "text"
        self.ValidateAndExpectInvalidValue(transfer, "min_transfer_time")
        transfer.min_transfer_time = 4 * 3600
        transfer.validate(self.problems)
        e = self.accumulator.pop_invalid_value("min_transfer_time")
        self.assertEquals(e.type, transitfeed.TYPE_WARNING)
        transfer.min_transfer_time = 25 * 3600
        transfer.validate(self.problems)
        e = self.accumulator.pop_invalid_value("min_transfer_time")
        self.assertEquals(e.type, transitfeed.TYPE_ERROR)
        transfer.min_transfer_time = 250
        transfer.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()

        # missing stop ids
        transfer.from_stop_id = ""
        self.ValidateAndExpectMissingValue(transfer, 'from_stop_id')
        transfer.from_stop_id = "S1"
        transfer.to_stop_id = None
        self.ValidateAndExpectMissingValue(transfer, 'to_stop_id')
        transfer.to_stop_id = "S2"

        # from_stop_id and to_stop_id are present in schedule
        schedule = transitfeed.Schedule()
        # 597m appart
        stop1 = schedule.add_stop(57.5, 30.2, "stop 1")
        stop2 = schedule.add_stop(57.5, 30.21, "stop 2")
        transfer = transitfeed.Transfer(schedule=schedule)
        transfer.from_stop_id = stop1.stop_id
        transfer.to_stop_id = stop2.stop_id
        transfer.transfer_type = 2
        transfer.min_transfer_time = 600
        repr(transfer)  # shouldn't crash
        transfer.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()

        # only from_stop_id is present in schedule
        schedule = transitfeed.Schedule()
        stop1 = schedule.add_stop(57.5, 30.2, "stop 1")
        transfer = transitfeed.Transfer(schedule=schedule)
        transfer.from_stop_id = stop1.stop_id
        transfer.to_stop_id = "unexist"
        transfer.transfer_type = 2
        transfer.min_transfer_time = 250
        self.ValidateAndExpectInvalidValue(transfer, 'to_stop_id')
        transfer.from_stop_id = "unexist"
        transfer.to_stop_id = stop1.stop_id
        self.ValidateAndExpectInvalidValue(transfer, "from_stop_id")
        self.accumulator.assert_no_more_exceptions()

        # Transfer can only be added to a schedule once because _schedule is set
        transfer = transitfeed.Transfer()
        transfer.from_stop_id = stop1.stop_id
        transfer.to_stop_id = stop1.stop_id
        schedule.add_transfer_object(transfer)
        self.assertRaises(AssertionError, schedule.add_transfer_object, transfer)

    def testValidationSpeedDistanceAllTransferTypes(self):
        schedule = transitfeed.Schedule()
        stop1 = schedule.add_stop(1, 0, "stop 1")
        stop2 = schedule.add_stop(0, 1, "stop 2")
        transfer = transitfeed.Transfer(schedule=schedule)
        transfer.from_stop_id = stop1.stop_id
        transfer.to_stop_id = stop2.stop_id
        for transfer_type in [0, 1, 2, 3]:
            transfer.transfer_type = transfer_type

            # from_stop_id and to_stop_id are present in schedule
            # and a bit far away (should be warning)
            # 2303m appart
            stop1.stop_lat = 57.5
            stop1.stop_lon = 30.32
            stop2.stop_lat = 57.52
            stop2.stop_lon = 30.33
            transfer.min_transfer_time = 2500
            repr(transfer)  # shouldn't crash
            transfer.validate(self.problems)
            if transfer_type != 2:
                e = self.accumulator.PopException(
                    "MinimumTransferTimeSetWithInvalidTransferType")
                self.assertEquals(e.transfer_type, transfer.transfer_type)
            e = self.accumulator.PopException('TransferDistanceTooBig')
            self.assertEquals(e.type, transitfeed.TYPE_WARNING)
            self.assertEquals(e.from_stop_id, stop1.stop_id)
            self.assertEquals(e.to_stop_id, stop2.stop_id)
            self.accumulator.assert_no_more_exceptions()

            # from_stop_id and to_stop_id are present in schedule
            # and too far away (should be error)
            # 11140m appart
            stop1.stop_lat = 57.5
            stop1.stop_lon = 30.32
            stop2.stop_lat = 57.4
            stop2.stop_lon = 30.33
            transfer.min_transfer_time = 3600
            repr(transfer)  # shouldn't crash
            transfer.validate(self.problems)
            if transfer_type != 2:
                e = self.accumulator.PopException(
                    "MinimumTransferTimeSetWithInvalidTransferType")
                self.assertEquals(e.transfer_type, transfer.transfer_type)
            e = self.accumulator.PopException('TransferDistanceTooBig')
            self.assertEquals(e.type, transitfeed.TYPE_ERROR)
            self.assertEquals(e.from_stop_id, stop1.stop_id)
            self.assertEquals(e.to_stop_id, stop2.stop_id)
            e = self.accumulator.PopException('TransferWalkingSpeedTooFast')
            self.assertEquals(e.type, transitfeed.TYPE_WARNING)
            self.assertEquals(e.from_stop_id, stop1.stop_id)
            self.assertEquals(e.to_stop_id, stop2.stop_id)
            self.accumulator.assert_no_more_exceptions()

    def testSmallTransferTimeTriggersWarning(self):
        # from_stop_id and to_stop_id are present in schedule
        # and transfer time is too small
        schedule = transitfeed.Schedule()
        # 298m appart
        stop1 = schedule.add_stop(57.5, 30.2, "stop 1")
        stop2 = schedule.add_stop(57.5, 30.205, "stop 2")
        transfer = transitfeed.Transfer(schedule=schedule)
        transfer.from_stop_id = stop1.stop_id
        transfer.to_stop_id = stop2.stop_id
        transfer.transfer_type = 2
        transfer.min_transfer_time = 1
        repr(transfer)  # shouldn't crash
        transfer.validate(self.problems)
        e = self.accumulator.PopException('TransferWalkingSpeedTooFast')
        self.assertEquals(e.type, transitfeed.TYPE_WARNING)
        self.assertEquals(e.from_stop_id, stop1.stop_id)
        self.assertEquals(e.to_stop_id, stop2.stop_id)
        self.accumulator.assert_no_more_exceptions()

    def testVeryCloseStationsDoNotTriggerWarning(self):
        # from_stop_id and to_stop_id are present in schedule
        # and transfer time is too small, but stations
        # are very close together.
        schedule = transitfeed.Schedule()
        # 239m appart
        stop1 = schedule.add_stop(57.5, 30.2, "stop 1")
        stop2 = schedule.add_stop(57.5, 30.204, "stop 2")
        transfer = transitfeed.Transfer(schedule=schedule)
        transfer.from_stop_id = stop1.stop_id
        transfer.to_stop_id = stop2.stop_id
        transfer.transfer_type = 2
        transfer.min_transfer_time = 1
        repr(transfer)  # shouldn't crash
        transfer.validate(self.problems)
        self.accumulator.assert_no_more_exceptions()

    def testCustomAttribute(self):
        """Add unknown attributes to a Transfer and make sure they are saved."""
        transfer = transitfeed.Transfer()
        transfer.attr1 = "foo1"
        schedule = self.SimpleSchedule()
        transfer.to_stop_id = "stop1"
        transfer.from_stop_id = "stop1"
        schedule.add_transfer_object(transfer)
        transfer.attr2 = "foo2"

        saved_schedule_file = StringIO()
        schedule.write_google_transit_feed(saved_schedule_file)
        self.accumulator.assert_no_more_exceptions()

        # Ignore NoServiceExceptions error to keep the test simple
        load_problems = util.get_test_failure_problem_reporter(
            self, ("ExpirationDate", "UnrecognizedColumn", "NoServiceExceptions"))
        loaded_schedule = transitfeed.Loader(saved_schedule_file,
                                             loader_problems=load_problems,
                                             extra_validation=True).load()
        transfers = loaded_schedule.get_transfer_list()
        self.assertEquals(1, len(transfers))
        self.assertEquals("foo1", transfers[0].attr1)
        self.assertEquals("foo1", transfers[0]["attr1"])
        self.assertEquals("foo2", transfers[0].attr2)
        self.assertEquals("foo2", transfers[0]["attr2"])

    def testDuplicateId(self):
        schedule = self.SimpleSchedule()
        transfer1 = transitfeed.Transfer(from_stop_id="stop1", to_stop_id="stop2")
        schedule.add_transfer_object(transfer1)
        transfer2 = transitfeed.Transfer(field_dict=transfer1)
        transfer2.transfer_type = 3
        schedule.add_transfer_object(transfer2)
        transfer2.validate()
        e = self.accumulator.PopException('DuplicateID')
        self.assertEquals('(from_stop_id, to_stop_id)', e.column_name)
        self.assertEquals('(stop1, stop2)', e.value)
        self.assertTrue(e.is_warning())
        self.accumulator.assert_no_more_exceptions()
        # Check that both transfers were kept
        self.assertEquals(transfer1, schedule.get_transfer_list()[0])
        self.assertEquals(transfer2, schedule.get_transfer_list()[1])

        # Adding a transfer with a different ID shouldn't cause a problem report.
        transfer3 = transitfeed.Transfer(from_stop_id="stop1", to_stop_id="stop3")
        schedule.add_transfer_object(transfer3)
        self.assertEquals(3, len(schedule.get_transfer_list()))
        self.accumulator.assert_no_more_exceptions()

        # GetTransferIter should return all Transfers
        transfer4 = transitfeed.Transfer(from_stop_id="stop1")
        schedule.add_transfer_object(transfer4)
        self.assertEquals(
            ",stop2,stop2,stop3",
            ",".join(sorted(t["to_stop_id"] for t in schedule.get_transfer_iter())))
        self.accumulator.assert_no_more_exceptions()


class TransferValidationTestCase(util.MemoryZipTestCase):
    """Integration test for transfers."""

    def testInvalidStopIds(self):
        self.SetArchiveContents(
            "transfers.txt",
            "from_stop_id,to_stop_id,transfer_type\n"
            "DOESNOTEXIST,BULLFROG,2\n"
            ",BULLFROG,2\n"
            "BULLFROG,,2\n"
            "BULLFROG,DOESNOTEXISTEITHER,2\n"
            "DOESNOTEXIT,DOESNOTEXISTEITHER,2\n"
            ",,2\n")
        self.MakeLoaderAndLoad()
        # First row
        self.accumulator.pop_invalid_value('from_stop_id')
        # Second row
        self.accumulator.pop_missing_value('from_stop_id')
        # Third row
        self.accumulator.pop_missing_value('to_stop_id')
        # Fourth row
        self.accumulator.pop_invalid_value('to_stop_id')
        # Fifth row
        self.accumulator.pop_invalid_value('from_stop_id')
        self.accumulator.pop_invalid_value('to_stop_id')
        # Sixth row
        self.accumulator.pop_missing_value('from_stop_id')
        self.accumulator.pop_missing_value('to_stop_id')
        self.accumulator.assert_no_more_exceptions()

    def testDuplicateTransfer(self):
        self.AppendToArchiveContents(
            "stops.txt",
            "BEATTY_AIRPORT_HANGER,Airport Hanger,36.868178,-116.784915\n"
            "BEATTY_AIRPORT_34,Runway 34,36.85352,-116.786316\n")
        self.AppendToArchiveContents(
            "trips.txt",
            "AB,FULLW,AIR1\n")
        self.AppendToArchiveContents(
            "stop_times.txt",
            "AIR1,7:00:00,7:00:00,BEATTY_AIRPORT_HANGER,1\n"
            "AIR1,7:05:00,7:05:00,BEATTY_AIRPORT_34,2\n"
            "AIR1,7:10:00,7:10:00,BEATTY_AIRPORT_HANGER,3\n")
        self.SetArchiveContents(
            "transfers.txt",
            "from_stop_id,to_stop_id,transfer_type\n"
            "BEATTY_AIRPORT,BEATTY_AIRPORT_HANGER,0\n"
            "BEATTY_AIRPORT,BEATTY_AIRPORT_HANGER,3")
        schedule = self.MakeLoaderAndLoad()
        e = self.accumulator.PopException('DuplicateID')
        self.assertEquals('(from_stop_id, to_stop_id)', e.column_name)
        self.assertEquals('(BEATTY_AIRPORT, BEATTY_AIRPORT_HANGER)', e.value)
        self.assertTrue(e.is_warning())
        self.assertEquals('transfers.txt', e.file_name)
        self.assertEquals(3, e.row_num)
        self.accumulator.assert_no_more_exceptions()

        saved_schedule_file = StringIO()
        schedule.write_google_transit_feed(saved_schedule_file)
        self.accumulator.assert_no_more_exceptions()
        load_problems = util.get_test_failure_problem_reporter(
            self, ("ExpirationDate", "DuplicateID"))
        loaded_schedule = transitfeed.Loader(saved_schedule_file,
                                             loader_problems=load_problems,
                                             extra_validation=True).load()
        self.assertEquals(
            [0, 3],
            [int(t.transfer_type) for t in loaded_schedule.get_transfer_iter()])
