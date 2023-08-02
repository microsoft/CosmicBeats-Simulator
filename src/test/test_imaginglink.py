'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 23 Dec 2022
@desc
    Let's test if the imaginglink class matches the data on page 6 at:
    https://digitalcommons.usu.edu/cgi/viewcontent.cgi?article=4405&context=smallsat
'''

import unittest
import os
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import EModelTag
from src.models.network.imaging.imaginglink import ImagingLink

class testimagingradiomodel(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator(os.path.join(os.getcwd(), "configs/testconfigs/config_testimaginglink.json"))
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        #Ignore the first satellite. It's not used in this test
        self.__sat = self.__topologies[0].get_Node(1)
        self.__gs = self.__topologies[0].get_Node(2)    
            
        #Let's get the radio models
        self.__satModel = self.__sat.has_ModelWithTag(EModelTag.IMAGINGRADIO)
        self.__gsModel = self.__gs.has_ModelWithTag(EModelTag.IMAGINGRADIO)
        
        #Get the radio devices
        self.__satRadio = self.__satModel.call_APIs("get_RadioDevice")
        self.__gsRadio = self.__gsModel.call_APIs("get_RadioDevice")
                        
    def nextStep(self) -> None:
        self.__manager.call_APIs("run_OneStep")
    
    def test_linkquality(self) -> None:
        #Let's test the link quality. This is the first column of the table
        _satLocation = self.__sat.get_Position()
        _gsLocation = self.__gs.get_Position()
        _distance = _satLocation.get_distance(_gsLocation)

        self.assertEqual(_distance, 1408*1000)
        
        _link = ImagingLink(self.__satRadio, self.__gsRadio, _distance)
         
        _desiredFSPL = 173.5
        self.assertAlmostEqual(_link.get_PropagationLoss(), _desiredFSPL, 0)
                
        _desiredSNR = 10.7 + .9 
        _diff = abs(_link.get_SNR() - _desiredSNR)
        print(_link.get_SNR(), _desiredSNR)
        print(_link.get_SNR(), _desiredSNR)
        self.assertLessEqual(_diff, 1.1)
        
        #Let's test the data rate. 
        _sizeInBytes = 64000/8
        _timeToTransmit = _link.get_TimeOnAir(_sizeInBytes) #this is msec
        _Bps = _sizeInBytes / (_timeToTransmit/1000) #this is bytes per second
        _Mbps = _Bps / 1000000 * 8
        
        #Take the uncoded data rate of one channel * coding rate * number of channels
        _desiredMbps = 228 * .75 * 6
        _diff = abs(_Mbps - _desiredMbps)
        self.assertLessEqual(_diff, 5) #5 Mbps error is acceptable
    
    @unittest.skip("This test must be verified by hand")
    def test_linkoverdistance(self):        
        #Let's make the same plot as on page 9 of the paper
        _rates = []
        _start = 2200*1000
        _end = 600*1000
        _delta = 1000
        _rng = range(_start, _end, -_delta)
        for _distance in _rng:
            _link = ImagingLink(self.__satRadio, self.__gsRadio, _distance)
            _sizeInBytes = 64000/8
            _timeToTransmit = _link.get_TimeOnAir(_sizeInBytes) #this is msec
            _Bps = _sizeInBytes / (_timeToTransmit/1000) #this is bytes per second
            _Mbps = _Bps / 1000000 * 8
            _rates.append(_Mbps)
        
        import matplotlib.pyplot as plt
        _kmVals = [x/1000 for x in _rng]
        plt.plot(_kmVals, _rates)
        plt.grid()
        #flip the x axis
        plt.gca().invert_xaxis()
        #Don't make the x axis scientific notation
        plt.ticklabel_format(style='plain')
        plt.xticks(rotation=45)
        
        plt.xlabel("Distance (km)")
        plt.ylabel("Mbps")
        plt.title("Data Rate Across All Channels vs Distance")
        plt.tight_layout()
        plt.savefig("test_linkoverdistance.png")