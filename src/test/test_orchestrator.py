'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 18 Oct 2022
@desc
    We conduct the unit test of the orchestrator class here 
'''

import unittest
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import IManager
from src.models.imodel import IModel, EModelTag

class TestOrchestrator(unittest.TestCase):
    def setUp(self) -> None:
        self.__orchestrator = Orchestrator("configs/testconfigs/config_testorchestrator.json")
        self.__orchestrator.create_SimEnv()

    
    def test_CreateSimEnv(self):
        __simEnv = self.__orchestrator.get_SimEnv()
        self.assertEqual(len(__simEnv[0]), 1)
        self.assertEqual(len(__simEnv[0][0].nodes), 3)
        self.assertEqual(__simEnv[0][0].nodes[0].iName, "SatelliteBasic")
        self.assertEqual(__simEnv[0][0].nodes[0].nodeID, 1)
        self.assertEqual(__simEnv[0][0].nodes[1].nodeID, 2)
    
    def test_ModelCreation(self):
        __simEnv = self.__orchestrator.get_SimEnv()
        self.assertTrue(__simEnv[0][0].nodes[0].has_ModelWithTag(EModelTag.ORBITAL) is not None)
        self.assertTrue(__simEnv[0][0].nodes[2].has_ModelWithTag(EModelTag.VIEWOFNODE) is not None)

    