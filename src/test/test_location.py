'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 27 July 2023
@desc
    Let's just test the location class
'''
import unittest
from src.utils import Location

class TestLocation(unittest.TestCase):
    def test_ToLatLong(self):
        _loc = Location(6254.834*1000, 6862.875*1000, 6448.296*1000)
        _lat, _long, _alt = _loc.to_lat_long()

        _desiredLat = 34.8793622
        _desiredLong = 47.6539135
        _desiredAlt = 4933808.18
        
        self.assertAlmostEqual(_desiredLat, _lat, 2)
        self.assertAlmostEqual(_desiredLong, _long, 2)
        self.assertAlmostEqual(_desiredAlt, _alt, -2)