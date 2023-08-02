'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 23 Dec 2022
@desc
    Just some test cases for the LoraRadioModel class
    Some of the test cases aren't realistic, but they are just to test the functionality, i.e. massive frame size
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
class testloraradiomodel(unittest.TestCase):
    def setUp(self) -> None:
        _orchestrator = Orchestrator(os.path.join(os.getcwd(), "configs/testconfigs/config_testlora.json"))
        _orchestrator.create_SimEnv()
        _simEnv = _orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(topologies = _simEnv[0], numOfSimSteps = _simEnv[1], numOfWorkers = 1)

        self.__topologies = self.__manager.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        self.__models = []
        self.__models.append(self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.BASICLORARADIO))
        self.__models.append(self.__topologies[0].nodes[1].has_ModelWithTag(EModelTag.BASICLORARADIO))
        self.__models.append(self.__topologies[0].nodes[2].has_ModelWithTag(EModelTag.BASICLORARADIO))
        
        self.__rxQueues = [i.call_APIs("get_RxQueue") for i in self.__models]
        self.__txQueues = [i.call_APIs("get_TxQueue") for i in self.__models]

        self.__topologies[0].nodes[0].has_ModelWithTag(EModelTag.ORBITAL).Execute()
        
    def nextStep(self) -> None:
        self.__manager.call_APIs("run_OneStep")
    
    def test_basic(self) -> None:
        # Let's just check that if we transmit from node 0 to node 1 and node2, we get a packet in the queue of node 1 and node 2
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
        
        _sentFrame = Frame(0, 100, payloadString="Test")
        self.__models[0].call_APIs("add_PacketToTransmit", _packet=_sentFrame)
        self.assertEqual(self.__txQueues[0].qsize(), 1)

        self.nextStep()
        self.nextStep()
        self.nextStep()
        self.nextStep()
        
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 1)
        self.assertEqual(self.__rxQueues[2].qsize(), 1)
        
        _receivedAtOne = self.__models[1].call_APIs("get_ReceivedPacket")
        _receivedAtTwo = self.__models[2].call_APIs("get_ReceivedPacket")
        
        self.assertEqual(_receivedAtOne, _sentFrame)
        self.assertEqual(_receivedAtTwo, _sentFrame)
        
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
    
    def test_collision(self) -> None:
        #lets check that if we transmit from node 1 and node 2 to node 0, we get a collision
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)

        self.__models[1].call_APIs("add_PacketToTransmit", _packet=Frame(0, 20, payloadString="Test"))
        self.__models[2].call_APIs("add_PacketToTransmit", _packet=Frame(0, 20, payloadString="Test"))
        self.assertEqual(self.__txQueues[1].qsize(), 1)
        self.assertEqual(self.__txQueues[2].qsize(), 1)

        self.nextStep()
        self.nextStep()

        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__txQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__txQueues[2].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
    
    def test_groundTransmit(self) -> None:
        # Let's just check that if we transmit from node 1 to node 0, we get a successful transmission
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
        
        self.__models[1].call_APIs("add_PacketToTransmit", _packet=Frame(0, 10, payloadString="Test"))
        self.assertEqual(self.__txQueues[1].qsize(), 1)

        #t= 0
        self.nextStep()
        #t = 1
        self.nextStep()
        
        self.assertEqual(self.__txQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 1)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)
        
    def test_overlapping_time(self) -> None:
        #This test is that if a packet takes more than one timestep to transmit, it is still received by the receiver at the appropriate time
        
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 0)

        #it's 255 bytes so it should take 4.something timesteps to transmit
        self.__models[0].call_APIs("add_PacketToTransmit", _packet=Frame(0, 255, payloadString=""))
        self.assertEqual(self.__txQueues[0].qsize(), 1)
        #let's transmit it (12:00:00)
        self.nextStep()
        
        #It should take 5 timesteps to transmit, so it should be received at 12:00:05
        for i in range(5):
            self.assertEqual(self.__txQueues[0].qsize(), 0)
            self.assertEqual(self.__rxQueues[0].qsize(), 0)
            self.assertEqual(self.__rxQueues[1].qsize(), 0)
            self.assertEqual(self.__rxQueues[2].qsize(), 0)
            self.nextStep()
        
        #Now it should be in the rx queue of both nodes (12:00:05)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 1)
        self.assertEqual(self.__rxQueues[2].qsize(), 1)

    def test_halfDuplex(self):
        #Let's check that if we transmit node 0 to node 1, and at the same time node 1 to node 0, nothing is received
        
        #Let's make sure that the queues are empty
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__txQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        
        _satFrame = Frame(0, 10)
        _groundFrame = Frame(1, 10)
        #Let's add to transmit
        self.__models[0].call_APIs("send_Packet", _packet=_satFrame)
        self.__models[1].call_APIs("send_Packet", _packet=_groundFrame)
        
        #Let's actually transmit it
        self.nextStep()
        self.nextStep()
        
        #Let's check that nothing is received at node 0 and node 1, but node 2 receives it
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__txQueues[1].qsize(), 0)
        self.assertEqual(self.__txQueues[2].qsize(), 0)
        
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 1)
        
        
        #Let's also check the same thing but with node 1 starting a second after node 0
        _satFrame = Frame(0, 255)
        _groundFrame = Frame(1, 255)
        
        self.__models[0].call_APIs("send_Packet", _packet=_satFrame)
        self.nextStep()
        self.__models[1].call_APIs("send_Packet", _packet=_groundFrame)
        self.nextStep()
        
        self.nextStep()
        self.nextStep()
        self.nextStep()
        self.nextStep()
        
        self.assertEqual(self.__txQueues[0].qsize(), 0)
        self.assertEqual(self.__txQueues[1].qsize(), 0)
        self.assertEqual(self.__txQueues[2].qsize(), 0)
        
        self.assertEqual(self.__rxQueues[0].qsize(), 0)
        self.assertEqual(self.__rxQueues[1].qsize(), 0)
        self.assertEqual(self.__rxQueues[2].qsize(), 2)
