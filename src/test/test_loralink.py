'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 23 Dec 2022
@desc
    Let's test if the lora matches the expected values. See page 31 of the following document:
    https://forum.nasaspaceflight.com/index.php?action=dlattach;topic=47072.0;attach=1538105;sess=0
'''

import unittest
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import IManager, EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import IModel, EModelTag
import os
from src.models.network.lora.loraradiodevice import LoraRadioDevice
from src.models.network.lora.loralink import LoraLink

class testloraradiomodel(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator(os.path.join(os.getcwd(), "configs/testconfigs/config_testloralink.json"))
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        self.__sat = self.__topologies[0].get_Node(1)
        self.__gs = self.__topologies[0].get_Node(2)    
            
        self.__satModel = self.__sat.has_ModelWithTag(EModelTag.BASICLORARADIO)
        self.__gsModel = self.__gs.has_ModelWithTag(EModelTag.BASICLORARADIO)
        
        #Get the radio devices
        self.__satRadio = self.__satModel.call_APIs("get_RadioDevice")
        self.__gsRadio = self.__gsModel.call_APIs("get_RadioDevice")
                
    def nextStep(self) -> None:
        self.__manager.call_APIs("run_OneStep")
    
    def test_linkquality(self) -> None:
        #Let's test the link quality from the satellite to the ground station (col 3 in the table)
        _satLocation = self.__sat.get_Position()
        _gsLocation = self.__gs.get_Position()
        _distance = _satLocation.get_distance(_gsLocation)

        self.assertEqual(_distance, 637*1000)
        
        _link = LoraLink(self.__satRadio, self.__gsRadio, _distance)
         
        _desiredFSPL = 131.33
        _calculatedFSPL = _link.get_PropagationLoss()
        _diff = abs(_desiredFSPL - _calculatedFSPL)
        self.assertLessEqual(_diff, 1)
                
        _desiredRSSI = -138.25
        _calculatedRSSI = _link.get_ReceivedSignalStrength()
        _diff = abs(_desiredRSSI - _calculatedRSSI)
        self.assertLessEqual(_diff, 1)
        print("SNR:", _link.get_SNR())
        
        
        #Try the other way around (col 1 in the table)
        _link = LoraLink(self.__gsRadio, self.__satRadio, _distance)
        
        _desiredFSPL = 131.99
        _calculatedFSPL = _link.get_PropagationLoss()
        _diff = abs(_desiredFSPL - _calculatedFSPL)
        self.assertLessEqual(_diff, 1)
        
        _desiredRSSI = -138.25
        _calculatedRSSI = _link.get_ReceivedSignalStrength()
        print(_desiredRSSI, _calculatedRSSI)
        _diff = abs(_desiredRSSI - _calculatedRSSI)
        self.assertLessEqual(_diff, 1)
        
        print("SNR:", _link.get_SNR())
    