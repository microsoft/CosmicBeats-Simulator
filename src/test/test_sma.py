'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 30 July 2023
@desc
    We conduct the unit test of the smas here. We have some sample strings
    which we will save to a file and then process them to get the smas. 
'''
import unittest
import pandas as pd
import os

from src.analytics.smas.smadatagenerator import init_SMADataGenerator
from src.analytics.smas.smadatastore import init_SMADataStore
from src.analytics.smas.smagenericradio import init_SMAGenericRadio
from src.analytics.smas.smaloraradiodevicetx import init_SMALoraRadioDeviceTx
from src.analytics.smas.smaloraradiodevicerx import init_SMALoraRadioDeviceRx
from src.analytics.smas.smapowerbasic import init_SMAPowerBasic

class TestSMAs(unittest.TestCase):
    def save_string_to_file(self, _string, _fileName):
        with open(_fileName, "w+") as f:
            f.write(_string)
            
    def test_smadatagenerator(self):
        _string = """
        logType, timestamp, modelName, message
        [ELogType.LOGINFO], 2023-07-06 00:05:48, ModelDataGenerator, "Generated dataID: 35. queueSize: 1"
        [ELogType.LOGINFO], 2023-07-06 00:02:58, ModelDataGenerator, "Generated dataID: 19. queueSize: 2"
        [ELogType.LOGINFO], 2023-07-06 00:09:04, ModelDataGenerator, "Generated dataID: 52. queueSize: 3"
        """
        _fileName = "Log_Constln1_0_IoT_136.log"
        self.save_string_to_file(_string, _fileName)
        
        #Now run the sma
        _sma = init_SMADataGenerator(modelLogPath = _fileName)
        _sma.Execute()
        _resultDf = _sma.get_Results()

        _desiredResultDf = pd.DataFrame(columns = ["timestamp", "action", "id", "queueSize", "sourceNodeID"])
        _desiredResultDf.loc[0] = ["2023-07-06 00:05:48", "Generated", 35, 1, 136]
        _desiredResultDf.loc[1] = ["2023-07-06 00:02:58", "Generated", 19, 2, 136]
        _desiredResultDf.loc[2] = ["2023-07-06 00:09:04", "Generated", 52, 3, 136]
        
        for i in range(len(_resultDf)):
            for j in range(len(_resultDf.columns)):
                self.assertEqual(str(_resultDf.iloc[i, j]), str(_desiredResultDf.iloc[i, j]))
        
        os.remove(_fileName)
        
    def test_smadatastore(self):
        _string = """
        logType, timestamp, modelName, message
        [ELogType.LOGINFO], 2023-07-06 00:09:22, ModelDataStore, "Queuing dataID: 12. creationTime: 2023-07-06 00:01:46. sourceNodeID: 942. timeDelay: 456.0. queueSize: 0"
        [ELogType.LOGINFO], 2023-07-06 00:09:22, ModelDataStore, "Current queue size: 1"
        [ELogType.LOGINFO], 2023-07-06 00:09:38, ModelDataStore, "Dropping dataID: 12. creationTime: 2023-07-06 00:01:46. sourceNodeID: 942. timeDelay: 472.0. queueSize: 1"
        [ELogType.LOGINFO], 2023-07-06 00:09:38, ModelDataStore, "Current queue size: 1"
        [ELogType.LOGINFO], 2023-07-06 00:09:54, ModelDataStore, "Dropping dataID: 24. creationTime: 2023-07-06 00:03:17. sourceNodeID: 139. timeDelay: 397.0. queueSize: 1"
        [ELogType.LOGINFO], 2023-07-06 00:09:54, ModelDataStore, "Current queue size: 1"
        """
        _fileName = "Log_Constln1_0_GS_105.log"
        self.save_string_to_file(_string, _fileName)
        
        _sma = init_SMADataStore(modelLogPath = _fileName)
        _sma.Execute()
        _resultDf = _sma.get_Results()
        
        _desiredResultDf = pd.DataFrame(columns = ["timestamp", "action", "dataID", "sourceNodeID", "creationTime", "timeDelay", "queueSize", "nodeID"])
        _desiredResultDf.loc[0] = ["2023-07-06 00:09:22", "Queuing", 12, 942, "2023-07-06 00:01:46", 456.0, 0, 105]
        _desiredResultDf.loc[1] = ["2023-07-06 00:09:38", "Dropping", 12, 942, "2023-07-06 00:01:46", 472.0, 1, 105]
        _desiredResultDf.loc[2] = ["2023-07-06 00:09:54", "Dropping", 24, 139, "2023-07-06 00:03:17", 397.0, 1, 105]
        
        for i in range(len(_resultDf)):
            for j in range(len(_resultDf.columns)):
                self.assertEqual(str(_resultDf.iloc[i, j]), str(_desiredResultDf.iloc[i, j]))
        
        os.remove(_fileName)
        
    def test_SMAGenericRadio(self):
        _string = """
        logType, timestamp, modelName, message
        [ELogType.LOGINFO], 2023-07-06 00:01:27, ModelDownlinkRadio, "Action: received. ObjectType: MACControl. ObjectID: 99. NodesInChannels: []. RxQueueSize: 1. TxQueueSize: 0"
        [ELogType.LOGINFO], 2023-07-06 00:01:27, ModelDownlinkRadio, "Action: dequeued. ObjectType: MACControl. ObjectID: 99. NodesInChannels: []. RxQueueSize: 1. TxQueueSize: 0"
        [ELogType.LOGINFO], 2023-07-06 00:01:27, ModelDownlinkRadio, "Action: noChannel. ObjectType: MACBeacon. ObjectID: 112. NodesInChannels: []. RxQueueSize: 0. TxQueueSize: 0"
        [ELogType.LOGINFO], 2023-07-06 00:01:33, ModelDownlinkRadio, "Action: received. ObjectType: MACBulkAck. ObjectID: 141. NodesInChannels: []. RxQueueSize: 1. TxQueueSize: 0"
        [ELogType.LOGINFO], 2023-07-06 00:03:56, ModelDownlinkRadio, "Action: sent. ObjectType: MACBeacon. ObjectID: 385. NodesInChannels: [0, 115]. RxQueueSize: 0. TxQueueSize: 0"
        """
        _fileName = "Log_Constln1_0_SAT_0.log"
        
        self.save_string_to_file(_string, _fileName)
        
        _sma = init_SMAGenericRadio(modelLogPath = _fileName, radioModelName = "ModelDownlinkRadio")
        _sma.Execute()
        _resultDf = _sma.get_Results()
        
        _desiredResultsDf = pd.DataFrame(columns = ["action", "objectType", "objectID", "nodesInView", "rxQueueSize", "txQueueSize", "timestamp", "nodeID"])
        _desiredResultsDf.loc[0] = ["received", "MACControl", 99, "", 1, 0, "2023-07-06 00:01:27", 0]
        _desiredResultsDf.loc[1] = ["dequeued", "MACControl", 99, "", 1, 0, "2023-07-06 00:01:27", 0]
        _desiredResultsDf.loc[2] = ["noChannel", "MACBeacon", 112, "", 0, 0, "2023-07-06 00:01:27", 0]
        _desiredResultsDf.loc[3] = ["received", "MACBulkAck", 141, "", 1, 0, "2023-07-06 00:01:33", 0]
        _desiredResultsDf.loc[4] = ["sent", "MACBeacon", 385, "0, 115", 0, 0, "2023-07-06 00:03:56", 0]
        
        for i in range(len(_resultDf)):
            for j in range(len(_resultDf.columns)):
                
                self.assertEqual(str(_resultDf.iloc[i, j]), str(_desiredResultsDf.iloc[i, j]))
        
        os.remove(_fileName)
        
    def test_smaloraradio(self):
        _string = """
        logType, timestamp, modelName, message
        [ELogType.LOGINFO], 2023-07-06 00:01:06, LoraRadioDevice, "Receiving. frameID: 4. success: True. collision: False. collisionFrameIDs: []. plrDrop: False. perDrop: False. txBusyDrop: False. crbwDrop: False. "
        [ELogType.LOGINFO], 2023-07-06 00:01:07, LoraRadioDevice, "Transmitting. frameID: 8. sourceAddress: 103. frameSize: 8. payloadSize: 8. mtuDrop: False. busyDrop: False. noValidChannelDrop: False. instanceIDs: [1, 2, 3, 4, 5, 6]. destinationNodeIDs: [17, 9, 20, 82, 51, 48]. destinationRadioIDs: [17, 9, 20, 82, 51, 48]. snrs: [14.778, 16.64, 14.852, 17.042, 21.205, 21.343]. secondsToTransmits: [2.0650, 2.0650, 2.0650, 2.0650, 2.0650, 2.0650]. plrs: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]. pers: [7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11]. "
        [ELogType.LOGINFO], 2023-07-06 00:03:40, LoraRadioDevice, "Receiving. frameID: 148. success: False. collision: True. collisionFrameIDs: [149]. plrDrop: False. perDrop: False. txBusyDrop: False. crbwDrop: False. "
        [ELogType.LOGINFO], 2023-07-06 00:03:42, LoraRadioDevice, "Receiving. frameID: 149. success: False. collision: True. collisionFrameIDs: [148]. plrDrop: False. perDrop: False. txBusyDrop: False. crbwDrop: False. "
        [ELogType.LOGINFO], 2023-07-06 00:03:57, LoraRadioDevice, "Receiving. frameID: 165. success: False. collision: True. collisionFrameIDs: [169]. plrDrop: False. perDrop: False. txBusyDrop: False. crbwDrop: False. "
        [ELogType.LOGINFO], 2023-07-06 00:03:59, LoraRadioDevice, "Receiving. frameID: 169. success: False. collision: True. collisionFrameIDs: [165]. plrDrop: False. perDrop: False. txBusyDrop: False. crbwDrop: False. "
        """
        _fileName = "Log_Constln1_0_GS_103.log"
        self.save_string_to_file(_string, _fileName)
        
        _txSMA = init_SMALoraRadioDeviceTx(modelLogPath = _fileName)
        _txSMA.Execute()
        _txResultDf = _txSMA.get_Results()
        
        #_columns are frameID,sourceAddress,frameSize,payloadSize,mtuDrop,busyDrop,noValidChannelDrop,instanceIDs,destinationNodeIDs,destinationRadioIDs,snrs,secondsToTransmits,plrs,pers,timestamp,nodeID
        _desiredTxResultDf = pd.DataFrame(columns = ["frameID", "sourceAddress", "frameSize", "payloadSize", "mtuDrop", "busyDrop", \
            "noValidChannelDrop", "instanceIDs", "destinationNodeIDs", "destinationRadioIDs", "snrs", "secondsToTransmits", "plrs", "pers", "timestamp", "nodeID"])
        _desiredTxResultDf.loc[0] = [8,103,8,8,False,False,False,"[1, 2, 3, 4, 5, 6]", "[17, 9, 20, 82, 51, 48]","[17, 9, 20, 82, 51, 48]", \
            "[14.778, 16.64, 14.852, 17.042, 21.205, 21.343]","[2.065, 2.065, 2.065, 2.065, 2.065, 2.065]","[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]", \
                "[7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11, 7.195667550324469e-11]", \
                    "2023-07-06 00:01:07",103]  
        
        for i in range(len(_txResultDf)):
            for j in range(len(_txResultDf.columns)):
                self.assertEqual(str(_txResultDf.iloc[i, j]), str(_desiredTxResultDf.iloc[i, j]))      
        
        _rxSMA = init_SMALoraRadioDeviceRx(modelLogPath = _fileName)
        _rxSMA.Execute()
        _rxResultDf = _rxSMA.get_Results()

        _desiredRxResultDf = pd.DataFrame(columns = ["frameID","success","collision","collisionFrameIDs","plrDrop","perDrop","txBusyDrop","crbwDrop","timestamp","nodeID"])
        _desiredRxResultDf.loc[0] = [4, True, False, [], False, False, False, False, "2023-07-06 00:01:06", 103]
        _desiredRxResultDf.loc[1] = [148, False, True, [149], False, False, False, False, "2023-07-06 00:03:40", 103]
        _desiredRxResultDf.loc[2] = [149, False, True, [148], False, False, False, False, "2023-07-06 00:03:42", 103]
        _desiredRxResultDf.loc[3] = [165, False, True, [169], False, False, False, False, "2023-07-06 00:03:57", 103]
        _desiredRxResultDf.loc[4] = [169, False, True, [165], False, False, False, False, "2023-07-06 00:03:59", 103]
        
        for i in range(len(_rxResultDf)):
            for j in range(len(_rxResultDf.columns)):
                self.assertEqual(str(_rxResultDf.iloc[i, j]), str(_desiredRxResultDf.iloc[i, j]))
                
        os.remove(_fileName)
        
    def test_powersma(self):
        _string = """
        logType, timestamp, modelName, message
        [ELogType.LOGWARN], 2023-07-06 00:00:00, ModelPower, "Power consumption tag RXRADIO not found in the requiredEnergy dictionary. Assuming this can always run if there is any power"
        [ELogType.LOGINFO], 2023-07-06 00:00:00, ModelPower, "PowerStats. CurrentCharge: [25306.612999999998] J. ChargeGenerated: [0.0] J. OutOfPower: [False]. Tag: [TXRADIO]. Requested: [False]. Granted: [None]. Consumed: [0]. Tag: [HEATER]. Requested: [False]. Granted: [None]. Consumed: [0.532]. Tag: [RXRADIO]. Requested: [True]. Granted: [True]. Consumed: [0.399]. Tag: [CONCENTRATOR]. Requested: [False]. Granted: [None]. Consumed: [0.266]. Tag: [GPS]. Requested: [False]. Granted: [None]. Consumed: [0.19]. Tag: [Other]. Requested: [False]. Granted: [None]. Consumed: [0]. "
        [ELogType.LOGINFO], 2023-07-06 00:00:01, ModelPower, "PowerStats. CurrentCharge: [25305.225999999995] J. ChargeGenerated: [0.0] J. OutOfPower: [False]. Tag: [TXRADIO]. Requested: [False]. Granted: [None]. Consumed: [0]. Tag: [HEATER]. Requested: [False]. Granted: [None]. Consumed: [0.532]. Tag: [RXRADIO]. Requested: [True]. Granted: [True]. Consumed: [0.399]. Tag: [CONCENTRATOR]. Requested: [False]. Granted: [None]. Consumed: [0.266]. Tag: [GPS]. Requested: [False]. Granted: [None]. Consumed: [0.19]. Tag: [Other]. Requested: [False]. Granted: [None]. Consumed: [0]. "
        [ELogType.LOGINFO], 2023-07-06 00:00:02, ModelPower, "PowerStats. CurrentCharge: [25303.838999999993] J. ChargeGenerated: [0.0] J. OutOfPower: [False]. Tag: [TXRADIO]. Requested: [False]. Granted: [None]. Consumed: [0]. Tag: [HEATER]. Requested: [False]. Granted: [None]. Consumed: [0.532]. Tag: [RXRADIO]. Requested: [True]. Granted: [True]. Consumed: [0.399]. Tag: [CONCENTRATOR]. Requested: [False]. Granted: [None]. Consumed: [0.266]. Tag: [GPS]. Requested: [False]. Granted: [None]. Consumed: [0.19]. Tag: [Other]. Requested: [False]. Granted: [None]. Consumed: [0]. "
        """
        
        _fileName = "Log_Constln1_0_SAT_0.log"
        self.save_string_to_file(_string, _fileName)
        
        _powerSMA = init_SMAPowerBasic(modelLogPath = _fileName)
        _powerSMA.Execute()
        _powerResultDf = _powerSMA.get_Results()
        
        #Yes, there are a lot of columns, but it is easier to put them here than nest them
        _desiredColumns = ["timestamp","currentCharge","chargeGenerated","outOfPower","tag0","requested0","granted0","consumed0", \
            "tag1","requested1","granted1","consumed1","tag2","requested2","granted2","consumed2","tag3","requested3","granted3", \
                "consumed3","tag4","requested4","granted4","consumed4","tag5","requested5","granted5","consumed5"]
        
        _desiredPowerResultDf = pd.DataFrame(columns = _desiredColumns)
        #0,2023-07-06 00:00:00,25306.613,0.0,False,TXRADIO,False,None,0,HEATER,False,None,0.532,RXRADIO,True,True,0.399,CONCENTRATOR,False,None,0.266,GPS,False,None,0.19,Other,False,None,0
        #1,2023-07-06 00:00:01,25305.225999999995,0.0,False,TXRADIO,False,None,0,HEATER,False,None,0.532,RXRADIO,True,True,0.399,CONCENTRATOR,False,None,0.266,GPS,False,None,0.19,Other,False,None,0
        #2,2023-07-06 00:00:02,25303.838999999996,0.0,False,TXRADIO,False,None,0,HEATER,False,None,0.532,RXRADIO,True,True,0.399,CONCENTRATOR,False,None,0.266,GPS,False,None,0.19,Other,False,None,0
        _desiredPowerResultDf.loc[0] = ["2023-07-06 00:00:00", 25306.613, 0.0, False, "TXRADIO", False, None, 0, "HEATER", False, None, 0.532, "RXRADIO", True, True, 0.399, "CONCENTRATOR", False, None, 0.266, "GPS", False, None, 0.19, "Other", False, None, 0]
        _desiredPowerResultDf.loc[1] = ["2023-07-06 00:00:01", 25305.226, 0.0, False, "TXRADIO", False, None, 0, "HEATER", False, None, 0.532, "RXRADIO", True, True, 0.399, "CONCENTRATOR", False, None, 0.266, "GPS", False, None, 0.19, "Other", False, None, 0]
        _desiredPowerResultDf.loc[2] = ["2023-07-06 00:00:02", 25303.839, 0.0, False, "TXRADIO", False, None, 0, "HEATER", False, None, 0.532, "RXRADIO", True, True, 0.399, "CONCENTRATOR", False, None, 0.266, "GPS", False, None, 0.19, "Other", False, None, 0]
        
        for i in range(len(_desiredPowerResultDf)):
            for j in range(len(_desiredPowerResultDf.columns)):
                #If the power is a float, then we need to check it with a tolerance
                if isinstance(_desiredPowerResultDf.iloc[i, j], float):
                    self.assertAlmostEqual(_powerResultDf.iloc[i, j], _desiredPowerResultDf.iloc[i, j], places = 3)
                else:
                    self.assertEqual(str(_powerResultDf.iloc[i, j]), str(_desiredPowerResultDf.iloc[i, j]))
                
        os.remove(_fileName)