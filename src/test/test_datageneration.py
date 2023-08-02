'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 17 March 2023
@desc
    This module implements the test cases for the data generation model
    Since this is a random process, we will check that over many timesteps,
    the expected number of frames generated approximately matches the expected value (set to 5 per second in this case)
'''

import unittest
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import IManager, EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import IModel, EModelTag
from src.nodes.itopology import ITopology
from src.nodes.inode import ENodeType
from src.models.network.frame import Frame
import os
import numpy as np

class testdatagenerationmodel(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator(os.path.join(os.getcwd(), "configs/testconfigs/config_testgenerator.json"))
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        self.__model = self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.DATAGENERATOR)
                
    def test_basic(self) -> None:
        #Since this is a random process, let's check that the expected number of frames generated is 5 per second
        
        _dataQueue = self.__model.call_APIs("get_Queue") 
        self.assertEqual(_dataQueue.qsize(), 0)
        
        _atEachStep = [0] #list of number of frames generated at each step (expected 5*500 = 2500 frames)
        for i in range(0, 500):
            self.__model.Execute()
            _atEachStep.append(_dataQueue.qsize())
        print(_atEachStep[-1])
        
        #let's find the average difference between the number of frames generated at each step
        _diff = [_atEachStep[i+1] - _atEachStep[i] for i in range(0, len(_atEachStep)-1)]
        _avgDiff = sum(_diff)/len(_diff)
        self.assertAlmostEqual(_avgDiff, 5, delta=0.5)
        
        #let's also test that the max holds true
        #we expect the max to be 3000 frames. Let's add extra frames and check that the max holds true
        for i in range(0, 500): 
            self.__model.Execute()
            
        self.assertEqual(self.__model.call_APIs("get_QueueSize"), 3000)