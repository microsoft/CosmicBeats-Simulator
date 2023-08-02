'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
'''

from datetime import datetime, timedelta, timezone
from typing import Tuple, List

from astropy.coordinates import EarthLocation, ITRS, AltAz, CIRS # type: ignore
from astropy import units as astropyUnit # type: ignore
import numpy.linalg as la # type: ignore
import numpy as np

class Time:
    """
    Wrapper from datetime class cause python datetime can be annoying at times.

    Attributes:
        time (datetime) - All times here are UTC!
    """
    def __init__(self) -> None:
        pass

    def copy(self) -> 'Time':
        """
        Returns another time object with same date
        """
        return Time().from_datetime(self.time) # deep copy

    def from_str(self, time: str, format: str = "%Y-%m-%d %H:%M:%S") -> 'Time':
        """
        Gets time from specified format

        Arguments:
            time (str) - time in format specified by second input
            format (str) - format string, by default YYYY-MM-DD HH:MM:SS
        """
        self.time = datetime.strptime(time, format)
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self

    def to_str(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Outputs time in format YYYY-MM-DD HH:MM:SS by default

        Arguments:
            format (str) - optional format string to change default
        """
        #If there's microseconds, then add it to the format
        if self.time.microsecond != 0:
            format += ".%f"
        return self.time.strftime(format)

    def from_datetime(self, time: datetime) -> 'Time':
        self.time = time
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self
    
    def from_unix(self, unix: float) -> 'Time':
        self.time = datetime.utcfromtimestamp(unix)
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self
    
    def to_unix(self) -> float:
        """
        Returns time in unix time (UTC)
        """
        assert self.time.tzinfo == timezone.utc, "Time object is not in UTC"
        return self.time.timestamp()
    
    def difference_in_seconds(time1: 'Time' , time2: 'Time') -> float:
        """
        Finds the difference between two time objects. Finds time1 - time2

        Arguments:
            time1 (Time) - time object
            time2 (Time) - time object
        """
        return (time1.time - time2.time).total_seconds()

    def to_datetime(self) -> datetime:
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self.time

    def add_seconds(self, second: float) -> 'Time':
        """
        Updates self by this number of seconds

        Arguments:
            second (float)
        """
        self.time = self.time + timedelta(seconds = second)
        return self

    ##Operators:
    def __lt__(self, other):
        return (self.time < other.time)

    def __le__(self, other):
        return(self.time <= other.time)

    def __gt__(self, other):
        return(self.time > other.time)

    def __ge__(self, other):
        return(self.time >= other.time)

    def __eq__(self, other):
        return (self.time == other.time)

    def __ne__(self, other):
        return not(self.__eq__(self, other))

    def __str__(self) -> str:
        return self.to_str()
    
    def __repr__(self) -> str:
        return self.to_str()
    
    def __hash__(self) -> int:
        return hash(self.time)

class Location:
    """
    Location class in ITRF Frame

    Attributes:
        x (float) - meters
        y (float) - meters
        z (float) - meters
    """
    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        self.x = x
        self.y = y
        self.z = z


    def from_lat_long(self, lat: float, lon: float, elev: float = 0) -> 'Location':
        """
        Converts location from WGS84 lat, long, height to x, y, z in ITRF

        Arguments:
            lat (float) - latitude in degrees
            lon (float) - longitude in degrees
            elev (float)- elevation in meters relative to WGS84's ground.
        Returns:
            Location at point (self)
        """
        earthLoc = EarthLocation.from_geodetic(lon=lon, lat=lat,  height=elev, ellipsoid='WGS84').get_itrs() #Idk why they have this order, but it takes lon, lat.Also elev is distance above WGS reference, so like 0 is sea level

        self.x = float(earthLoc.x.value)
        self.y = float(earthLoc.y.value)
        self.z = float(earthLoc.z.value)
        return self

    def to_lat_long(self) -> 'Tuple[float, float, float]':
        """
        Returns lat, long, and elevation (WGS 84 output)

        Returns:
            Tuple (float, float, float) - lat, long, elevation in (deg, deg, m)

        """
        #Original astropy way. This is probably much slower than algo 13 in Vallado but it's fine for now
        geoCentric = EarthLocation.from_geocentric(x = self.x, y = self.y, z = self.z, unit=astropyUnit.m)

        lat = round(geoCentric.lat.value, 4) ##round all of these to four decimal places
        lon = round(geoCentric.lon.value, 4)
        elev = round(geoCentric.height.value, 4)
        return (lat, lon, elev)        
    
    def to_alt_az(self, groundPoint: 'Location', time: 'Time') -> 'Tuple[float, float, float]':
        """
        Converts this location (self) to get the alt, az, and elevation relative to this point

        Arguments:
            groundPoint (Location) - location of ground point
            time (Time) - time when calculation needed
        Returns:
            tuple (float, float, float) - (alt, az, distance) in (degrees, degrees, and meters)
        Raise:
            ValueError - if input location and self are the same
        """
        if self == groundPoint:
            raise ValueError("Location of object and ground are the same")

        #based on https://docs.astropy.org/en/stable/coordinates/common_errors.html

        t = time.to_datetime()
        sat = EarthLocation.from_geocentric(x = self.x, y = self.y, z = self.z, unit=astropyUnit.m)
        ground = EarthLocation.from_geocentric(x = groundPoint.x, y = groundPoint.y, z = groundPoint.z, unit = astropyUnit.m)
        itrs_vec = sat.get_itrs().cartesian - ground.get_itrs().cartesian
        cirs_vec = ITRS(itrs_vec, obstime=t).transform_to(CIRS(obstime=t)).cartesian
        cirs_topo = CIRS(cirs_vec, obstime=t, location=ground)
        altAz = cirs_topo.transform_to(AltAz(obstime=t, location=ground))

        return (altAz.alt.value, altAz.az.value, altAz.distance.value)

    def calculate_altitude_angle(self, groundPoint: 'Location') -> float:
        """
        Calculates the altitude angle for self at the groundPoint

        Arguments:
            self (Location) - location of satellite
            groundPoint (Location) - point where you want the altitude at
        Returns:
            float - angle in degrees
        """
        #eqn 1 in https://arxiv.org/pdf/1611.02402.pdf
        rSat = np.array(self.to_tuple())
        rGround = np.array(groundPoint.to_tuple())
        delR = rSat - rGround
        r0Ground = rGround/np.linalg.norm(rGround, ord = 2)
        val = np.dot(delR, r0Ground)/np.linalg.norm(delR, ord=2)
        return np.arcsin(val)*180/np.pi

    def get_radius(self) -> float:
        """
        Gets the height above Earth's center of mass in m
        """
        return float(la.norm(self.to_tuple(), ord = 2)); #numpy norm

    def to_tuple(self) -> 'Tuple[float, float, float]':
        return (self.x, self.y, self.z)

    def to_str(self) -> str:
        return "(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"

    def get_distance(self, other: 'Location') -> float:
        """
        Return distance in m from this point to another

        Arguments:
            other (Location) - other object
        Returns:
            float - (distance in m)
        """
        return float(np.sqrt( (self.x - other.x)** 2 + (self.y - other.y)** 2 + (self.z - other.z)** 2 ))
    
    @staticmethod
    def multiple_to_lat_long(locs: 'List[Location]') -> 'Tuple[List[float], List[float], List[float]]':
        """
        Returns lat, long, and elevation (WGS 84 output) of all of the locations. Faster than each one seperately
        Arguments:
            List[Location]
        Returns:
            Tuple (List[float], List[float], List[float]) - lat, long, elevation in (deg, deg, m)

        """
        xLst, yLst, zLst = zip(*[(pos.x, pos.y, pos.z) for pos in locs])
        geoCentric = EarthLocation.from_geocentric(x = xLst, y = yLst, z = zLst, unit=astropyUnit.m)

        lat = np.round(geoCentric.lat.value, 4).tolist()
        lon = np.round(geoCentric.lon.value, 4).tolist()
        elev = np.round(geoCentric.height.value, 4).tolist()

        return (lat, lon, elev)
    
    @staticmethod
    def multiple_from_lat_long(latLst: 'List[float]', lonLst: 'List[float]', elevLst: 'List[float]') -> 'List[Location]':
        """
        Returns a list of locations from lat, long, and elevation (WGS 84 input). Take a look in from_lat_long for more info

        Arguments:
            List[float] - latitudes (deg)
            List[float] - longitudes (deg)
            List[float] - elevations (m)
        Returns:
            List[Location] - locations
        """
        earthLoc = EarthLocation.from_geodetic(lon=lonLst, lat=latLst,  height=elevLst, ellipsoid='WGS84').get_itrs() #Idk why they have this order, but it takes lon, lat.Also elev is distance above WGS reference, so like 0 is sea level

        xLst = np.round(earthLoc.x.value, 4).tolist()
        yLst = np.round(earthLoc.y.value, 4).tolist()
        zLst = np.round(earthLoc.z.value, 4).tolist()

        return [Location(x, y, z) for x, y, z in zip(xLst, yLst, zLst)]