'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 27 July 2023
@desc
    Just some test cases for the ImagingRadio model.
    These are very similar to the lora ones. 
'''
import os
import unittest
from src.models.network.frame import Frame
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import IManager, EManagerReqType
from src.sim.managerparallel import ManagerParallel
from src.models.imodel import IModel, EModelTag

class testimagingradiomodel(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator(os.path.join(os.getcwd(), "configs/testconfigs/config_testimaginglink.json"))
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        self.__models = []
        self.__models.append(self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.IMAGINGRADIO))
        self.__models.append(self.__topologies[0].nodes[1].has_ModelWithTag(EModelTag.IMAGINGRADIO))
        self.__models.append(self.__topologies[0].nodes[2].has_ModelWithTag(EModelTag.IMAGINGRADIO))
        
        self.__rxQueues = [i.call_APIs("get_RxQueue") for i in self.__models]
        self.__txQueues = [i.call_APIs("get_TxQueue") for i in self.__models]

        self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.ORBITAL).Execute()

    def test_basic(self) -> None:
        # Let's just check that if we transmit from node 0 to node 1, we get a packet in the queue of node 1 
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
        
        _sentFrame = Frame(0, 100, payloadString="Test")
        self.__models[0].call_APIs("send_Packet", _packet=_sentFrame)

        self.__manager.call_APIs("run_OneStep")
        self.__manager.call_APIs("run_OneStep")
        self.__manager.call_APIs("run_OneStep")
        self.__manager.call_APIs("run_OneStep")
        
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 1)
        
        _receivedAtGS = self.__models[2].call_APIs("get_ReceivedPacket")
        self.assertEqual(_receivedAtGS, _sentFrame)
        
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
    
    def test_collision(self) -> None:
        #Let's also just check that collision handling works
        _sentFrame = Frame(0, 1000, payloadString="Test")
        _sentFrame2 = Frame(0, 1000, payloadString="Test2")
        
        self.__models[0].call_APIs("send_Packet", _packet=_sentFrame)
        self.__models[1].call_APIs("send_Packet", _packet=_sentFrame2)
        
        self.__manager.call_APIs("run_OneStep")
        self.__manager.call_APIs("run_OneStep")
        self.__manager.call_APIs("run_OneStep")
        self.__manager.call_APIs("run_OneStep")
        
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__txQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
        
        self.assertEqual(self.__models[2].call_APIs("get_ReceivedPacket"), None)