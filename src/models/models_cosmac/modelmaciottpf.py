'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
Updated: 2024

@desc
    This model implements the CosMAC (Constellation-Aware Medium Access and Scheduling for IoT Satellites) 
    MAC IoT with Transmission Probability Function (TPF) protocol.
    Based on the paper: https://deepakv.web.illinois.edu/assets/papers/CosMAC_MobiCom_2024.pdf
    
    This model controls IoT device behavior using a transmission probability function approach.
    It implements a simplified version of the CosMAC protocol with:
    1. Beacon-based transmission scheduling
    2. Probabilistic transmission decisions based on device count
    3. Acknowledgment-based reliability
    4. Fixed alpha parameter (no adaptive tuning)
    
    The model operates through a 6-state machine similar to ModelCosmacIoT but with
    simpler probability calculations and fixed parameters.
'''
from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.network.macdata.macbeacon import MACBeacon
from src.models.network.macdata.macdata import MACData
from src.models.network.macdata.macack import MACAck

import random
import pickle
import numpy as np

class ModelMACiotTPF(IModel):
    __modeltag = EModelTag.MAC
    __ownernode: INode
    __supportednodeclasses = ['IoTBasic']
    __dependencies = [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio']]
    
    @property
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the model class. For example, ModelPower 
            Note that the name should exactly match to your class name. 
        """
        return self.__class__.__name__
    
    @property
    def modelTag(self) -> EModelTag:
        """
        @type
            EModelTag
        @desc
            The model tag for the implemented model
        """
        return self.__modeltag

    @property
    def ownerNode(self):
        """
        @type
            INode
        @desc
            Instance of the owner node that incorporates this model instance.
            The subclass (implementing a model) should keep a private variable holding the owner node instance. 
            This method can return that variable.
        """
        return self.__ownernode
    
    @property
    def supportedNodeClasses(self) -> 'list[str]':
        '''
        @type
            List of string
        @desc
            A model may not support all the node implementation. 
            supportedNodeClasses gives the list of names of the node implementation classes that it supports.
            For example, if a model supports only the SatBasic and SatAdvanced, the list should be ['SatBasic', 'SatAdvanced']
            If the model supports all the node implementations, just keep the list EMPTY.
        '''
        return self.__supportednodeclasses
    
    @property
    def dependencyModelClasses(self) -> 'list[list[str]]':
        '''
        @type
            Nested list of string
        @desc
            dependencyModelClasses gives the nested list of name of the model implementations that this model has dependency on.
            For example, if a model has dependency on the ModelPower and ModelOrbitalBasic, the list should be [['ModelPower'], ['ModelOrbitalBasic']].
            Now, if the model can work with EITHER of the ModelOrbitalBasic OR ModelOrbitalAdvanced, the these two should come under one sublist looking like [['ModelPower'], ['ModelOrbitalBasic', 'ModelOrbitalAdvanced']]. 
            So each exclusively dependent model should be in a separate sublist and all the models that can work with either of the dependent models should be in the same sublist.
            If your model does not have any dependency, just keep the list EMPTY. 
        '''
        return self.__dependencies
    
    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName + ", " , "Model tag: " + self.__modeltag.__str__()])
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
    }
    
    def call_APIs(
            self, 
            _apiName: str, 
            **_kwargs):
        '''
        This method acts as an API interface of the model. 
        An API offered by the model can be invoked through this method.
        @param[in] _apiName
            Name of the API. Each model should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        _ret = None
        
        try:
            _ret = self.__apiHandlerDictionary[_apiName](self, _kwargs)
        except Exception as e:
            print(f"[ModelMACiotTPF]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
        
    def __get_ReceivedData(self):
        """
        @desc
            This method returns all the received data from the LoRa radio model. It will empty the received data buffer of the LoRa radio model.
        @return
            List of received data
        """
        _receivedData = [] 
        while (_data := self.__loraModel.call_APIs("get_ReceivedPacket")) is not None:
            _receivedData.append(_data)
        
        return _receivedData
    
    def __check_BeaconsReceived(self, _receivedData):
        """
        @desc
            This method returns if a beacon is received
        @param[in] _receivedData
            List of received data. This should be the output of __get_ReceivedData and should contain either acks or beacons
        @return
            A tuple of the following:
                1. True if a beacon is received, False otherwise
                2. The number of devices in the footprint if a beacon is received, -1 otherwise
        """
        for _data in _receivedData:
            if isinstance(_data, MACBeacon):
                #self.__logger.write_Log("Received beacon from: " + str(_data.sourceRadioID) + ". Current state:" + str(self.__currentState), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                return (True, _data.numDevicesInView)
        return (False, -1)
    
    def __check_AcksReceived(self, _desiredData, _receivedData):
        """
        @desc
            This method returns the received data
        @param[in] _desiredData
            The MACData unit that we are waiting for an ack
        @param[in] _receivedData
            List of received data. This should be the output of __get_ReceivedData and should contain either acks or beacons
        @return
            True if the ack is received, False otherwise
        """
        for _data in _receivedData:
            if isinstance(_data, MACAck) and _data.receivedMACDataID == _desiredData.id:
                return True
        return False
    
    def __send_Data(self):
        """
        @desc
            This method sends the data through the radio
        @return
            True if the data is sent, False otherwise
        """
        return self.__loraModel.call_APIs("send_Packet", _packet = self.__currentData)
    
    def Execute(self):
        """
        Main execution method for the MAC IoT TPF model.
        
        Implements a simplified CosMAC protocol with transmission probability function:
        1. Data generation and queuing
        2. Beacon reception and processing
        3. Probabilistic transmission scheduling
        4. Acknowledgment handling and retransmission
        
        Uses a fixed transmission probability based on slot count and device count
        without adaptive alpha tuning.
        """
        # Initialize LoRa model on first execution
        if self.__loraModel is None:
            self.__loraModel = self.__ownernode.has_ModelWithTag(EModelTag.BASICLORARADIO)
        
        _receivedData = self.__get_ReceivedData()
        _beaconsReceived, self.__numDevices = self.__check_BeaconsReceived(_receivedData)
        # Here are our states
        # 1: We have no data to send
        # 2: We have data to send and are waiting for a beacon
        # 3: We have received a beacon. Set a backoff period
        # 4: We are in the backoff period and waiting to send data
        # 5: We are past the backoff period and sending data. Don't wait for an ack - go back to state 2
            
        #State 1: We have no data to send
        if self.__currentState == 1:
            #let's see if we can get some
            if self.__dataGenerator is None:
                self.__dataGenerator = self.__ownernode.has_ModelWithTag(EModelTag.DATAGENERATOR)
            
            _data = self.__dataGenerator.call_APIs("get_Data")
            if _data is not None:
                #We need to add the MAC header to the data
                _time = self.__ownernode.timestamp.copy()
                _payload = pickle.dumps(_data)
                _size = self.__packetSize  # Data packet size in bytes
                _macData = MACData(creationTime=_time,
                                      sourceRadioID=self.__loraModel.radioID,
                                      size=_size,
                                      intendedRadioID=-1, 
                                      sequenceNumber=self.__sequenceNumber,
                                      dataPayloadString=_payload)
                
                #self.__logger.write_Log(f"Data to send: " + str(_macData.id), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__sequenceNumber += 1
                self.__currentData = _macData
                
                #we have data to send. Proceed to state 2
                self.__currentState = 2
            else:
                #we have no data to send. Let's continue waiting. State remains 1
                return 
        
        #State 2: We have data to send and are waiting for a beacon
        if self.__currentState == 2:
            self.__loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency)
            
            _beaconsReceived, self.__numDevices = self.__check_BeaconsReceived(_receivedData)
            if _beaconsReceived:
                #We have received a beacon. Let's go to state 3
                self.__currentState = 3
            else:
                #Let's continue waiting for a beacon. State remains 2
                return
        
        #State 3: We have received a beacon. Set a backoff period before sending data
        if self.__currentState == 3:           
            #We have n slots, each of which is m seconds long. 
            if self.__numDevices == 0:
                _prob = 1
            else:
                _prob = self.__nSlots/self.__numDevices
            
            #Generate n random numbers between 0 and 1. If any of them is less than _prob, then we will transmit in that slot
            #_randNums = [random.random() for _ in range(self.__nSlots)]
            # _transmitSlots = [_randNums[i] < _prob for i in range(self.__nSlots)]
            
            #if True not in _transmitSlots:
            if random.random() > _prob: 
                #we didn't get a slot. Let's try again later. Move to state 2 and wait for another beacon
                self.__currentState = 2
            else:
                self.__logger.write_Log(f"Probability of transmission: " + str(_prob), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                _slot = random.randint(0, self.__nSlots - 1)
                #we got a slot. Let's find the first one
                #_slot = _transmitSlots.index(True)
                self.__transmitTime = self.__ownernode.timestamp.copy().add_seconds(_slot * self.__slotLength)
                
                self.__currentState = 4
                     
        #State 4: We are in the backoff period and waiting to send data
        if self.__currentState == 4:
            self.__loraModel.call_APIs("set_Frequency", _frequency = self.__ulFrequency)
            #Let's check if the backoff period is over
            if self.__transmitTime <= self.__ownernode.timestamp:
                #we should send the data. Let's go to state 5
                self.__currentState = 5
            else:
                #we should not send the data. Let's try again later. State remains 4
                return
        
        #State 5: We are past the backoff period and sending data
        if self.__currentState == 5:
            #let's send the data
            _success = self.__send_Data()
            self.__currentState = 6
            self.__retransmitTime = self.__ownernode.timestamp.copy().add_seconds(self.__retransmitInterval)

        if self.__currentState == 6:
            #if we have received the desired ack, we can go back to state 1. 
            if self.__check_AcksReceived(self.__currentData, _receivedData):
                self.__logger.write_Log("Ack received", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__currentState = 1
                self.__currentData = None

                
            # if passed the timeout, we need to go back to state 2 and retransmit
            elif self.__retransmitTime <= self.__ownernode.timestamp:
                self.__logger.write_Log("Timeout on ack. Retransmitting", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__currentState = 2

            else:
                #we are still waiting for the ack. Let's continue waiting. State remains 6
                return

    
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _slotLength: int,
            _beaconInterval: int) -> None:
        '''
        Constructor for ModelMACiotTPF.
        
        Initializes the MAC IoT TPF model with fixed transmission parameters.
        This model provides a simplified version of CosMAC without adaptive tuning.
        
        @param[in]  _ownernodeins: INode
            Instance of the IoT device node that incorporates this model
        @param[in]  _loggerins: ILogger
            Logger instance for recording model events and debugging
        @param[in]  _slotLength: int
            Duration of each transmission slot in seconds
        @param[in]  _beaconInterval: int
            Expected interval between beacon transmissions in seconds
            
        @raises AssertionError: If _ownernodeins or _loggerins is None
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__lastBeacon = None #the frame of the last beacon
        
        self.__numDevices = -1 #the number of other iot devices in the footprint
        self.__loraModel = None #the lora model instance
        self.__dataGenerator = None #the data generator model instance
        
        self.__currentState = 1 #the current state of the model
        self.__currentData = None #the data that is currently being sent
        
        self.__slotLength = _slotLength #the length of each slot in seconds
        self.__beaconInterval = _beaconInterval 
        self.__nSlots = int(_beaconInterval/_slotLength) #the number of slots in a beacon interval
        self.__sequenceNumber = 0 #the sequence number of the data packet
        
        # Radio frequencies (configurable)
        self.__beaconFrequency = 0.4013e9  # 401.3 MHz - beacon frequency
        self.__ulFrequency = 0.4015e9      # 401.5 MHz - uplink frequency
        
        # Protocol parameters (configurable)
        self.__retransmitInterval = 30  # ACK timeout in seconds
        self.__packetSize = 100         # Data packet size in bytes

def init_ModelMACiotTPF(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    Factory function to initialize a ModelMACiotTPF instance.
    
    Creates a simplified CosMAC IoT device model with fixed transmission parameters.
    This variant uses transmission probability functions without adaptive tuning.
    
    @param[in]  _ownernodeins: INode
        Instance of the IoT device node
    @param[in]  _loggerins: ILogger
        Logger instance for recording model events
    @param[in]  _modelArgs: object
        Configuration object (currently unused - parameters are hardcoded)
        
    @return IModel
        Initialized instance of ModelMACiotTPF
        
    @raises AssertionError: If _ownernodeins or _loggerins is None
    
    @note
        slot_length is hardcoded to 2 seconds and beacon_interval to 120 seconds.
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None

    return ModelMACiotTPF( _ownernodeins, 
                                _loggerins,
                                2,
                                120)
    
    
    
    
                    

# #We handle the state 6 first because it deals with the previous timestamp (waiting for ack)
# if self.__currentState == 6:
#     #if we have received the desired ack, we can go back to state 1. 
#     if self.__check_AcksReceived(self.__currentData, _receivedData):
#         self.__logger.write_Log("Ack received", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
#         self.__currentState = 1
    
#     # if passed the timeout, we need to go back to state 2 and retransmit
#     elif self.__transmitTime.copy().add_seconds(self.__retransmitInterval) <= self.__ownernode.timestamp:
#         self.__logger.write_Log("Timeout on ack. Retransmitting", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
#         self.__currentState = 2
    
#     else:
#         #we are still waiting for the ack. Let's continue waiting. State remains 6
#         return
