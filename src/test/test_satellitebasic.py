'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 13 Oct 2022
@desc
    We conduct the unit test here for SatelliteBasic class
'''

from pyexpat import model
import unittest
from src.models.imodel import EModelTag
from src.simlogging.ilogger import ELogType, ILogger
from src.simlogging.loggercmd import LoggerCmd
from src.nodes.satellitebasic import SatelliteBasic
from src.utils import Location, Time
from src.models.models_orbital.modelorbit import ModelOrbit

class TestSatelliteBasic(unittest.TestCase):

    def setUp(self) -> None:
        _logger = LoggerCmd(ELogType.LOGALL, 'SatelliteBasicTest')
        self.__time = Time().from_str("2022-10-11 12:00:00")
        self.__endtime = Time().from_str("2022-10-11 12:00:30")
        _tlelines = ["1 50985U 22002B   22290.71715197  .00032099  00000+0  13424-2 0  9994", "2 50985  97.4784 357.5505 0011839 353.6613   6.4472 15.23462773 42039"]
        self.__sat = SatelliteBasic(0 , 0, _tlelines[0], _tlelines[1], 10, self.__time.copy(), self.__endtime.copy(), _logger)
        
        _models = list()
        _models.append(ModelOrbit(self.__sat, _logger))
        
        self.__sat.add_Models(_models)

        self.__sat.ExecuteCntd()
    
    
    def test_OrbitModel(self):
        _testTime = Time().from_str("2022-10-11 12:00:30")
        _testTargetLoc = Location(4254212.590504601, -1566798.705286896, 5166824.198105468)
        _testRetLocation = self.__sat.get_Position(_testTime)
        
        #Within 10m (way less than the error in the model)
        self.assertAlmostEquals(_testRetLocation.x, _testTargetLoc.x, delta=10)
        self.assertAlmostEquals(_testRetLocation.y, _testTargetLoc.y, delta=10)
        self.assertAlmostEquals(_testRetLocation.z, _testTargetLoc.z, delta=10)    
            
    def test_HasModel(self):
        _retModel = self.__sat.has_ModelWithTag(EModelTag.ORBITAL)
        self.assertTrue(_retModel.modelTag == EModelTag.ORBITAL)

    
    def test_Position(self):
        _position = Location().from_lat_long(1.0, 2.0, 3.0)
        _time = Time().from_str("2022-10-11 12:00:30")

        self.__sat.update_Position(_position, _time)

        _lat, _long, _elv  = self.__sat.get_Position(_time).to_lat_long()

        self.assertEqual(_lat, 1.0)
        self.assertEqual(_long, 2.0)
        self.assertEqual(_elv, 3.0)