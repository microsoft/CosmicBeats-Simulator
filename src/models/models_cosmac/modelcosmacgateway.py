'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
@desc
    This model implements the CosMAC (Constellation-Aware Medium Access and Scheduling for IoT Satellites) gateway protocol.
    Based on the paper: https://deepakv.web.illinois.edu/assets/papers/CosMAC_MobiCom_2024.pdf
    
    This MAC Layer model is designed for satellite gateway functionality in IoT satellite constellations.
    It manages uplink communication from IoT devices and implements adaptive collision control through:
    
    1. Beacon transmission with adaptive alpha tuning based on collision feedback
    2. Uplink packet reception and ACK transmission
    3. Collision detection and adaptive scheduling parameter adjustment
    4. Data storage coordination for received IoT packets
    
    The model operates through the following steps:
        1. Examines the RX queue of the ModelAggregatorRadio (uplink) for received packets
        2. Transmits acknowledgments (ACK) back to devices using the uplink radio
        3. Stores received packets in the satellite's local storage
        4. Sends periodic beacons with collision control information
        5. Adapts transmission parameters based on collision statistics
'''

import pickle
import numpy as np
import random

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.network.macdata.macbeacon import MACBeacon
from src.models.network.macdata.macack import MACAck

from src.utils import Time

class ModelCosmacGateway(IModel):
    __modeltag = EModelTag.MAC
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = [['ModelAggregatorRadio'],
                       ['ModelDataStore']]
    
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
            print(f"[ModelCosmacGateway]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
            
    def __get_ReceivedData(self):
        """
        @desc
            This method returns the received data
        @return
            List of received data
        """
        if self.__uplinkModel is None:
            self.__uplinkModel = self.__ownernode.has_ModelWithName("ModelAggregatorRadio")

        #the received data is a list of the received data
        _receivedData = [] 
        while (_data := self.__uplinkModel.call_APIs("get_ReceivedPacket")) is not None:
            _receivedData.append(_data)
        
        return _receivedData
        
    def Execute(self):
        """
        Main execution method for the CosMAC gateway model.
        
        This method implements the core CosMAC gateway functionality:
        1. Receives and processes uplink packets from IoT devices
        2. Sends acknowledgments for received packets
        3. Tracks collision statistics for adaptive parameter tuning
        4. Transmits periodic beacons with updated scheduling parameters
        5. Adjusts alpha parameters based on collision feedback
        
        The method operates on a per-timestep basis and maintains state across calls.
        """
        # Receive all available data packets
        _receivedDatas = self.__get_ReceivedData()
        if len(_receivedDatas) > 1:
            # Fine granularity assumption: only one packet per timestep expected
            raise Exception("More than one data received. This is not expected. Make the granularity finer.")
                
        #If we have received a data, let's store it
        if len(_receivedDatas) == 1:
            _receivedData = _receivedDatas[0]
                                
            _currentTime = self.__ownernode.timestamp.copy()
            _size = self.__ackSize  # ACK packet size in bytes
            _ack = MACAck(creationTime=_currentTime,
                        sourceRadioID=self.__uplinkModel.radioID,
                        size=_size,
                        intendedRadioID=_receivedData.sourceRadioID,
                        sequenceNumber=_receivedData.sequenceNumber + 1,
                        receivedMACDataID=_receivedData.id)
            
            #print(f"Sending ACK with ID {_ack.id}", _ack)
            self.__uplinkModel.call_APIs("send_Packet", _packet = _ack, _timeOffset = random.uniform(0, self.__maxAckDelay))

            
            _dataModel = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE)
            if _dataModel is None:
                raise Exception("Data storage is not found for owner node: " + str(self.__ownernode.nodeId))
            _dataModel.call_APIs("add_Data", _data = pickle.loads(_receivedData.dataPayloadString))
        
        #If we're alpha tuning, we need to keep track of the collisions. 
        if True:
            _collisionHappened = self.__uplinkModel.call_APIs("collision_Happened")
            if _collisionHappened:
                #we have a collision, let's store it
                self.__collisionHistory.append((self.__ownernode.timestamp.copy().add_seconds(-1))) #The collision technically happened one second ago
                #self.__logger.write_Log("Collision happened", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                
        #Now, let's do the alpha tuning logic at the start of every 60 seconds. Don't do this until after the first beacon is sent
        if True and self.__nextMinuteTime <= self.__ownernode.timestamp and self.__beaconSequenceNumber > 0:
            #self.__logger.write_Log("Collision buffer: " + str(self.__collisionHistory), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
            #We need to go through and group the collisions by the slot
            
            _startSlot = self.__nextMinuteTime.copy().add_seconds(-60) #Start of each slot. 
            _endOfSlot = _startSlot.copy().add_seconds(self.__slotLength) #End of each slot
            _nSlotsWithCollisions = 0  #Number of slots with collisions
            while _endOfSlot <= self.__nextMinuteTime:
                _nCollisions = 0
                for _time in self.__collisionHistory:
                    if _startSlot <= _time and _time < _endOfSlot:
                        _nCollisions += 1
                if _nCollisions > 0:
                    _nSlotsWithCollisions += 1
                    
                _startSlot.add_seconds(self.__slotLength) #move to the next slot
                _endOfSlot.add_seconds(self.__slotLength) #move to the next slot

            #To get a percentage, we need to find the number of slots with collisions and divide by the total number of slots
            
            #Let's count the number of slots with collisions in the last 60 seconds
            _nSlots = 60 / self.__slotLength - 1 #We don't count the first slot since it's not a full slot as the beacon is still being sent
            _collisionPercentage = _nSlotsWithCollisions / _nSlots 
            
            self.__logger.write_Log("Collision percentage: " + str(_collisionPercentage), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                       
            #add the percentage to the history. If more than _windowInterval, remove the first one - we only want to keep the last _windowInterval
            if len(self.__collisionPercentageHistory) >= self.__windowInterval:
                self.__collisionPercentageHistory.pop(0) #The first one is the oldest one, so remove it
            self.__collisionPercentageHistory.append(_collisionPercentage) #add the new one
            
            self.__collisionHistory = []

            self.__nextMinuteTime = self.__getNextMinuteTime()
            
        #Now, when we are ready to send the beacon, see if we need to change the alpha
        if self.__nextBeaconTime <= self.__ownernode.timestamp:
            _increaseAlpha = None
            
            if self.__fovModel is None:
                self.__fovModel = self.__ownernode.has_ModelWithTag(EModelTag.VIEWOFNODE)
                
            _nIot = len(self.__fovModel.call_APIs("get_View", _targetNodeTypes = [ENodeType.IOTDEVICE], _isDownView=True))
            self.__logger.write_Log(f"Number of IoT devices in view: {_nIot}, alpha tuning: {self.__alphaTuning}, window interval: {self.__windowInterval}", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
            #If we have a collision percentage history, we can do the alpha tuning
            if self.__alphaTuning and len(self.__collisionPercentageHistory) >= self.__windowInterval and _nIot > 0:
                self.__logger.write_Log(f"Collision percentage history: {self.__collisionPercentageHistory}", ELogType.LOGDEBUG, self.__ownernode.timestamp, self.iName)
                #Let's first fit a linear model to the collision percentage history
                
                #We want to make a line where the most recent minute's collision percentage is at the y-intercept and the previous minutes and -1, -2, -3, etc. are the x values
                _xVals = np.array(range(-len(self.__collisionPercentageHistory) + 1, 1))
                _yVals = np.array(self.__collisionPercentageHistory)
                
                #Let's fit a line to the data
                _slope, _intercept = np.polyfit(_xVals, _yVals, 1)
                
                #Let's find what the ideal collision percentage is
                
                #P(N >= 2) = 1 - P(N = 0) - P(N = 1)
                #pIdealInOne = 1/n
                #P(N = 0) = (1 - p)^n = (1 - 1/n)^n 
                #P(N = 1) = n * p * (1 - p)^(n-1) = n * 1/n * (1 - 1/n)^(n-1) = (1 - 1/n)^(n-1)
                #P(N >= 2)= 1 - [(1-1/n)^(n-1) + (1-1/n)^n]
                _pECIdeal = 1 - ((1 - 1/_nIot)**(_nIot - 1) + (1 - 1/_nIot)**_nIot)
                
                _pECupper = _pECIdeal * 2
                _pEClower = _pECIdeal * 0.5
                
                #If the slope is non-negative, and the intercept is greater than our threshold, we decrease alpha            
                if (_slope >= 0 and _intercept >= _pECupper) or _intercept >= 2 * _pECIdeal:
                    _increaseAlpha = False
                #If the slope is non-positive, and the intercept is less than our threshold, we increase alpha
                elif (_intercept <= _pEClower):
                    _increaseAlpha = True
                    
                self.__logger.write_Log(f"Decided to increase alpha: {_increaseAlpha}. Slope: {_slope}, Intercept: {_intercept}, pEC: {_pECIdeal}, pECupper: {_pECupper}, pEClower: {_pEClower}, history {self.__collisionPercentageHistory} ",
                                        ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                                
                if _increaseAlpha is not None:
                    self.__collisionPercentageHistory = []

                self.__nextMinuteTime = self.__getNextMinuteTime()
                
            _beacon = MACBeacon(creationTime=self.__ownernode.timestamp.copy(),
                                sourceRadioID=self.__ownernode.nodeID,
                                size = self.__beaconSize,
                                intendedRadioID=-1,
                                sequenceNumber=self.__beaconSequenceNumber,
                                numDevicesInView=_nIot,
                                alphaIncrease=_increaseAlpha)
            self.__beaconSequenceNumber += 1
            
            if self.__beaconSequenceNumber == 1:
                self.__nextMinuteTime = self.__getNextMinuteTime()
            
            self.__uplinkModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency)
            self.__uplinkModel.call_APIs("send_Packet", _packet = _beacon)
            self.__uplinkModel.call_APIs("set_Frequency", _frequency = self.__ulFrequency)
            
            self.__nextBeaconTime = self.__getNextBeaconTime()
            self.__logger.write_Log("Next beacon time {}".format(self.__nextBeaconTime), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
            
        
    beaconCount = 0
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _beaconInterval: int,
            _beaconBackoff: int,
            _alphaTuning: bool,
            _windowInterval: int,
            _slotLength: int) -> None:
        '''
        Constructor for ModelCosmacGateway.
        
        Initializes the CosMAC gateway model with parameters for beacon transmission,
        collision detection, and adaptive alpha tuning.
        
        @param[in]  _ownernodeins: INode
            Instance of the owner node (satellite) that incorporates this model
        @param[in]  _loggerins: ILogger
            Logger instance for recording model events and debugging
        @param[in]  _beaconInterval: int
            Interval between beacon transmissions in seconds
        @param[in]  _beaconBackoff: int
            Backoff time for beacon transmissions in seconds (currently unused)
        @param[in]  _alphaTuning: bool
            Enable adaptive alpha tuning based on collision feedback
        @param[in]  _windowInterval: int
            Time window for collision statistics collection (in minutes)
        @param[in]  _slotLength: int
            Duration of each transmission slot in seconds
            
        @raises AssertionError: If _ownernodeins or _loggerins is None
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        #For beacons:
        self.__beaconInterval = _beaconInterval #seconds
        self.__beaconBackoff = _beaconBackoff #seconds
        self.__getNextBeaconTime = lambda: self.__ownernode.timestamp.copy().add_seconds(self.__beaconInterval)
        self.__beaconSequenceNumber = 0

        self.__nextBeaconTime = self.__ownernode.timestamp.copy().add_seconds(ModelCosmacGateway.beaconCount)
        ModelCosmacGateway.beaconCount += 1
                
        #For alpha tuning:
        self.__alphaTuning = _alphaTuning
        self.__windowInterval = _windowInterval #minutes
        self.__slotLength = _slotLength

        self.__getNextMinuteTime = lambda: self.__ownernode.timestamp.copy().add_seconds(60)
        
        self.__nextMinuteTime = self.__getNextMinuteTime()
        
        self.__collisionHistory = [] # This is a list of timestamps when collisions happened
        self.__collisionPercentageHistory = [] # This is a list of percentage of slots with collisions in one minute windows

        self.__uplinkModel = None
        self.__fovModel = None
        
        # Radio frequencies (configurable)
        self.__beaconFrequency = 0.4013e9  # 401.3 MHz - beacon frequency
        self.__ulFrequency = 0.4015e9      # 401.5 MHz - uplink frequency
        
        # Packet sizes (configurable)
        self.__ackSize = 4        # ACK packet size in bytes
        self.__beaconSize = 4     # Beacon packet size in bytes
        self.__maxAckDelay = 1.5  # Maximum random delay for ACK transmission

        
