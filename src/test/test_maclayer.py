'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 30 July 2023
@desc
    Let's test the mac layer protocol out. 
    This won't be an exhaustive test, but more to check if it's not completely broken. 
'''

from src.sim.simulator import Simulator
import os
import unittest
import time

class testmaclayer(unittest.TestCase):
    def setUp(self) -> None:
        _simulator = Simulator(os.path.join(os.getcwd(), "configs/testconfigs/config_testmaclayer.json"))
        _simulator.execute()
        #Delete the simulator once it's done. We need the logs to be flushed to the file
        del _simulator
        
    def string_IsInFile(self, _string: str, _file: str) -> bool:
        with open(_file, "r") as _f:
            _lines = _f.readlines()
            for _line in _lines:
                if _string in _line:
                    return True
        return False
    
    def test_output(self):
        time.sleep(1) #Wait for all the logs to be written to the file
        #There should be a folder called "macLayerTestLogs" in the current directory
        #Let's check that it exists
        self.assertTrue(os.path.isdir(os.path.join(os.getcwd(), "macLayerTestLogs")))
        
        #Now let's check that there are 3 files in the folder
        self.assertEqual(len(os.listdir(os.path.join(os.getcwd(), "macLayerTestLogs"))), 3)
        
        #Let's check that the files are named correctly
        _gsFile = "Log_Constln1_0_GS_3.log"
        _gsFullPath = os.path.join(os.getcwd(), "macLayerTestLogs", _gsFile)
        
        _iotFile = "Log_Constln1_0_IoT_2.log"
        _iotFullPath = os.path.join(os.getcwd(), "macLayerTestLogs", _iotFile)
        
        _satFile = "Log_Constln1_0_SAT_1.log"
        _satFullPath = os.path.join(os.getcwd(), "macLayerTestLogs", _satFile)
        
        self.assertTrue(os.path.isfile(_gsFullPath))
        self.assertTrue(os.path.isfile(_iotFullPath))
        self.assertTrue(os.path.isfile(_satFullPath))
        
        #Now let's check that the files have the correct data in them
        #Let's check that the satellite sent a beacon
        _desiredString = "Sending beacon"
        self.assertTrue(self.string_IsInFile("Sending beacon", _satFullPath))
        
        #Now, let's check that the iot device received the beacon
        _desiredString = "Beacons received"
        self.assertTrue(self.string_IsInFile(_desiredString, _iotFullPath))
        
        #Check that the iot device sent a packet
        _desiredString = "Transmitting"
        self.assertTrue(self.string_IsInFile(_desiredString, _iotFullPath))
        
        #Check that the satellite received the packet
        _desiredString = "Received MACData"
        self.assertTrue(self.string_IsInFile(_desiredString, _satFullPath))
        
        #Check that the satellite sent an ack
        _desiredString = "Sending ACK with"
        self.assertTrue(self.string_IsInFile(_desiredString, _satFullPath))
        
        #Check that the iot device received the ack
        _desiredString = "Ack received"
        self.assertTrue(self.string_IsInFile(_desiredString, _iotFullPath))
        
        #Check that the satellite received a control packet from the ground station
        _desiredString = "Received control packet"
        self.assertTrue(self.string_IsInFile(_desiredString, _satFullPath))
        
        #Check that the gs received data from the satellite
        _desiredString = "Received MACData"
        self.assertTrue(self.string_IsInFile(_desiredString, _gsFullPath))
        
        #Check that the sat received a bulk ack from the gs
        _desiredString = "Received ack MACBulkAck"
        self.assertTrue(self.string_IsInFile(_desiredString, _satFullPath))
        
        os.remove(_gsFullPath)
        os.remove(_iotFullPath)
        os.remove(_satFullPath)
        os.rmdir(os.path.join(os.getcwd(), "macLayerTestLogs"))