'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 17 March 2023
@desc
    This model automatically transmits the data received from the radio model to the radio's model transmit buffer.
'''

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger

class ModelDataRelay(IModel):
    __modeltag = EModelTag.DATASTORE
    __ownernode: INode
    __supportednodeclasses = []
    __dependencies = [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio', 'ModelImagingRadio']]  
    __logger: ILogger
    
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
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self.__modeltag.__str__()])
    
    def __add_Data(self, **_kwargs):
        """
        @desc
            API handler for adding data to the transmit buffer
        @param[in]  _kwargs
            Keyworded arguments 
            @key _data
                The data to be added
        @return
            True if the data is added to the transmit buffer, False otherwise
        """
        _data = _kwargs['_data']
        _isDataAddedToQueue = self.__radioTxQueue.put(_data)
        return _isDataAddedToQueue
        
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "add_Data": __add_Data
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
        This model does not have any API. So, this method does nothing.
        '''
        _ret = None

        try:
            _ret = self.__apiHandlerDictionary[_apiName](self, **_kwargs)
        except Exception as e:
            print(f"[ModelDataRelay]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
    
    def Execute(self):
        '''
        @desc
            This method moves the received data to the output buffer
        '''
        if self.__radioModel is None:
            self.__radioModel = self.__ownernode.has_ModelWithTag(EModelTag.IMAGINGRADIO)
            
        while (_data := self.__radioModel.call_APIs("get_ReceivedPacket")) is not None:
            self.__logger.write_Log(f"Received and Moving to Transmit packet {_data.id}", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                
            ## send the data object to the radio model
            _isDataAddedToQueue = self.__radioTxQueue.put(_data)
            
            if not _isDataAddedToQueue:
                self.__logger.write_Log(f"Dropping sensor data unit with ID {_data.id} for radio model denial", ELogType.LOGINFO, self.__ownernode.timestamp)

    def __init__(
            self,  
            _ownernodeins: INode, 
            _loggerins: ILogger,
            ) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        '''
        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__radioRxQueue = None
        self.__radioTxQueue = None
        self.__radioModel = None
        
def init_ModelDataRelay(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelDataRelay class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        None required for this model
    @return
        Instance of the model class
    '''
    
    assert _ownernodeins is not None
    assert _loggerins is not None
    assert _modelArgs is not None
        
    return ModelDataRelay(
                        _ownernodeins, 
                        _loggerins)
