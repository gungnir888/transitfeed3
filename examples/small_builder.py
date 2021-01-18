# A really simple example of using transitfeed to build a Google Transit
# Feed Specification file.

import transitfeed
from optparse import OptionParser


parser = OptionParser()
parser.add_option('--output', dest='output',
                  help='Path of output file. Should end in .zip')
parser.set_defaults(output='google_transit.zip')
(options, args) = parser.parse_args()

schedule = transitfeed.Schedule()
schedule.add_agency("Fly Agency", "http://iflyagency.com", "America/Los_Angeles")

service_period = schedule.get_default_service_period()
service_period.set_weekday_service(True)
service_period.set_date_has_service('20070704')

stop1 = schedule.add_stop(lng=-122, lat=37.2, name="Suburbia")
stop2 = schedule.add_stop(lng=-122.001, lat=37.201, name="Civic Center")

route = schedule.add_route(short_name="22", long_name="Civic Center Express", route_type="Bus")

trip = route.add_trip(schedule, headsign="To Downtown")
trip.add_stop_time(stop1, stop_time='09:00:00')
trip.add_stop_time(stop2, stop_time='09:15:00')

trip = route.add_trip(schedule, headsign="To Suburbia")
trip.add_stop_time(stop1, stop_time='17:30:00')
trip.add_stop_time(stop2, stop_time='17:45:00')

schedule.validate()
schedule.write_google_transit_feed(options.output)
