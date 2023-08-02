'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 23 Dec 2022
@desc
    We conduct the unit test of the field of view helper model here.
    This is for the time based field of view.
'''

import os
import unittest
import sys
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import EModelTag
from src.nodes.inode import ENodeType
from src.sim.simulator import Simulator
from time import time

class TestModelTimeBasedFOV(unittest.TestCase):
    def setUp(self) -> None: #not named setUp because some other tests don't need this
        _orchestrator = Orchestrator("configs/testconfigs/config_testmodelfovtime.json")
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)
        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
    
    def check_SatFOV(self, _modelVisible, _minAngle, _satPos):
        # This is a helper method to check if the FOV is working properly
        _gsNodes = [i for i in self.__topologies[0].nodes if i.nodeType == ENodeType.GS]
        _gsPositions = {_gsNode.nodeID: _gsNode.get_Position() for _gsNode in _gsNodes}
        _gsAngle = {id: _satPos.calculate_altitude_angle(_gsPos) for id, _gsPos in _gsPositions.items()}
        
        # there might be some difference in accuracy. Let's check the difference
        _fpIndex = [] #False positive (visible but not in ground truth)
        _fnIndex = [] #False negative (not visible but in ground truth)
        for i in range(len(_modelVisible)):
            if _gsAngle[_modelVisible[i]] < _minAngle:
                _fpIndex.append(i)
                
        for id, angle in _gsAngle.items():
            if angle > _minAngle and id not in _modelVisible:
                _fnIndex.append(id)
        
        print("Number of false positives: ", len(_fpIndex))
        print("Number of false negatives: ", len(_fnIndex))
        
        _anglesWithFP = [_gsAngle[_modelVisible[i]] for i in _fpIndex]
        _anglesWithFN = [_gsAngle[i] for i in _fnIndex]
        
        # let's make sure that the angles are within 5 degrees of the minimum angle
        self.assertTrue(all([i < _minAngle + 5 for i in _anglesWithFP]))
        self.assertTrue(all([i < _minAngle + 5 for i in _anglesWithFN]))
    
    def test_mainFeatures(self):
        # let's check the visibility of the GS from the satellite
        for i in range(10):
            self.__manager.call_APIs("run_OneStep")
            _modelVisible = self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                                            "get_View", 
                                                                                            _isDownView = True,
                                                                                            _targetNodeTypes = [ENodeType.GS],
                                                                                            _myTime = None,
                                                                                            _myLocation = None)
            self.check_SatFOV(_modelVisible, 0, self.__topologies[0].nodes[0].get_Position())
            _modelVisible = self.__topologies[0].nodes[1].has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                                            "get_View", 
                                                                                            _isDownView = True,
                                                                                            _targetNodeTypes = [ENodeType.GS],
                                                                                            _myTime = None,
                                                                                            _myLocation = None)
            
            #_modelVisible is a list of node IDs that are visible from the satellite
            self.check_SatFOV(_modelVisible, 0, self.__topologies[0].nodes[1].get_Position())
    
    @unittest.skipIf(sys.platform.startswith("win"), "Skipping this test on windows")
    def test_precompute(self):            
        _simulator = Simulator("configs/testconfigs/config_testmodelfovtime.json")
        _simulator.call_RuntimeAPIs("compute_FOVs")
        
        _fovs = []
        for i in range(10):
            _modelVisible = _simulator.call_RuntimeAPIs("call_ModelAPIsByModelName",
                            _topologyID = 0,
                            _nodeID = 1,
                            _modelName = "ModelFovTimeBased",
                            _apiName = "get_View",
                            _apiArgs = {
                                "_targetNodeTypes": [ENodeType.GS],
                                "_isDownView": True,
                                "_myTime": None,
                                "_myLocation": None       
                            }
                        )
            _fovs.append(_modelVisible)
                    
        #Now, let's go back to the default manager and see if the results are the same
        #We need to do this here because we need to control the positions of the satellite for every time step
        for i in range(10):
            self.__manager.call_APIs("run_OneStep")
            _satPos = self.__topologies[0].nodes[0].get_Position()
            self.check_SatFOV(_fovs[i], 0, _satPos)
            
        #Let's now delete the simulator so that the rest of the tests can run independently
        del _simulator
        
    def test_timing(self):
        # let's reset the simulation so that we can measure the run time of this model vs the helper model
        _orchestrator = Orchestrator("configs/testconfigs/config_testmodelfovtime.json")
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()
        
        _manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)
        self.__manager.call_APIs("run_OneStep")
        _topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        _startTime = time()
        for node in _topologies[0].nodes:
            if node.nodeType == ENodeType.SAT:
                node.has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                    "get_View", 
                                                                    _targetNodeTypes = [ENodeType.GS],
                                                                    _myTime = None)
            else:
                node.has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                    "get_View", 
                                                                    _targetNodeTypes = [ENodeType.SAT],
                                                                    _myTime = None)
        _endTime = time()
        _timeTaken = _endTime - _startTime #On my laptop it takes roughly 4.5 min
        print("Time to calculate the view of all nodes (1 hour sim, 10000 gs, 2 sat): ", _timeTaken, " seconds")
        
        # let's reset the simulation so that we can measure the run time of this model vs the helper model
        _orchestrator = Orchestrator("configs/testconfigs/config_testfovhelperlarge.json")
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()
        
        _manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)
        self.__manager.call_APIs("run_OneStep")
        _topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        _startTime = time()
        for node in _topologies[0].nodes:
            if node.nodeType == ENodeType.SAT:
                node.has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                    "get_View", 
                                                                    _targetNodeTypes = [ENodeType.GS],
                                                                    _myTime = None)
            else:
                node.has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                    "get_View", 
                                                                    _targetNodeTypes = [ENodeType.SAT],
                                                                    _myTime = None)
        _endTime = time()
        _otherTaken = _endTime - _startTime #On my laptop, it takes roughly 45 seconds
        
        print("Time to calculate the view of all nodes for one timestep (10000 gs, 2 sat): ", _otherTaken, " seconds")
        print("Ignoring multiprocessing, for the time based method to be faster, the simulation should be run with a timestep of ", _timeTaken/_otherTaken, " seconds")
        print("This will benefit more from multiprocessing. Please see the simulator APIs documentation for more information.")
        
    def tearDown(self) -> None:
        #Delete everything in the testLogs folder
        _dir = os.path.join(os.getcwd(), "testLogs")
        for _file in os.listdir(_dir):
            _path = os.path.join(_dir, _file)
            os.remove(_path)
        os.rmdir(_dir)