'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
@desc
    This MAC layer model is designed specifically for ground stations. It operates through the following steps:

    1. he ground station listens for satellite beacons by checking the RX queue of the modelradio.
    2. Upon receiving a beacon, the ground station sends a data download request for a specific number of packets, denoted as "X."
    3. The satellite responds by transmitting up to "X" packets to the ground station.
    4. The ground station confirms the number of packets received and stores the received packets in its data store.
'''
import pickle

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ELogType, ILogger

from src.models.network.macdata.macbeacon import MACBeacon
from src.models.network.macdata.maccontrol import MACControl
from src.models.network.macdata.macdata import MACData
from src.models.network.macdata.macbulkack import MACBulkAck

from src.utils import Time

class ModelMACgs(IModel):
    
    __modeltag = EModelTag.MAC
    __ownernode: INode
    __supportednodeclasses = ['GSBasic']
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
            print(f"[ModelMACgs]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
            
    def __get_ReceivedData(self, _loraModel):
        """
        @desc
            This method returns the received data
        @return
            List of received data
        """
        #the received data is a list of the received data. This can be beacons or acks
        _receivedData = [] 
        while (_data := _loraModel.call_APIs("get_ReceivedPacket")) is not None:
            _receivedData.append(_data)
        
        return _receivedData
    
    def __get_BeaconIDS(self, _receivedData):
        """
        @desc
            This method returns if a beacon is received
        @param[in] _receivedData
            List of received data. This should be the output of __get_ReceivedData and should contain either acks or beacons
        @return
            List of the IDs of the satellites that sent the beacons
        """
        _beaconIDS = []
        for _data in _receivedData:
            if isinstance(_data, MACBeacon):
                _beaconIDS.append(_data.sourceRadioID)
        return _beaconIDS
    
    def __send_ControlPacket(self, _loraModel, _satelliteID, _numWantedPackets):
        """
        @desc
            This method sends a control packet to the satellite with the given ID
        @param[in] _loraModel
            The lora model instance
        @param[in] _satelliteID
            The ID of the satellite to send the control packet to
        @param[in] _numWantedPackets
            The number of packets that the satellite should send
        @return
            List of the IDs of the satellites that sent the beacons
        """
        _time = self.__ownernode.timestamp.copy()
        _size = 8 #(bytes 4 bytes for satellite ID, 4 bytes for number of packets) - change this to the actual size of the payload
        _controlPacket = MACControl(creationTime=_time,
                                    sourceRadioID=_loraModel.radioID,
                                    size=_size,
                                    intendedRadioID=_satelliteID,
                                    sequenceNumber=self.__sequenceNumber,
                                    numPacketsToSend=_numWantedPackets
                                    )
        self.__sequenceNumber += 1
                   
        self.__logger.write_Log("Sending control packet asking for " + str(_controlPacket.numPacketsToSend), ELogType.LOGINFO, _time, self.iName)
        
        _loraModel.call_APIs("send_Packet", _packet = _controlPacket)  
        
    def __send_BulkAck(self, _loraModel, _satelliteID, _macUnitsReceived: 'List[int]'):
        """
        @desc
            This method sends an ack to the satellite with the given ID
        @param[in] _loraModel
            The lora model instance to send the data on
        @param[in] _satelliteID
            The ID of the satellite to send the ack to
        @param[in] _macUnitsReceived
            The list of the ids of the MACData units that the satellite has received
        """
        _time = self.__ownernode.timestamp.copy()
        _size = 8 #(bytes 4 bytes for satellite ID, 4 bytes for data ID) - change this to the actual size of the payload
        _ack = MACBulkAck(creationTime=_time,
                          sourceRadioID=_loraModel.radioID,
                          size=_size,
                          intendedRadioID=_satelliteID,
                          sequenceNumber=self.__sequenceNumber,
                          receivedMACDataIDs=_macUnitsReceived)
        self.__sequenceNumber += 1
        
        self.__logger.write_Log(f"Sending bulk ack for packets: {_macUnitsReceived}", ELogType.LOGINFO, _time, self.iName)
        
        _loraModel.call_APIs("send_Packet", _packet = _ack)
        
    def Execute(self):      
        #The ground station might be in the vicinity of multiple satellites.
        #It should only send a control packet to one satellite at a time. 
        #The ground station can be in one of the following states:
        #1. We are waiting for a beacon from any satellite. We are listening on the beacon frequency
        #2. We have received a beacon from a satellite. Let's switch to the downlink frequency and send a control packet to the satellite
        #3. We have received n >= 0 packets. 
        #       If we have received all the data, let's go reset to state 1. 
        #       If we receive a control without receiving all the data, let's resend the control with the list of received packets
        #       If we don't receive any packets from the satellite after the timeout, the sat is likely out of view -let's go to state 1 for another sat
        #       If we receive any MACData from any satellite, let's keep it in the data store, but don't change what we are doing
        #       Ignore beacons from other satellites (we don't want another satellite to also send us packets and cause collisions. We shouldn't get them anyway)
        
        _loraModel = self.__ownernode.has_ModelWithTag(EModelTag.BASICLORARADIO)
        if _loraModel is None:
            raise Exception("Basic LoRa Radio model is not found for owner node: " + str(self.__ownernode.nodeId))
        
        #let's get all of the data from the radio model
        _receivedData = self.__get_ReceivedData(_loraModel)
       
        #State 1: We are waiting for a beacon from any satellite
        if self.__currentState == 1: 
            #If the ground station is in state 1, it should be listening on the beacon frequency
            _loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency) #This should already be set, but let's set it again just in case
            
            _satRadioIDs = self.__get_BeaconIDS(_receivedData)
            #Let's check if we have received a beacon from any satellite
            if len(_satRadioIDs) > 0:
                #We have received a beacon. Proceed to state 2
                self.__listeningRadioID = _satRadioIDs[0]
                self.__logger.write_Log("Received beacon from radio " + str(self.__listeningRadioID), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__currentState = 2
            else:
                #We have not received a beacon. Let's wait for the next time step
                return
        
        #State 2: We have received a beacon from the satellite. Let's send a control packet
        elif self.__currentState == 2:
            _loraModel.call_APIs("set_Frequency", _frequency = self.__downlinkFrequency)
            
            self.__send_ControlPacket(_loraModel, self.__listeningRadioID, self.__numPackets)
            
            #We need to reset the received packet IDs to keep track of the packets that we have received
            self.__receivedPacketIDs = set()
            self.__currentState = 3
            self.__lastTimeReceivedPacket = self.__ownernode.timestamp.copy()
         
        #State 3: We have received n >= 0 packets
        elif self.__currentState == 3: 
            #If we have received some packets, let's process them
            if len(_receivedData) > 0:    
                #let's get the data store so that we can store the data
                _dataStore = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE)
                if _dataStore is None:
                    raise Exception("Data store model is not found for owner node: " + str(self.__ownernode.nodeID))
                
                for _data in _receivedData:
                    if isinstance(_data, MACData):
                        _payload = pickle.loads(_data.dataPayloadString)
                        
                        self.__logger.write_Log("Received MACData packet " + str(_data.id) + " with data id: " + str(_payload.id), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                        
                        _dataStore.call_APIs("add_Data", _data=_payload)
                        
                        #Add the packet ID to the list of received packet IDs
                        self.__logger.write_Log("Received MACData packet " + str(_data.id), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                        self.__receivedPacketIDs.add(_data.id)
                        self.__lastTimeReceivedPacket = self.__ownernode.timestamp.copy()
    
            #let's check if we have received an end of sequence control packet
            _satsControlPacket = [x for x in _receivedData if isinstance(x, MACControl) and x.sourceRadioID == self.__listeningRadioID]

            #If we have not received all the packets, let's check if we have received a control packet from the satellite. 
            #If we have, let's check the number of packets that the satellite wants to send us.
            if len(_satsControlPacket) > 0:
                self.__logger.write_Log("Received control packet from " + str(self.__listeningRadioID) + " :" + str(_satsControlPacket), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                _satsControlPacket = _satsControlPacket[0]
                
                self.__send_BulkAck(_loraModel, self.__listeningRadioID, list(self.__receivedPacketIDs))
                self.__lastTimeReceivedPacket = self.__ownernode.timestamp.copy()
                    
            #Let's check if we have not received any packets for a while. If we have, let's go to back to state 1
            elif Time.difference_in_seconds(self.__ownernode.timestamp, self.__lastTimeReceivedPacket) > self.__timeout:
                self.__logger.write_Log("Timed out waiting for packets from radio " + str(self.__listeningRadioID), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                _loraModel.call_APIs("set_Frequency", _frequency = self.__beaconFrequency)
                self.__currentState = 1
            
            #If we are here, we're still just listening for packets. Let's keep doing that
            
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _numPackets: int,
            _timeout: int,
            _beaconFrequency: int,
            _downlinkFrequency: int,
            ) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _numPackets
            Number of packets to ask the satellite to send
        @param[in]  _timeout
            How long to wait to not receive any packets from the satellite before moving on.
            This is necessary because the satellite might leave the gs range and we don't want to wait forever
        @param[in]  _beaconFrequency
            The frequency at which the satellite sends beacons
        @param[in]  _downlinkFrequency
            The frequency at which the satellite sends downlink packets
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__currentState = 1 #See execute() for the meaning of each state
        
        self.__numPackets = _numPackets #Number of packets to ask the satellite to send
        self.__timeout = _timeout #How long to wait to not receive any packets from the satellite before moving on.
        
        self.__beaconFrequency = _beaconFrequency
        self.__downlinkFrequency = _downlinkFrequency
        
        self.__receivedPacketIDs = set() #Set of received packet IDs
        self.__listeningRadioID = -1 #ID of the satellite's radio that we are listening to 
        self.__lastTimeReceivedPacket = -1 #Time when we last received a packet from the satellite that we are communicating with
        self.__sequenceNumber = 0 #Sequence number of the control packet that we are sending to the satellite
        
def init_ModelMACgs(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelMACgs class
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
        @key downlink_frequency
            What frequency to listen for data packets from the satellite
    @return
        Instance of the model class
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    if "num_packets" not in _modelArgs or "timeout" not in _modelArgs or "beacon_frequency" not in _modelArgs or "downlink_frequency" not in _modelArgs:
        raise Exception("num_packets, timeout, beacon_frequency, or downlink_frequency is not provided for ModelMACgs for node " + _ownernodeins.nodeID)

    return ModelMACgs(_ownernodeins, 
                          _loggerins,
                          _modelArgs.num_packets,
                          _modelArgs.timeout,
                          _modelArgs.beacon_frequency,
                          _modelArgs.downlink_frequency)