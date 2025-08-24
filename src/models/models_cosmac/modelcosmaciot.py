'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
Updated: 2024

@desc
    This model implements the CosMAC (Constellation-Aware Medium Access and Scheduling for IoT Satellites) IoT device protocol.
    Based on the paper: https://deepakv.web.illinois.edu/assets/papers/CosMAC_MobiCom_2024.pdf
    
    This model controls IoT device behavior in satellite constellation communication, implementing:
    1. Beacon-based transmission scheduling with adaptive alpha parameters
    2. Multi-satellite beacon tracking and coordination
    3. Collision-aware transmission probability adjustment
    4. Acknowledgment-based reliable data transmission
    5. State machine for efficient packet transmission workflow
    
    The model operates through a 6-state machine:
    - State 1: No data to send (idle)
    - State 2: Data available, waiting for beacon
    - State 3: Beacon received, calculating transmission probability
    - State 4: Backoff period, waiting for transmission slot
    - State 5: Transmitting data packet
    - State 6: Waiting for acknowledgment
'''
from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.network.macdata.macbeacon import MACBeacon
from src.models.network.macdata.macdata import MACData
from src.models.network.macdata.macack import MACAck
from src.utils import Time
import numpy as np

import random
import pickle

class ModelCosmacIoT(IModel):
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
            print(f"[ModelCosmacIoT]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
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
            Nothing. Update the beacons dictionary
        """
        for _data in _receivedData:
            if isinstance(_data, MACBeacon):
                self.__beacons[_data.sourceRadioID] = (self.__ownernode.timestamp.copy().add_seconds(self.__beaconInterval), _data.numDevicesInView)
                self.__mostRecentBeaconTime = _data.creationTime.copy()
                self.__waitingForNewBeacon = False #we have received a beacon. We are not waiting for a new one
                
                if _data.alphaIncrease == True:
                    self.__alpha += self.__alphaIncrease
                    #self.__logger.write_Log(f"Alpha: {self.__alpha}", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                elif _data.alphaIncrease == False:
                    self.__alpha *= self.__alphaDecrease
                    #self.__logger.write_Log(f"Alpha: {self.__alpha}", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                    
                self.__nextBeaconTime = min([i[0] for i in self.__beacons.values()])
                
        if self.__nextBeaconTime is not None and self.__nextBeaconTime <= self.__ownernode.timestamp:
            _toRemove = []
            for _radioID, _beacon in self.__beacons.items():
                if _beacon[0] <= self.__ownernode.timestamp:
                    _toRemove.append(_radioID)
            for _radioID in _toRemove:
                self.__beacons.pop(_radioID)

    def __send_Data(self):
        """
        @desc
            This method sends the data through the radio
        @return
            True if the data is sent, False otherwise
        """
        return self.__loraModel.call_APIs("send_Packet", _packet = self.__currentData)
    
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
    
    def Execute(self):
        """
        Main execution method for the CosMAC IoT device model.
        
        Implements the CosMAC protocol state machine for IoT devices:
        1. Manages data generation and queuing
        2. Tracks beacons from multiple satellites
        3. Calculates transmission probabilities based on constellation state
        4. Handles backoff and transmission timing
        5. Manages acknowledgment reception and retransmission
        
        The method maintains state across calls and adapts behavior based on
        received beacons and collision feedback from satellites.
        """
        # Initialize required models on first execution
        if self.__loraModel is None:
            self.__loraModel = self.__ownernode.has_ModelWithTag(EModelTag.BASICLORARADIO)
            self.__dataGenerator = self.__ownernode.has_ModelWithTag(EModelTag.DATAGENERATOR)
        
        _receivedData = self.__get_ReceivedData()
        # Okay, here we need to always check if we have received a beacon
        # State 1: We have no data to send
        # State 2: We have data to send and are waiting for a beacon
        # State 3: We have received a beacon. Set a backoff period before sending data
        # State 4: We are in the backoff period and waiting to send data
        # State 5: We are past the backoff period and sending data
        # State 6: We have sent the data and are waiting for an ACK
 
        #We always check if we have received a beacon
        self.__check_BeaconsReceived(_receivedData)

        # #State 1: We have no data to send
        if self.__currentState == 1:
            self.__loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency)
            
            #let's see if we can get some
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
                
                #self.__logger.write_Log(f"Data to send: " + str(_macData), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__sequenceNumber += 1
                self.__currentData = _macData
                
                #we have data to send. Proceed to state 2
                self.__currentState = 2

        #State 2: We have data to send and are waiting for a beacon
        if self.__currentState == 2:
            self.__loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency)
            
            _beaconsReceived = len(self.__beacons) > 0 and not self.__waitingForNewBeacon
            if _beaconsReceived:
               #We have received a beacon. Let's go to state 3
               self.__currentState = 3

        #State 3: We have received a beacon. Set a backoff period before sending data
        if self.__currentState == 3:
            #If we're here, we always need to wait for a new beacon
            self.__waitingForNewBeacon = True
            
            _totalDevices = sum([vals[1] for satID, vals in self.__beacons.items()])
            if _totalDevices == 0:
                _prob = 1
            else:
                _prob = self.__alpha / _totalDevices * self.__nSlots
            #Generate n random numbers between 0 and 1. If any of them is less than _prob, then we will transmit in that slot
            #_randNums = np.random.rand(self.__nSlots - 1) #Ignore the first slot. 
            _random = random.random()
            
            #_transmitSlots = np.argwhere(_randNums < _prob).flatten()
            #_transmitSlots += 1 #Add 1 to account for the first slot that we ignored
            
            #if len(_transmitSlots) == 0:
            if _random > _prob:
                #we didn't get a slot. Let's try again later. Move to state 2 and wait for another beacon
                self.__currentState = 2
            else:
                _slot = random.randint(1, self.__nSlots - 1)
                self.__logger.write_Log(f"Probability of transmission: " + str(_prob*1/self.__nSlots) + ". Number of devices: "+ str(_totalDevices) + ". Number of beacons" + str(len(self.__beacons)), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                #we got a slot. Let's find the first one
                self.__transmitTime = self.__mostRecentBeaconTime.copy().add_seconds(int(_slot) * self.__slotLength)
                            
                #self.__logger.write_Log(f"Backing off till: " + str(self.__transmitTime), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__currentState = 4
                     
        #State 4: We are in the backoff period and waiting to send data
        if self.__currentState == 4:
            self.__loraModel.call_APIs("set_Frequency", _frequency = self.__ulFrequency)
            
            #Let's check if the backoff period is over
            if self.__transmitTime <= self.__ownernode.timestamp:
                #we should send the data. Let's go to state 5
                self.__currentState = 5
        
        #State 5: We are past the backoff period and sending data
        if self.__currentState == 5:
            #let's send the data
            _success = self.__send_Data()
            self.__retransmitTime = self.__ownernode.timestamp.copy().add_seconds(self.__retransmitInterval)
            #we have sent the data. Let's go to state 6            
            #self.__currentState = 1
            #self.__currentData = None
            self.__currentState = 6
            
        #State 6: listen for acks
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
            _beaconInterval: int,
            _alpha: float,
            _alphaDecrease: float,
            _alphaIncrease: float) -> None:
        '''
        Constructor for ModelCosmacIoT.
        
        Initializes the CosMAC IoT device model with transmission parameters
        and adaptive alpha tuning capabilities.
        
        @param[in]  _ownernodeins: INode
            Instance of the IoT device node that incorporates this model
        @param[in]  _loggerins: ILogger
            Logger instance for recording model events and debugging
        @param[in]  _slotLength: int
            Duration of each transmission slot in seconds
        @param[in]  _beaconInterval: int
            Expected interval between beacon transmissions in seconds
        @param[in]  _alpha: float
            Base alpha parameter for transmission probability calculation
        @param[in]  _alphaDecrease: float
            Multiplicative factor for decreasing alpha (collision avoidance)
        @param[in]  _alphaIncrease: float
            Additive factor for increasing alpha (improved channel utilization)
            
        @raises AssertionError: If _ownernodeins or _loggerins is None
        
        @note
            Alpha parameters are currently hardcoded in the constructor and
            override the provided values. This should be addressed in future versions.
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__loraModel = None #the lora model instance
        
        self.__currentState = 1 #the current state of the model
        self.__currentData = None #the data that is currently being sent
        
        self.__slotLength = _slotLength #the length of each slot in seconds
        self.__beaconInterval = _beaconInterval 
        
        self.__nSlots = int(_beaconInterval/_slotLength) #the number of slots in a beacon interval
        self.__sequenceNumber = 0 #the sequence number of the data packet
        
        # Alpha parameters for transmission probability (use provided values)
        self.__alpha = _alpha                    # Base alpha value for TPF model
        self.__alphaIncrease = _alphaIncrease   # Additive increase factor
        self.__alphaDecrease = _alphaDecrease   # Multiplicative decrease factor
        
        self.__beacons = {} #Dict of satID -> (timestamp, numDevices)
        self.__waitingForNewBeacon = True #Flag to indicate if we are waiting for a new beacon
        self.__nextBeaconTime = None #the time of the next beacon
        self.__mostRecentBeaconTime = None #the time of the most recent beacon
        
        # Radio frequencies (configurable)
        self.__beaconFrequency = 0.4013e9  # 401.3 MHz - beacon frequency
        self.__ulFrequency = 0.4015e9      # 401.5 MHz - uplink frequency
        
        # Protocol parameters (configurable)
        self.__retransmitInterval = 30  # ACK timeout in seconds
        self.__packetSize = 100         # Data packet size in bytes
        
def init_ModelCosmacIoT(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    Factory function to initialize a ModelCosmacIoT instance.
    
    Creates and configures a CosMAC IoT device model with the provided parameters.
    This function serves as the standard initialization interface for the simulator.
    
    @param[in]  _ownernodeins: INode
        Instance of the IoT device node
    @param[in]  _loggerins: ILogger
        Logger instance for recording model events
    @param[in]  _modelArgs: object
        Configuration object containing model-specific parameters
        Required attributes:
        - alpha (float): Base alpha parameter for transmission probability
        - alpha_decrease (float): Multiplicative factor for alpha reduction
        - alpha_increase (float): Additive factor for alpha increase
        
    @return IModel
        Initialized instance of ModelCosmacIoT
        
    @raises AssertionError: If _ownernodeins or _loggerins is None
    @raises AttributeError: If required attributes are missing from _modelArgs
    
    @note
        slot_length is hardcoded to 2 seconds and beacon_interval to 120 seconds
        as per CosMAC protocol specifications.
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None

    return ModelCosmacIoT( _ownernodeins, 
                                _loggerins,
                                2,
                                120,
                                _modelArgs.alpha,
                                _modelArgs.alpha_decrease,
                                _modelArgs.alpha_increase)
    
    
    
    
                    

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
