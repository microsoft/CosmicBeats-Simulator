'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
@desc
    This model represents the MAC layer for IoT nodes and operates according to the following steps:

    1. The model checks the queue of the data generation model to see if there is any data to transmit.
    2. Upon encountering a beacon, the model verifies whether it is the most recent one and not an old beacon.
    3. If the beacon is the latest, the model attempts data transmission and waits for an acknowledgment (ACK). Both packet transmission and ACK reception occur through the modelradio.
    4. The model persists in retransmitting during subsequent beacon cycles until it successfully receives the ACK.
'''
import pickle
import random

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger

from src.models.network.macdata.macbeacon import MACBeacon
from src.models.network.macdata.macack import MACAck
from src.models.network.macdata.macdata import MACData

class ModelMACiot(IModel):
    __modeltag = EModelTag.MAC
    __ownernode: INode
    __supportednodeclasses = ['IoTBasic']
    __dependencies = [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio'], 
                      ['ModelDataGenerator']]
    
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
            print(f"[ModelMACiot]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
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
    
    def __check_BeaconsReceived(self, _receivedData):
        """
        @desc
            This method returns if a beacon is received
        @param[in] _receivedData
            List of received data. This should be the output of __get_ReceivedData and should contain either acks or beacons
        @return
            True if a beacon is received, False otherwise
        """
        for _data in _receivedData:
            if isinstance(_data, MACBeacon):
                self.__logger.write_Log(f"Beacons received: " + str(_receivedData), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
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
        #Let's get the radio model and store it so we don't have to get it every time
        if self.__loraModel is None:
            self.__loraModel = self.__ownernode.has_ModelWithTag(EModelTag.BASICLORARADIO)
            
        #We have a few possible states:
        # 1. We have no data to send
        # 2. We have data to send and are waiting for a beacon
        # 3. We have received a beacon. Set a backoff period before sending data
        # 4. We are in the backoff period and waiting to send data
        # 5. We are past the backoff period and are sending the data
        # 6. We have sent data and waiting for an ack        
        #Let's first get all the received data. This will be used in multiple states
        #We do it here because multiple states need it. This will empty the received data queue. 
        _receivedData = self.__get_ReceivedData() 
        
        #We handle the state 6 first because it deals with the previous timestamp (waiting for ack)
        if self.__currentState == 6:
            #if we have received the desired ack, we can go back to state 1. 
            if self.__check_AcksReceived(self.__currentData, _receivedData):
                self.__logger.write_Log("Ack received", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__currentState = 1
            
            # if passed the timeout, we need to go back to state 2 and retransmit
            elif self.__transmitTime.copy().add_seconds(self.__retransmitInterval) <= self.__ownernode.timestamp:
                self.__logger.write_Log("Timeout on ack. Retransmitting", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__currentState = 2
            
            else:
                #we are still waiting for the ack. Let's continue waiting. State remains 6
                return
            
        #State 1: We have no data to send
        if self.__currentState == 1:
            #let's see if we can get some
            _dataGenerator = self.__ownernode.has_ModelWithTag(EModelTag.DATAGENERATOR)
            if _dataGenerator is None:
                raise Exception("Data generator model is not found for owner node: " + str(self.__ownernode.nodeId))
            
            _data = _dataGenerator.call_APIs("get_Data")
            if _data is not None:
                #We need to add the MAC header to the data
                _time = self.__ownernode.timestamp.copy()
                _payload = pickle.dumps(_data)
                _size = _data.size + 4 #TODO: change this to the actual size of the payload
                _macData = MACData(creationTime=_time,
                                      sourceRadioID=self.__loraModel.radioID,
                                      size=_size,
                                      intendedRadioID=-1, 
                                      sequenceNumber=self.__sequenceNumber,
                                      dataPayloadString=_payload)
                
                self.__sequenceNumber += 1
                
                self.__currentData = _macData
                
                #we have data to send. Proceed to state 2
                self.__loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency)
                self.__currentState = 2
            else:
                #we have no data to send. Let's continue waiting. State remains 1
                return 
        
        #State 2: We have data to send and are waiting for a beacon
        if self.__currentState == 2:
            self.__loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency) #Should already be set, but just in case
            _beaconsReceived = self.__check_BeaconsReceived(_receivedData)
            if _beaconsReceived:
                #We have received a beacon. Let's go to state 3
                self.__currentState = 3
            else:
                #Let's continue waiting for a beacon. State remains 2
                return
        
        #State 3: We have received a beacon. Set a backoff period before sending data
        if self.__currentState == 3:
            _timeToBackoff = random.randint(0, self.__backoffInterval)
            self.__transmitTime = self.__ownernode.timestamp.copy().add_seconds(_timeToBackoff)
            self.__logger.write_Log(f"Backing off till: " + str(self.__transmitTime), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
            self.__currentState = 4
            
            #we will switch to the ack/send frequency:
            self.__loraModel.call_APIs("set_Frequency", _frequency = self.__uplinkFrequency)
         
        #State 4: We are in the backoff period and waiting to send data
        if self.__currentState == 4:
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
            if _success:
                #we have sent the data. Let's go to state 6            
                self.__currentState = 6
            else:
                #For some reason, we could not send the data. This is likely that the sat is now out of range. 
                #Go back to waiting for a beacon. State goes back to 2
                self.__currentState = 2

        #State 6 is handled at the beginning of the next timestep
        
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _backoff: int,
            _retransmit: int,
            _beaconFrequency: int,
            _uplinkFrequency: int) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _backoff
            Backoff time in seconds. Random backoff time will be chosen between 0 and _backoff
        @param[in]  _retransmit
            Retransmission time in seconds. After _retransmit seconds, the data will be retransmitted
        @param[in]  _beaconFrequency
            Frequency at which the beacons are sent
        @param[in]  _uplinkFrequency
            Frequency at which the data is sent
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__retransmitInterval = _retransmit
        self.__backoffInterval = _backoff
        self.__beaconFrequency = _beaconFrequency
        self.__uplinkFrequency = _uplinkFrequency
        
        self.__transmitTime: 'Time' = None #The time at which we will send the next data
        self.__currentData = None #The data that we are sending/waiting to send/waiting for ack
        self.__sequenceNumber = 0 #The sequence number of the data that we are sending/waiting to send/waiting for ack
        
        self.__currentState = 1 #See execute() for the meaning of each state
        self.__loraModel = None #The model of the LoRa radio that we are using
                
def init_ModelMACiot(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelMACiot class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key num_packets
            The number of packets to ask the satellite to send
        @key timeout
            How long to wait to not receive any packets from the satellite before moving on.
        @key beacon_frequency
            What frequency to listen for beacons from the satellite
        @key uplink_frequency
            What frequency to send data packets to the satellite
    @return
        Instance of the model class
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    if "backoff_time" not in _modelArgs or "retransmit_time" not in _modelArgs or "beacon_frequency" not in "uplink_frequency" not in _modelArgs: 
        raise Exception("backoff_time, retransmit_time, beacon_frequency, timeout or is not provided for ModelMACiot for node " + _ownernodeins.nodeID)

    return ModelMACiot(_ownernodeins, 
                          _loggerins,
                          _modelArgs.backoff_time,
                          _modelArgs.retransmit_time,
                          _modelArgs.beacon_frequency,
                          _modelArgs.uplink_frequency)