def init_ModelCosmacGateway(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    Factory function to initialize a ModelCosmacGateway instance.
    
    Creates and configures a CosMAC gateway model instance with the provided parameters.
    This function serves as the standard initialization interface for the simulator.
    
    @param[in]  _ownernodeins: INode
        Instance of the owner satellite node
    @param[in]  _loggerins: ILogger
        Logger instance for recording model events
    @param[in]  _modelArgs: object
        Configuration object containing model-specific parameters
        Required attributes:
        - beacon_backoff (int): Backoff time for beacon transmissions
        - alpha_tuning (bool): Enable adaptive alpha tuning
        - window_interval (int): Collision statistics window in minutes
        
    @return IModel
        Initialized instance of ModelCosmacGateway
        
    @raises AssertionError: If _ownernodeins or _loggerins is None
    @raises AttributeError: If required attributes are missing from _modelArgs
    
    @note
        beacon_interval is hardcoded to 120 seconds and slot_length to 2 seconds
        as per CosMAC protocol specifications.
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    return ModelCosmacGateway(_ownernodeins, 
                          _loggerins,
                            120,
                            _modelArgs.beacon_backoff,
                            _modelArgs.alpha_tuning,
                            _modelArgs.window_interval,
                            2)


# self.__logger.write_Log(f"Received MACData with ID {_receivedData.id}", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)        
# #Let's create the acks
# _currentTime = self.__ownernode.timestamp.copy()
# _size = 4 #(I'm assuming that the data size is 4 bytes)
# _ack = MACAck(creationTime=_currentTime,
#               sourceRadioID=_uplinkModel.radioID,
#               size=_size,
#               intendedRadioID=_receivedData.sourceRadioID,
#               sequenceNumber=_receivedData.sequenceNumber + 1,
#               receivedMACDataID=_receivedData.id)

# #Let's send the ack.
# _success = self.__send_Ack(_ack)
# if not _success:
#     #The ack could not be sent. This is likely because either we don't have enough power or now the iot device is out of range
#     #Let's log this but keep going. We can't do anything about it
#     self.__logger.write_Log(f"Could not send ack for MACData with ID {_receivedData.id}", ELogType.LOGWARN, self.__ownernode.timestamp, self.iName)
    
