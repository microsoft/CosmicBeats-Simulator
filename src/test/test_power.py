'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: July 11, 2023
@desc
    We test out the power consumption of the system.
'''

import os
import unittest
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import EModelTag

#for sunlight test:
from skyfield.api import load, EarthSatellite

class testpower(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator(os.path.join(os.getcwd(), "configs/testconfigs/config_testpower.json"))
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        self.__models = []
        self.__models.append(self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.POWER))
    
    def test_basic(self) -> None:
        
        #let's check that the power model is working
        #let's first check that the amount of power is correct when loaded
        currPower = 7030*0.001*3600 
        self.assertEqual(self.__models[0].call_APIs("get_AvailableEnergy"), currPower)
        
        #let's check that if we use transmit power for one second, the amount of power is correct
        ret = self.__models[0].call_APIs("consume_Energy", _tag="TXRADIO", _duration=1)
        self.assertTrue(ret)
        currPower -= 532 * 1 * 0.001
        self.assertAlmostEquals(self.__models[0].call_APIs("get_AvailableEnergy"), currPower)
        
        self.__manager.call_APIs("run_OneStep") #the satellite should be in the sun, so the power should be the maximum
        
        #satellite should gain some power
        currPower += 1667.667 * 5 * 0.001
        currPower = min(currPower, 7030*0.001*3600)
        #but also lose some power due to necessary operations
        currPower -= (190 + 133 + 532 + 266) * 0.001 * 5
        
        #check that the power is within 1% of the expected value
        self.assertEqual(round(self.__models[0].call_APIs("get_AvailableEnergy")), round(currPower))
        
        #let's check that if we use transmit power for 1 million seconds, no power is consumed and the function returns false
        ret = self.__models[0].call_APIs("consume_Energy", _tag="TXRADIO", _duration=1000000)
        self.assertFalse(ret)
        self.assertEqual(round(self.__models[0].call_APIs("get_AvailableEnergy")), round(currPower))
        
    def test_Sunlight(self):
        #Let's check that the sunlight calculations are correct
        #Going off of: https://rhodesmill.org/skyfield/earth-satellites.html
        eph = load('dependencies/de440s.bsp')
        ts = load.timescale()
        
        tle_1 = "1 50985U 22002B   22290.71715197  .00032099  00000+0  13424-2 0  9994"
        tle_2 = "2 50985  97.4784 357.5505 0011839 353.6613   6.4472 15.23462773 42039"
        satellite = EarthSatellite(tle_1, tle_2, 'samplesat', ts)
        
        times = ts.utc(2022, 11, 14, 12, 0, range(0, 2*60*60, 5))
        sunlits = satellite.at(times).is_sunlit(eph)
        #Now, let's check the model orbit and see if the results match
        modelOrbit = self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.ORBITAL)
        
        for i in range(0, len(sunlits)):
            self.__manager.call_APIs("run_OneStep")
            _modelSunlit = modelOrbit.call_APIs("in_Sunlight")
            
            #The sunlit might be off by a a timestep, so let's check if it's within 1 timestep
            _sunlitCorrect = sunlits[i] == _modelSunlit or sunlits[i-1] == _modelSunlit or sunlits[i+1] == _modelSunlit
            self.assertTrue(_sunlitCorrect)
        