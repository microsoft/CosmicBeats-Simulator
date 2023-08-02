'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
@desc
    This model represents the MAC layer specifically designed for the satellite network, known as the TTnC model. It operates based on the following steps:

    1. The model checks the RX queue of the ModelDownlinkRadio for a control packet sent from the Ground Station (GS).
    2. Upon receiving the control packet, the model checks the requested number of packets, denoted as 'X,' and searches its local storage to obtain the necessary data.
    3. The model sends up to "X" packets to the Ground Station using the ModelDownlinkRadio. It does not discard the sent packets until receiving a bulk ACK (Acknowledgment) that contains the sent packets. The sent packets are held in this model.
    4. The model then waits for the ACK by monitoring the RX queue of the downlink radiomodel.
    5. Once an ACK is received, the model examines the packet IDs and discards the received packets accordingly. Any packets that were not acknowledged will be resent when the next control packet is received.
'''

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ELogType, ILogger
import random
from src.models.network.macdata.macbeacon import MACBeacon
from src.models.network.macdata.maccontrol import MACControl
from src.models.network.macdata.macdata import MACData
from src.models.network.macdata.macbulkack import MACBulkAck
import pickle

class ModelMACTTnC(IModel):

    __modeltag = EModelTag.MAC
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio'],
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
            print(f"[ModelMACTTnC]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
            
    def __get_ReceivedData(self, _loraModel):
        """
        @desc
            This method returns all the received data from the LoRa radio model. It will empty the received data buffer of the LoRa radio model.
        @param[in]
            _loraModel: LoRa radio model to get the received data from
        @return
            List of received data
        """
        _receivedData = [] 
        while (_data := _loraModel.call_APIs("get_ReceivedPacket")) is not None:
            _receivedData.append(_data)
        
        return _receivedData
    
    def __send_Beacon(self, _loraModel):
        """
        @desc
            This method creates a beacon and sends it on the beacon frequency. It also sets the next beacon time.
        @param[in]
            _loraModel: LoRa radio model to send the beacon from
        """
        #We send a beacon on the beacon frequency 
        _loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency)
        
        _time = self.__ownernode.timestamp.copy()
        _size = 8 #TODO: change this to the actual size of the payload
        _beacon = MACBeacon(creationTime=_time,
                            sourceRadioID=_loraModel.radioID,
                            size=_size,
                            intendedRadioID=-1,
                            sequenceNumber=0,
                            numDevicesInView=0)
        
        _loraModel.call_APIs("send_Packet", _packet = _beacon)
        self.__nextBeaconTime = self.__ownernode.timestamp.copy().add_seconds(self.__beaconInterval + random.randint(0, self.__beaconBackoff))
        
        #We listen for controls/acks and send data on the downlink frequency
        _loraModel.call_APIs("set_Frequency", _frequency = self.__downlinkFrequency)
        
    def Execute(self):      
        #The satellite can be in one of the following states:
        #1. We are waiting to send a beacon
        #2. We have sent a beacon. Let's wait for a control packet or ack from the ground station. If we don't receive anything after a timeout, let's resend the beacon
        #3. We have received a control packet. Let's send the requested data
        #4. We have sent the requested data. Let's send a control packet to the ground station to let it know that we have sent the data
        
        _downlinkModel = self.__ownernode.has_ModelWithName("ModelDownlinkRadio")
        if _downlinkModel is None:
            raise Exception("Downlink radio model is not found for owner node: " + str(self.__ownernode.nodeID))
        
        #let's get all of the data from the radio model
        _receivedData = self.__get_ReceivedData(_downlinkModel)
        
        #State 1: We are waiting to send a beacon
        if self.__currentState == 1:
            if self.__ownernode.timestamp >= self.__nextBeaconTime:
                self.__logger.write_Log("Sending beacon", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                #Let's send a beacon
                self.__send_Beacon(_downlinkModel)
                self.__currentState = 2
        
        #State 2: We have sent a beacon. Let's wait for a control packet or ack from the ground station. If we don't receive anything after a timeout, let's resend the beacon
        elif self.__currentState == 2:
            #Let's check if we have received a control packet, ack, or timeout
            
            _controlPackets = [x for x in _receivedData if isinstance(x, MACControl) and x.intendedRadioID == _downlinkModel.radioID]
            _acks = [x for x in _receivedData if isinstance(x, MACBulkAck) and x.intendedRadioID == _downlinkModel.radioID]
            
            if len(_controlPackets) > 0:
                #In the off chance that we receive multiple control packets, we first check if any of them are from the current ground station. 
                #If not, we pick the one with the highest amount of data requested
                _controlPacket = max(_controlPackets, key = lambda x: x.numPacketsToSend)
                    
                self.__gsRadioID = _controlPacket.sourceRadioID 
                self.__logger.write_Log("Received control packet from radio " + str(self.__gsRadioID), ELogType.LOGINFO, \
                    self.__ownernode.timestamp, self.iName)
                
                #Now, any data that is left in __sentData is the data that we need to send. Move it back to __dataToSend
                #We will send the 0th element of __dataToSend first, which will become the 0th element of __sentData
                self.__dataToSend = self.__sentData.copy()
                self.__sentData.clear()
                
                #Now, let's see if the control packet has requested more data than currently available. Get the data from the data store
                _numWantedPackets = _controlPacket.numPacketsToSend
                _dataStore = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE)
                while len(self.__dataToSend) < _numWantedPackets:
                    #Let's get the data object from the data store
                    _data = _dataStore.call_APIs("get_Data")
                    if _data is None:
                        break
                    
                    #We need to convert it to a MACData object
                    _time = self.__ownernode.timestamp.copy()
                    _size = _data.size + 4 #TODO: change this to the actual size
                    _payload = pickle.dumps(_data)
                    _data = MACData(creationTime=_time,
                                    sourceRadioID=_downlinkModel.radioID,
                                    size=_size,
                                    intendedRadioID=self.__gsRadioID,
                                    sequenceNumber=self.__currentSequenceNumber,
                                    dataPayloadString=_payload)
                    self.__currentSequenceNumber += 1
                    
                    self.__dataToSend.append(_data)
                
                #Now, let's send the requested data
                self.__currentState = 3

            #We get an ack if the ground station has received our data
            elif len(_acks) > 0:
                #We have received a bulk ack. We might receive multiple acks if there are multiple ground stations in range
                #Let's remove all the acked data
                for _bulkAck in _acks:
                    self.__logger.write_Log("Received ack " + str(_bulkAck), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                    _ind = 0
                    while _ind < len(self.__sentData):
                        if self.__sentData[_ind].id in _bulkAck.receivedMACDataIDs:
                            self.__logger.write_Log("Received ack for mac unit " + str(self.__sentData[_ind].id), \
                                ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                            self.__sentData.pop(_ind)
                            _ind -= 1
                        _ind += 1
                        
                    #Let's just wait for when we need to send the next beacon
                    self.__currentState = 1 
            
            #We get a timeout if we have not received a control packet or ack in a while. 
            elif self.__ownernode.timestamp >= self.__nextBeaconTime:
                self.__logger.write_Log("Timed out waiting for feedback. Resending beacon", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                #We have not received a control packet or ack in a while. Let's resend the beacon        
                self.__currentState = 1
            
        #State 3: After receiving a control packet, we send the requested data
        if self.__currentState == 3:
            #If we have data to send, send it
            if len(self.__dataToSend) > 0:
                #The radio model might be busy, so send the data if you can
                _actuallySent = _downlinkModel.call_APIs("send_Packet", _packet = self.__dataToSend[0])
                if _actuallySent:
                    self.__logger.write_Log("Sent MACData " + str(self.__dataToSend[0].id) + " to radio " + str(self.__gsRadioID), \
                        ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                    self.__sentData.append(self.__dataToSend[0])
                    self.__dataToSend.pop(0)
            else:
                #We have sent all of the data we can. Let's send a control packet to the ground station to confirm that we have sent all of the data
                self.__logger.write_Log("Sending Control. Sent " + str(len(self.__sentData)) + " packets to radio " + str(self.__gsRadioID), \
                    ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                
                _time = self.__ownernode.timestamp.copy()
                
                _control = MACControl(creationTime=_time,
                                        sourceRadioID=_downlinkModel.radioID,
                                        size=8, #TODO: change this to the actual size
                                        intendedRadioID=self.__gsRadioID,
                                        sequenceNumber=self.__currentSequenceNumber,
                                        numPacketsToSend=len(self.__sentData))
                
                _sucessful = _downlinkModel.call_APIs("send_Packet", _packet = _control)
                
                #If the radio is not busy, we should be able to send the control packet
                #let's go back to state 2 to listen for the ground station's response
                if _sucessful:
                    self.__currentState = 2
                    
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _beaconInterval: int,
            _beaconBackoff: int,
            _beaconFrequency: int,
            _downlinkFrequency: int) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _beaconInterval
            How often to send a beacon
        @param[in]  _beaconBackoff
            Wait for a random amount of time between _beaconInterval and _beaconInterval + _beaconBackoff before sending a beacon
        @param[in]  _beaconFrequency
            Frequency to use for sending beacons
        @param[in]  _downlinkFrequency
            Frequency to use for sending data
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__currentState = 1 #See execute() for the meaning of each state
        
        self.__beaconInterval = _beaconInterval
        self.__beaconBackoff = _beaconBackoff
        self.__beaconFrequency = _beaconFrequency
        self.__downlinkFrequency = _downlinkFrequency
        
        #We use lists instead of queues because we want to be able to remove elements from the middle of the list
        self.__dataToSend: 'list[MACData]' = [] #List of the MACData units we need to send. 
        self.__sentData: 'list[MACData]' = [] #List of the MACData units we have sent but have not received an ack for. 
        
        self.__currentSequenceNumber = 0 #Sequence number of the next packet to send
        
        self.__gsRadioID = -1 #ID of the GS's radio that we are currently communicating with. 
        self.__nextBeaconTime = self.__ownernode.timestamp.copy().add_seconds(random.randint(self.__beaconInterval, self.__beaconInterval + self.__beaconBackoff)) #Time when we will send the next beacon
        self.__currentState = 1 #See execute() for the meaning of each state
        
def init_ModelMACTTnC(
                    _ownernodeins: INode, 
                    _loggerins: ILogger, 
                    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelMACTTnC class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key beacon_interval
            How often to send a beacon (in seconds)
        @key beacon_backoff
            Wait for a random amount of time between _beaconInterval and _beaconInterval + _beaconBackoff before sending a beacon
        @key beacon_frequency
            What frequency to send beacons
        @key downlink_frequency
            What frequency to send data on
    @return
        Instance of the model class
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    if "beacon_interval" not in _modelArgs or "beacon_backoff" not in _modelArgs or "beacon_frequency" not in _modelArgs or "downlink_frequency" not in _modelArgs:
        raise Exception("beacon_interval or beacon_backoff is not provided for ModelBeacon for node " + _ownernodeins.nodeID)

    return ModelMACTTnC(_ownernodeins, 
                          _loggerins,
                          _modelArgs.beacon_interval,
                          _modelArgs.beacon_backoff,
                          _modelArgs.beacon_frequency,
                          _modelArgs.downlink_frequency)