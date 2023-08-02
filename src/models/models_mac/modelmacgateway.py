'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
@desc
    This MAC Layer model is designed for satellite-to-IoT device communication management. The model operates through the following steps:

        1. At each iteration, it examines the RX queue of the ModelAggregatorRadio (uplink) to check for any received packets.
        2. Upon receiving a packet, it transmits an acknowledgment (ACK) back to the device using the same uplink ModelAggregatorRadio.
        3. The received packet is then stored in the satellite's local storage.
        Both the acknowledgments and packets are sent and received using the ModelAggregatorRadio's frequency.
'''
import pickle


from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.network.macdata.macack import MACAck

class ModelMACgateway(IModel):
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
            print(f"[ModelMACgateway]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
            
    def __get_ReceivedData(self):
        """
        @desc
            This method returns the received data
        @return
            List of received data
        """
        _loraModel = self.__ownernode.has_ModelWithName("ModelAggregatorRadio")
        if _loraModel is None:
            raise Exception("ModelAggregatorRadio is not found for owner node: " + str(self.__ownernode.nodeId))
        
        #the received data is a list of the received data
        _receivedData = [] 
        while (_data := _loraModel.call_APIs("get_ReceivedPacket")) is not None:
            _receivedData.append(_data)
        
        return _receivedData
        
    def __send_Ack(self, _ack):
        """
        @desc
            This method sends an ack through the radio
        @param[in] _ack
            The ack to be sent
        @return
            True if the data is sent, False otherwise
        """
        _uplinkRadio = self.__ownernode.has_ModelWithName("ModelAggregatorRadio")
        if _uplinkRadio is None:
            raise Exception("ModelAggregatorRadio model is not found for owner node: " + str(self.__ownernode.nodeId))
        self.__logger.write_Log(f"Sending ACK with ID {_ack.id}", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
        return _uplinkRadio.call_APIs("send_Packet", _packet = _ack)
    
    def Execute(self):
        #let's first receive the data
        _receivedDatas = self.__get_ReceivedData()
        if len(_receivedDatas) == 0:
            return
        if len(_receivedDatas) > 1:
            #We only expect one data at a time since we are running at a fine granularity
            raise Exception("More than one data received. This is not expected. Make the granularity finer.")
        
        _receivedData = _receivedDatas[0]
        _uplinkModel = self.__ownernode.has_ModelWithName("ModelAggregatorRadio")
        
        self.__logger.write_Log(f"Received MACData with ID {_receivedData.id}", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)        
        #Let's create the acks
        _currentTime = self.__ownernode.timestamp.copy()
        _size = 4 #(I'm assuming that the data size is 4 bytes)
        _ack = MACAck(creationTime=_currentTime,
                      sourceRadioID=_uplinkModel.radioID,
                      size=_size,
                      intendedRadioID=_receivedData.sourceRadioID,
                      sequenceNumber=_receivedData.sequenceNumber + 1,
                      receivedMACDataID=_receivedData.id)
        
        #Let's send the ack.
        _success = self.__send_Ack(_ack)
        if not _success:
            #The ack could not be sent. This is likely because either we don't have enough power or now the iot device is out of range
            #Let's log this but keep going. We can't do anything about it
            self.__logger.write_Log(f"Could not send ack for MACData with ID {_receivedData.id}", ELogType.LOGWARN, self.__ownernode.timestamp, self.iName)
            
        #Now, let's send the data to the satellite's data store
        _dataModel = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE)
        if _dataModel is None:
            raise Exception("Data storage is not found for owner node: " + str(self.__ownernode.nodeId))
        _dataModel.call_APIs("add_Data", _data = pickle.loads(_receivedData.dataPayloadString))
        
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
def init_ModelMACgateway(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelMACgateway class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @return
        Instance of the model class
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    return ModelMACgateway(_ownernodeins, 
                          _loggerins)