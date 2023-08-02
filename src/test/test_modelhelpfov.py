'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 23 Dec 2022
@desc
    We conduct the unit test of the field of view helper model here.
    As the functionality of this model demands a mature simulation setup, we set up the same here.
'''

import unittest
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import IManager, EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import IModel, EModelTag
from src.nodes.itopology import ITopology
from src.nodes.inode import ENodeType

class TestModelHelperFoV(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator("configs/testconfigs/config_testmodelhelperfov.json")
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        # run the orbital model to update the position of a satellite
        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.ORBITAL).Execute()
        self.__topologies[0].nodes[1].has_ModelWithTag(EModelTag.ORBITAL).Execute()
    
    def test_get_View(self):
        _desiredResult = [[3, -19.279868415728256], 
                            [4, -6.47781766442099], 
                            [5, -15.249999282440179],
                            [6, 1.3183448569488105],
                            [7, -13.591257313017305],
                            [8, -27.306696675612574],
                            [9, -0.49842836843193666],
                            [10, 4.103873098364186],
                            [11, 3.8902260059766824],
                            [12, -25.92891116120493],
                            [13, -53.57128636153784],
                            [14, -51.71924016388395]]
        #_result is a list of nodes that are visible from the node with id 0
        _result = self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                                        "get_View", 
                                                                                        _isDownView = True,
                                                                                        _targetNodeTypes = [ENodeType.GS],
                                                                                        _myTime = None,
                                                                                        _myLocation = None)
        for i in range(len(_desiredResult)):
            if _desiredResult[i][1] > 0:
                self.assertIn(_desiredResult[i][0], _result)

        _desiredResult = [[1, -6.47781766442099], [2, -60.858417791668614]]
        _result = self.__topologies[0].nodes[3].has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                                        "get_View", 
                                                                                        _isDownView = False,
                                                                                        _targetNodeTypes = [ENodeType.SAT],
                                                                                        _myTime = None,
                                                                                        _myLocation = None)
        
        for i in range(len(_desiredResult)):
            if _desiredResult[i][1] > 0:
                self.assertIn(_desiredResult[i][0], _result)