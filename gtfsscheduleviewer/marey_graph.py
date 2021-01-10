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

"""Output svg/xml data for a marey graph

Marey graphs are a visualization form typically used for timetables. Time
is on the x-axis and position on the y-axis. This module reads data from a
transitfeed.Schedule and creates a marey graph in svg/xml format. The graph
shows the speed between stops for each trip of a route.

TODO: This module was taken from an internal Google tool. It works but is not
well intergrated into transitfeed and schedule_viewer. Also, it has lots of
ugly hacks to compensate set canvas size and so on which could be cleaned up.

For a little more information see (I didn't make this URL ;-)
http://transliteracies.english.ucsb.edu/post/research-project/research-clearinghouse-individual/research-reports/the-indexical-imagination-marey%e2%80%99s-graphic-method-and-the-technological-transformation-of-writing-in-the-nineteenth-century

  MareyGraph: Class, keeps cache of graph data and graph properties
               and draws marey graphs in svg/xml format on request.

"""
import transitfeed


class MareyGraph:
    """Produces and caches marey graph from transit feed data."""

    _MAX_ZOOM = 5.0  # change docstring of ChangeScaleFactor if this changes
    _DUMMY_SEPARATOR = 10  # pixel

    def __init__(self):
        # Timetablerelated state
        self._cache = ''
        self._stop_list = []
        self._trip_list = []
        self._stations = []
        self._decorators = []
        self._g_height = None
        self._g_width = None

        # TODO: Initialize default values via constructor parameters
        # or via a class constants

        # Graph properties
        self._tspan = 30  # number of hours to display
        self._offset = 0  # starting hour
        self._hour_grid = 60  # number of pixels for an hour
        self._min_grid = 5  # number of pixels between sub-hour lines

        # Canvas properties
        self._zoom_factor = 0.9  # svg Scaling factor
        self._x_offset = 0  # move graph horizontally
        self._y_offset = 0  # move graph vertically
        self._bg_color = "lightgrey"

        # height/width of graph canvas before transform
        self._g_width = self._tspan * self._hour_grid

    def draw(self, stop_list=None, trip_list=None, height=520):
        """Main interface for drawing the marey graph.

        If called without arguments, the data generated in the previous call
        will be used. New decorators can be added between calls.

        Args:
          # Class Stop is defined in transitfeed.py
          stop_list: [Stop, Stop, ...]
          # Class Trip is defined in transitfeed.py
          trip_list: [Trip, Trip, ...]
          height: TODO: Add desc

        Returns:
          # A string that contain a svg/xml web-page with a marey graph.
          " <svg  width="1440" height="520" version="1.1" ... "
        """
        if not trip_list:
            trip_list = []
        if not stop_list:
            stop_list = []

        if not self._cache or trip_list or stop_list:
            self._g_height = height
            self._trip_list = trip_list
            self._stop_list = stop_list
            self._decorators = []
            self._stations = self._build_stations(stop_list)
            self._cache = "%s %s %s %s" % (
                self._draw_box(),
                self._draw_hours(),
                self._draw_stations(),
                self._draw_trips(trip_list)
            )

        output = "%s %s %s %s" % (
            self._draw_header(),
            self._cache,
            self._draw_decorators(),
            self._draw_footer()
        )
        return output

    def _draw_header(self):
        svg_header = """
        <svg  width="%s" height="%s" version="1.1"
        xmlns="http://www.w3.org/2000/svg">
        <script type="text/ecmascript"><![CDATA[
            function init(evt) {
                if ( window.svgDocument == null ) {
                    svgDocument = evt.target.ownerDocument;
                }
            }
            var oldLine = 0;
            var oldStroke = 0;
            var hoffset= %s; // Data from python
    
            function parseLinePoints(pointnode) {
                var wordlist = pointnode.split(" ");
                var xlist = new Array();
                var h;
                var m;
                // TODO: add linebreaks as appropriate
                var xstr = "  Stop Times :";
                for (i=0;i<wordlist.length;i=i+2){
                    var coord = wordlist[i].split(",");
                    h = Math.floor(parseInt((coord[0])-20)/60);
                    m = parseInt((coord[0]-20))%%60;
                    xstr = xstr +" "+ (hoffset+h) +":"+m;
                }
                return xstr;
            }
    
            function LineClick(tripid, x) {
                var line = document.getElementById(tripid);
                if (oldLine) {
                    oldLine.setAttribute("stroke",oldStroke);
                    oldLine = line;
                    oldStroke = line.getAttribute("stroke");
                }
                line.setAttribute("stroke","#fff");
            
                var dynTxt = document.getElementById("dynamicText");
                var tripIdTxt = document.createTextNode(x);
                while (dynTxt.hasChildNodes()) {
                    dynTxt.removeChild(dynTxt.firstChild);
                }
                dynTxt.appendChild(tripIdTxt);
            }
        ]]></script>
        <style type="text/css"><![CDATA[
            .T { fill:none; stroke-width:1.5 }
            .TB { fill:none; stroke:#e20; stroke-width:2 }
            .Station { fill:none; stroke-width:1 }
            .Dec { fill:none; stroke-width:1.5 }
            .FullHour { fill:none; stroke:#eee; stroke-width:1 }
            .SubHour { fill:none; stroke:#ddd; stroke-width:1 }
            .Label { fill:#aaa; font-family:Helvetica,Arial,sans; text-anchor:middle }
            .Info { fill:#111; font-family:Helvetica,Arial,sans; text-anchor:start; }
        ]]></style>
        <text class="Info" id="dynamicText" x="0" y="%d"></text>
        <g id="mcanvas"  transform="translate(%s,%s)">
        <g id="zcanvas" transform="scale(%s)">
       """ % (
            self._g_width + self._x_offset + 20, self._g_height + 15,
            self._offset, self._g_height + 10,
            self._x_offset, self._y_offset, self._zoom_factor
        )
        return svg_header

    @staticmethod
    def _draw_footer():
        return "</g></g></svg>"

    def _draw_decorators(self):
        """Used to draw fancy overlays on trip graphs."""
        return " ".join(self._decorators)

    def _draw_box(self):
        tmp_str = """<rect x="%s" y="%s" width="%s" height="%s"
                fill="lightgrey" stroke="%s" stroke-width="2" />
             """ % (0, 0, self._g_width + 20, self._g_height, self._bg_color)
        return tmp_str

    def _build_stations(self, stop_list):
        """Dispatches the best algorithm for calculating station line position.

        Args:
          # Class Stop is defined in transitfeed.py
          stop_list: [Stop, Stop, ...]
          # Class Trip is defined in transitfeed.py

        Returns:
          # One integer y-coordinate for each station normalized between
          # 0 and X, where X is the height of the graph in pixels
          [0, 33, 140, ... , X]
        """
        # stations = [] TODO: What is this for
        dists = self._euclidian_distances(stop_list)
        stations = self._calculate_y_lines(dists)
        return stations

    @staticmethod
    def _euclidian_distances(stop_list):
        """Calculate euclidian distances between stops.

        Uses the stop_lists long/lats to approximate distances
        between stations and build a list with y-coordinates for the
        horizontal lines in the graph.

        Args:
          # Class Stop is defined in transitfeed.py
          stop_list: [Stop, Stop, ...]

        Returns:
          # One integer for each pair of stations
          # indicating the approximate distance
          [0,33,140, ... ,X]
        """
        e_dists2 = [transitfeed.approximate_distance_between_stops(stop, tail) for
                    (stop, tail) in zip(stop_list, stop_list[1:])]

        return e_dists2

    def _calculate_y_lines(self, dists):
        """Builds a list with y-coordinates for the horizontal lines in the graph.

        Args:
          # One integer for each pair of stations
          # indicating the approximate distance
          dists: [0,33,140, ... ,X]

        Returns:
          # One integer y-coordinate for each station normalized between
          # 0 and X, where X is the height of the graph in pixels
          [0, 33, 140, ... , X]
        """
        tot_dist = sum(dists)
        if tot_dist > 0:
            pixel_dist = [float(d * (self._g_height - 20)) / tot_dist for d in dists]
            pixel_grid = [0] + [int(pd + sum(pixel_dist[0:i])) for i, pd in
                                enumerate(pixel_dist)]
        else:
            pixel_grid = []

        return pixel_grid

    def _travel_times(self, trip_list, index=0):
        """ Calculate distances and plot stops.

        Uses a timetable to approximate distances
        between stations

        Args:
        # Class Trip is defined in transitfeed.py
        trip_list: [Trip, Trip, ...]
        # (Optional) Index of Triplist prefered for timetable Calculation
        index: 3

        Returns:
        # One integer for each pair of stations
        # indicating the approximate distance
        [0,33,140, ... ,X]
        """

        def distance_in_travel_time(dep_secs, arr_secs):
            t_dist = arr_secs - dep_secs
            if t_dist < 0:
                t_dist = self._DUMMY_SEPARATOR  # min separation
            return t_dist

        if not trip_list:
            return []

        if 0 < index < len(trip_list):
            trip = trip_list[index]
        else:
            trip = trip_list[0]

        t_dists2 = [distance_in_travel_time(stop[3], tail[2]) for (stop, tail)
                    in zip(trip.get_time_stops(), trip.get_time_stops()[1:])]
        return t_dists2

    @staticmethod
    def _add_warning(str_warning):
        print(str_warning)

    def _draw_trips(self, trip_list, colpar=""):
        """Generates svg polylines for each transit trip.

        Args:
          # Class Trip is defined in transitfeed.py
          [Trip, Trip, ...]

        Returns:
          # A string containing a polyline tag for each trip
          ' <polyline class="T" stroke="#336633" points="433,0 ...'
        """

        # stations = [] TODO: What is that for?
        if not self._stations and trip_list:
            self._stations = self._calculate_y_lines(self._travel_times(trip_list))
            if not self._stations:
                self._add_warning("Failed to use traveltimes for graph")
                self._stations = self._calculate_y_lines(self._uniform(trip_list))
                if not self._stations:
                    self._add_warning("Failed to calculate station distances")
                    return

        stations = self._stations
        tmp_str_list = []
        service_list = []
        for t in trip_list:
            if not colpar:
                if t.service_id not in service_list:
                    service_list.append(t.service_id)
                shade = int(service_list.index(t.service_id) * (200 / len(service_list)) + 55)
                color = "#00%s00" % hex(shade)[2:4]
            else:
                color = colpar

            start_offsets = [0]
            # first_stop = t.get_time_stops()[0] TODO: What is that for?

            for j, freq_offset in enumerate(start_offsets):
                if j > 0 and not colpar:
                    color = "purple"
                script_call = 'onmouseover="LineClick(\'%s\',\'Trip %s starting %s\')"' % (
                    t.trip_id,
                    t.trip_id,
                    transitfeed.format_seconds_since_midnight(t.get_start_time())
                )
                tmp_str_head = '<polyline class="T" id="%s" stroke="%s" %s points="' % (
                    str(t.trip_id), color, script_call
                )
                tmp_str_list.append(tmp_str_head)

                for i, s in enumerate(t.get_time_stops()):
                    arr_t = s[0]
                    dep_t = s[1]
                    if arr_t is None or dep_t is None:
                        continue
                    arr_x = int(arr_t / 3600.0 * self._hour_grid) - self._hour_grid * self._offset
                    dep_x = int(dep_t / 3600.0 * self._hour_grid) - self._hour_grid * self._offset
                    tmp_str_list.append("%s,%s " % (int(arr_x + 20), int(stations[i] + 20)))
                    tmp_str_list.append("%s,%s " % (int(dep_x + 20), int(stations[i] + 20)))
                tmp_str_list.append('" />')
        return "".join(tmp_str_list)

    @staticmethod
    def _uniform(trip_list):
        """Fallback to assuming uniform distance between stations"""
        # This should not be necessary, but we are in fallback mode
        longest = max([len(t.get_time_stops()) for t in trip_list])
        return [100] * longest

    def _draw_stations(self, color="#aaa"):
        """Generates svg with a horizontal line for each station/stop.

        Args:
          # Class Stop is defined in transitfeed.py

        Returns:
          # A string containing a polyline tag for each stop
          " <polyline class="Station" stroke="#336633" points="20,0 ..."
        """
        stations = self._stations
        tmp_str_list = []
        for y in stations:
            tmp_str_list.append('<polyline class="Station" stroke="%s" points="%s,%s, %s,%s" />' % (
                color, 20, 20 + y + .5, self._g_width + 20, 20 + y + .5
            ))
        return "".join(tmp_str_list)

    def _draw_hours(self):
        """Generates svg to show a vertical hour and sub-hour grid

        Returns:
          # A string containing a polyline tag for each grid line
          " <polyline class="FullHour" points="20,0 ..."
        """
        tmp_str_list = []
        for i in range(0, self._g_width, self._min_grid):
            if i % self._hour_grid == 0:
                tmp_str_list.append('<polyline class="FullHour" points="%d,%d, %d,%d" />' % (
                    i + .5 + 20, 20, i + .5 + 20, self._g_height))
                tmp_str_list.append('<text class="Label" x="%d" y="%d">%d</text>' % (
                    i + 20, 20, (i / self._hour_grid + self._offset) % 24))
            else:
                tmp_str_list.append('<polyline class="SubHour" points="%d,%d,%d,%d" />' % (
                    i + .5 + 20, 20, i + .5 + 20, self._g_height))
        return "".join(tmp_str_list)

    def add_station_decoration(self, index, color="#f00"):
        """Flushes existing decorations and highlights the given station-line.

        Args:
          # Integer, index of stop to be highlighted.
          index: 4
          # An optional string with a html color code
          color: "#fff"
        """
        tmp_str = ''
        num_stations = len(self._stations)
        ind = int(index)
        if self._stations:
            if 0 < ind < num_stations:
                y = self._stations[ind]
                tmp_str = '<polyline class="Dec" stroke="%s" points="%s,%s,%s,%s" />' % (
                    color, 20, 20 + y + .5, self._g_width + 20, 20 + y + .5
                )
        self._decorators.append(tmp_str)

    def add_trip_decoration(self, trip_list, color="#f00"):
        """Flushes existing decorations and highlights the given trips.

        Args:
          # Class Trip is defined in transitfeed.py
          trip_list: [Trip, Trip, ...]
          # An optional string with a html color code
          color: "#fff"
        """
        tmp_str = self._draw_trips(trip_list, color)
        self._decorators.append(tmp_str)

    def change_scale_factor(self, new_factor):
        """Changes the zoom of the graph manually.

        1.0 is the original canvas size.

        Args:
          # float value between 0.0 and 5.0
          new_factor: 0.7
        """
        if 0 < float(new_factor) < self._MAX_ZOOM:
            self._zoom_factor = new_factor

    def scale_larger(self):
        """Increases the zoom of the graph one step (0.1 units)."""
        new_factor = self._zoom_factor + 0.1
        if 0 < float(new_factor) < self._MAX_ZOOM:
            self._zoom_factor = new_factor

    def scale_smaller(self):
        """Decreases the zoom of the graph one step(0.1 units)."""
        new_factor = self._zoom_factor - 0.1
        if 0 < float(new_factor) < self._MAX_ZOOM:
            self._zoom_factor = new_factor

    def clear_decorators(self):
        """Removes all the current decorators.
        """
        self._decorators = []

    def add_text_strip_decoration(self, txtstr):
        tmp_str = '<text class="Info" x="%d" y="%d">%s</text>' % (
            0, 20 + self._g_height, txtstr
        )
        self._decorators.append(tmp_str)

    def set_span(self, first_arr, last_arr, mint=5, maxt=30):
        s_hour = (first_arr / 3600) - 1
        e_hour = (last_arr / 3600) + 1
        self._offset = max(min(s_hour, 23), 0)
        self._tspan = max(min(e_hour - s_hour, maxt), mint)
        self._g_width = self._tspan * self._hour_grid
