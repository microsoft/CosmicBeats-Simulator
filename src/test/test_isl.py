'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 5 May 2023
@desc
    Just some test cases for the ISL class
'''

import unittest
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import EModelTag
from src.models.network.frame import Frame
import os
from src.models.network.address import Address

class testisl(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator(os.path.join(os.getcwd(), "configs/testconfigs/config_testisl.json"))
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)

        self.__models = []
        self.__models.append(self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.ISL))
        self.__models.append(self.__topologies[0].nodes[1].has_ModelWithTag(EModelTag.ISL))
        self.__models.append(self.__topologies[0].nodes[2].has_ModelWithTag(EModelTag.ISL))
        
        self.__rxQueues = [i.call_APIs("get_RxQueue") for i in self.__models]

        self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.ORBITAL).Execute()
        self.__topologies[0].nodes[1].has_ModelWithTag(EModelTag.ORBITAL).Execute()
        self.__topologies[0].nodes[2].has_ModelWithTag(EModelTag.ORBITAL).Execute()
        
    def nextStep(self) -> None:
        self.__manager.call_APIs("run_OneStep")
        
    def test_basic(self) -> None:
        # Let's just check that if we transmit from node 0 to node 1 and node2, we get a packet in the queue of node 1 and node 2
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)

        self.nextStep()
        #so at this point, the orbital model has executed and the ISL model has executed for 18:30 and now it is 18:31
        
        self.__models[0].call_APIs("send_Packet", _packet=Frame(0, 100, payloadString="Test"), _destAddr=Address(2)) #(addresses are 1-indexed)
        self.nextStep()
        self.nextStep()
        
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 1)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
        
        _frame = Frame(0, 100, payloadString="Test")
        self.__models[1].call_APIs("send_Packet", _packet=_frame, _destAddr=Address(1))
        self.nextStep()
        self.nextStep()
        
        self.assertEqual(self.__rxQueues[0].qsize(), 1)
        self.assertEqual(self.__rxQueues[1].qsize(), 1)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
        
        _receivedFrame = self.__models[0].call_APIs("get_ReceivedPacket") 
        self.assertEqual(_receivedFrame, _frame) 