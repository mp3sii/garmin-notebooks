"""Class to parse and create a table with running activity"""
import datetime as dt
import math
from functools import reduce
from pathlib import Path
from typing import Literal
import matplotlib.pyplot as plt
import numpy as np

import fitfile
import folium
import pandas as pd
import snakemd
from garmindb.garmindb import Activities


class RunningActivity:
    """A class to represent running activities

    Attributes
    ----------
    _activity : garmindb.garmindb.Activities
        A Garmindb Activity

    Methods
    -------
    get_activity_summary_markdown()
        Returns a snakemd table with a summary of the running activity
    """

    def __init__(self, activity: Activities):
        self._activity = activity

    def get_activity_summary_markdown(self) -> snakemd.Table:
        """Produce a summary Table of the activity"""
        header = ["VARIABLE", "VAL"]
        values = [
            ("id", str(self._activity.activity_id)),
            ("name", self._activity.name),
            ("distance", f"{self._activity.distance:,.2f} km"),
            # ('avg pace':
            ("aerobic_training_effect", str(self._activity.training_effect)),
            (
                "anaerobic_training_effect",
                str(self._activity.anaerobic_training_effect),
            ),
            ("start_time", self._activity.start_time.strftime("%H:%M")),
            ("stop_time", self._activity.stop_time.strftime("%H:%M")),
            ("moving_time", self._activity.moving_time.strftime("%H:%M:%S")),
            ("avg_pace", self.calculate_pace_min_per_k(self._activity.avg_speed)),
            ("avg_hr", str(self._activity.avg_hr)),
            ("max_hr", str(self._activity.max_hr)),
            ("pct_zone_1", f"{self._calc_pct_in_zone(self._activity.hrz_1_time):.1f}%"),
            ("pct_zone_2", f"{self._calc_pct_in_zone(self._activity.hrz_2_time):.1f}%"),
            ("pct_zone_3", f"{self._calc_pct_in_zone(self._activity.hrz_3_time):.1f}%"),
            ("pct_zone_4", f"{self._calc_pct_in_zone(self._activity.hrz_4_time):.1f}%"),
            ("pct_zone_5", f"{self._calc_pct_in_zone(self._activity.hrz_5_time):.1f}%"),
        ]
        return snakemd.Table(
            header, values, [snakemd.Table.Align.LEFT, snakemd.Table.Align.RIGHT]
        )

    @classmethod
    def calculate_pace_min_per_k(cls, speed: float) -> str:
        """Calculates the pace in min per k

        Attributes
        ----------
        speed : float
            The speed in km per hour

        Returns
        -------
            A string with the pace in min per km
        """
        secs, minutes = math.modf(1 / speed * 60)
        return f"{int(minutes)}:{secs * 60:02.0f} min/km"

    @property
    def _total_hr_zone_times(self) -> dt.time:
        """Calculates the total time of all the hr zones"""
        time_list = [
            self._activity.hrz_1_time,
            self._activity.hrz_2_time,
            self._activity.hrz_3_time,
            self._activity.hrz_4_time,
            self._activity.hrz_5_time,
        ]
        delta = reduce(
            lambda x, y: x
                         + dt.timedelta(
                hours=y.hour,
                minutes=y.minute,
                seconds=y.second,
                microseconds=y.microsecond,
            ),
            time_list,
            dt.timedelta(seconds=0),
        )

        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return dt.time(hours, minutes, seconds)

    def _calc_pct_in_zone(self, time_in_zone: dt.time) -> float:
        def calc_secs(time: dt.time) -> int:
            return time.hour * 3600 + time.minute * 60 + time.second

        return 100 * calc_secs(time_in_zone) / calc_secs(self._total_hr_zone_times)

    @property
    def fit(self) -> fitfile.File:
        """Opens the fit file for this activity

        Assumes that the file will be located in ~/HealthData/FitFiles/Activities/
        """
        return fitfile.File(
            Path.home()
            / "HealthData"
            / "FitFiles"
            / "Activities"
            / f"{self._activity.activity_id}_ACTIVITY.fit"
        )

    def create_map(self,
                   tiles: Literal["Stamen Watercolor", "OpenStreetMap", "Stamen Terrain", "Stamen Toner"] = "Stamen Watercolor",
                   png_enabled: bool = False,
                   ) -> folium.Map:
        """Creates a folium map
    
        Create map with running route. It adds markers at start, end and each km.
    
        Parameters
        ----------
        self : RunningActivity
            A running activity
        tiles : TILES, optional
            A valid tile option, defaults to Stamen Watercolor
        png_enabled : int, optional
            if png is enabled instead of html (requires selenium and is slow), defaults to False.
    
        """
        # pylint: disable=no-member
        data = [dict(x.fields) for x in self.fit.record]
        # pylint: enable=no-member
        running_df: pd.DataFrame = pd.DataFrame(data).sort_values("timestamp")
        running_map = folium.Map(
            location=[self._activity.start_lat, self._activity.start_long],
            zoom_start=4,
            tiles=tiles,
            no_touch=True,
            zoom_control=False,
            png_enabled=png_enabled,
            width=1200,
            height=600,
        )
        start = folium.Marker(
            location=[self._activity.start_lat, self._activity.start_long],
            tooltip="start",
            color="black",
            icon=folium.Icon(icon="play", color="black", prefix="fa"),
        )
        start.add_to(running_map)
        end = folium.Marker(
            location=[self._activity.stop_lat, self._activity.stop_long],
            tooltip="start",
            color="black",
            icon=folium.Icon(icon="flag", color="black", prefix="fa"),
        )
        end.add_to(running_map)

        # Km markers, picks the closest to the km marker
        dist_markers = [
            folium.Marker(
                location=[
                    running_df.loc[running_df.distance <= x].tail(1).position_lat.values[0],
                    running_df.loc[running_df.distance <= x].tail(1).position_long.values[0],
                ],
                icon=folium.Icon(icon=f"{x}", prefix="fa", color="black"),
            )
            for x in range(1, int(self._activity.distance) + 1)
        ]

        if self._activity.distance >= 1:
            for marker in dist_markers:
                marker.add_to(running_map)

        positions = []
        # pylint: disable=no-member
        for rec in self.fit.record:
            if rec.fields.get("position_lat") and rec.fields.get("position_long"):
                positions.append(
                    [rec.fields.get("position_lat"), rec.fields.get("position_long")]
                )
        path = folium.PolyLine(positions, color="blue", weight=4, dashArray="0 10 0")
        path.add_to(running_map)
        # pylint: enable=no-member

        # Fit to the bounds
        running_map.fit_bounds(
            [
                (running_df.position_lat.min(), running_df.position_long.min()),
                (running_df.position_lat.max(), running_df.position_long.max()),
            ]
        )
        return running_map


    def create_zone_plot(self):
        x = 0.5 + np.arange(5)
        y = [self._calc_pct_in_zone(self._activity.hrz_1_time),
             self._calc_pct_in_zone(self._activity.hrz_2_time),
             self._calc_pct_in_zone(self._activity.hrz_3_time),
             self._calc_pct_in_zone(self._activity.hrz_4_time),
             self._calc_pct_in_zone(self._activity.hrz_5_time)
             ]

        fig, ax = plt.subplots()
        color = ['grey', 'green', 'yellow', 'orange', 'red']
        labels = [f'{data:.2f}' for data in y]

        p = ax.bar(x, y, width=1, edgecolor="white", linewidth=0.7, color=color)
        ax.bar_label(p, labels=labels, label_type='center', color='black')

        return plt.show()