'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
Updated: 2024

@desc
    This model implements the CosMAC (Constellation-Aware Medium Access and Scheduling for IoT Satellites) ground station protocol.
    Based on the paper: https://deepakv.web.illinois.edu/assets/papers/CosMAC_MobiCom_2024.pdf
    
    This model manages ground station functionality for receiving and processing data from satellites
    in the CosMAC IoT satellite constellation system. It handles:
    1. Reception of MAC data packets from satellites via LoRa radio
    2. Data extraction and storage in the ground station's data store
    3. Integration with the broader CosMAC ecosystem for IoT data collection
    
    The model operates as a simple receiver, processing all incoming MAC data packets
    and storing the payload data for further analysis or forwarding.
'''

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ILogger
from src.models.network.macdata.macdata import MACData
import pickle

class ModelCosmacGS(IModel):
    __modeltag = EModelTag.MAC
    __ownernode: INode
    __supportednodeclasses = []
    __dependencies = [['ModelLoraRadio'],
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
            print(f"[ModelCosmacGS]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
            
        
    def Execute(self):
        """
        Main execution method for the CosMAC ground station model.
        
        This method:
        1. Initializes required models (LoRa radio, data store) on first execution
        2. Receives all available packets from the LoRa radio interface
        3. Processes MAC data packets and extracts payload data
        4. Stores extracted data in the ground station's data store
        
        The method operates continuously, processing all available packets
        in each execution cycle.
        """
        # Initialize required models on first execution
        if self.__loraModel is None:
            self.__loraModel = self.__ownernode.has_ModelWithTag(EModelTag.BASICLORARADIO)
            self.__dataStore = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE)
        
        # Receive all available packets
        _receivedData = [] 
        while (_data := self.__loraModel.call_APIs("get_ReceivedPacket")) is not None:
            _receivedData.append(_data)
        
        # Process received MAC data packets
        if len(_receivedData) > 0:
            for _data in _receivedData:
                if isinstance(_data, MACData):
                    # Extract and store payload data
                    self.__dataStore.call_APIs("add_Data", _data = pickle.loads(_data.dataPayloadString))
        
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger) -> None:
        '''
        Constructor for ModelCosmacGS.
        
        Initializes the CosMAC ground station model for receiving and processing
        data from satellites in the constellation.
        
        @param[in]  _ownernodeins: INode
            Instance of the ground station node that incorporates this model
        @param[in]  _loggerins: ILogger
            Logger instance for recording model events and debugging
            
        @raises AssertionError: If _ownernodeins or _loggerins is None
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None
        
        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__dataStore = None
        self.__loraModel = None
        
def init_ModelCosmacGS(
                    _ownernodeins: INode, 
                    _loggerins: ILogger, 
                    _modelArgs) -> IModel:
    '''
    Factory function to initialize a ModelCosmacGS instance.
    
    Creates and configures a CosMAC ground station model instance.
    This function serves as the standard initialization interface for the simulator.
    
    @param[in]  _ownernodeins: INode
        Instance of the ground station node
    @param[in]  _loggerins: ILogger
        Logger instance for recording model events
    @param[in]  _modelArgs: object
        Configuration object (currently unused for ground station model)
        
    @return IModel
        Initialized instance of ModelCosmacGS
        
    @raises AssertionError: If _ownernodeins or _loggerins is None
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    return ModelCosmacGS(_ownernodeins, 
                          _loggerins)