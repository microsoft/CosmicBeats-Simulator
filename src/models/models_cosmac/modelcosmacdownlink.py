'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023
Updated: 2024

@desc
    This model implements the CosMAC (Constellation-Aware Medium Access and Scheduling for IoT Satellites) downlink protocol.
    Based on the paper: https://deepakv.web.illinois.edu/assets/papers/CosMAC_MobiCom_2024.pdf
    
    This model manages MAC layer functionality for satellite-to-ground transmission in IoT satellite constellations.
    It uses a pre-loaded schedule to determine transmission times and spreading factors (SF), enabling efficient
    downlink communication from satellites to IoT devices on the ground.
    
    The model coordinates with downlink radio models and data storage/generation models to transmit data packets
    according to a predetermined schedule that considers constellation dynamics and IoT device requirements.
'''

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ILogger
from src.models.network.macdata.macdata import MACData
import pickle

class ModelCosmacDownlink(IModel):
    __modeltag = EModelTag.MAC
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = [['ModelDownlinkRadio'],
                       ['ModelDataStore', 'ModelDataGenerator']]
    
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
            print(f"[ModelCosmacDownlink]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
            
        
    def Execute(self):
        """
        Main execution method called at each simulation timestep.
        
        This method:
        1. Initializes required models (downlink radio, data store/generator) on first run
        2. Checks the pre-loaded schedule to determine if it's time to transmit
        3. Retrieves data from the data store/generator if needed
        4. Packages data into MAC frames and transmits via the downlink radio
        5. Advances to the next scheduled transmission slot
        
        @raises Exception: If no data store or data generator model is found
        """
        if self.__downlinkModel is None:
            self.__downlinkModel = self.__ownernode.has_ModelWithName("ModelDownlinkRadio")
            self.__dataStore = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE) 
            if self.__dataStore is None:
                self.__dataStore = self.__ownernode.has_ModelWithTag(EModelTag.DATAGENERATOR)
                if self.__dataStore is None:
                    raise Exception(f"[ModelCosmacDownlink]: The node {self.__ownernode.nodeID} does not have a data store or data generator model")
        
        if self.__currentScheduleIndex == len(self.__loadedSchedule):
            return
        
        #For now, the downlink just checks the schedule file and sends the data at the appropriate times
        #Check if it is time to send the next packet
        #The start and end time is [start, end) 
        if self.__ownernode.timestamp >= self.__loadedSchedule[self.__currentScheduleIndex][0] and \
            self.__ownernode.timestamp < self.__loadedSchedule[self.__currentScheduleIndex][1]:          
                #It is time to send the next packet
                #Assign the SF

                if self.__currentData is None:
                    #We don't have any data loaded. Let's load the next data
                    _data = self.__dataStore.call_APIs("get_Data")
                        
                    #If there is data, let's package it
                    if _data is not None:
                        _time = self.__ownernode.timestamp.copy()
                        _size = _data.size + 4 #TODO: change this to the actual size
                        _payload = pickle.dumps(_data)
                        _data = MACData(creationTime=_time,
                                        sourceRadioID=self.__downlinkModel.radioID,
                                        size=_size,
                                        intendedRadioID=-1,
                                        sequenceNumber=self.__currentSequenceNumber,
                                        dataPayloadString=_payload)
                        self.__currentData = _data
                        self.__currentSequenceNumber += 1
                        
                #If we were able to load data, let's send it
                if self.__currentData is not None:
                    _success = self.__downlinkModel.call_APIs("send_Packet", _packet = self.__currentData)
                    if _success:
                        self.__currentData = None
        
        #Check if we need to move to the next schedule
        while self.__currentScheduleIndex < len(self.__loadedSchedule) and self.__ownernode.timestamp >= self.__loadedSchedule[self.__currentScheduleIndex][1]:
            self.__currentScheduleIndex += 1
                         
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _scheduleFile: str) -> None:
        '''
        Constructor for ModelCosmacDownlink.
        
        Initializes the COSMAC downlink model with a pre-loaded transmission schedule.
        The schedule determines when and how data should be transmitted.
        
        @param[in]  _ownernodeins: INode
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins: ILogger
            Logger instance for recording model events and debugging
        @param[in]  _scheduleFile: str
            Path to a pickle file containing the transmission schedule.
            Schedule format: List of tuples (start_time, end_time, spreading_factor)
            
        @raises AssertionError: If _ownernodeins or _loggerins is None
        @raises FileNotFoundError: If _scheduleFile cannot be found or loaded
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        
        self.__scheduleFile = _scheduleFile
        self.__loadedSchedule = pickle.load(open(self.__scheduleFile, "rb"))
        
        # Process loaded schedule: if there are only two indices instead of three, 
        # set end time to 60 seconds after start time with default SF of 11
        for _index, _schedule in enumerate(self.__loadedSchedule):
            if type(_schedule[0]) is int:
                self.__loadedSchedule[_index] = (_schedule[1], _schedule[1].copy().add_seconds(60), 11)
        
        # Initialize state variables
        self.__currentScheduleIndex = 0
        self.__downlinkModel = None  # Will be initialized on first Execute() call
        self.__dataStore = None      # Will be initialized on first Execute() call
        self.__currentSequenceNumber = 0
        self.__currentData = None    # Currently queued data packet
        
def init_ModelCosmacDownlink(
                    _ownernodeins: INode, 
                    _loggerins: ILogger, 
                    _modelArgs) -> IModel:
    '''
    Factory function to initialize a ModelCosmacDownlink instance.
    
    This function serves as the standard initialization interface for the COSMAC downlink model,
    extracting configuration parameters from the provided arguments.
    
    @param[in]  _ownernodeins: INode
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins: ILogger
        Logger instance for recording model events
    @param[in]  _modelArgs: object
        Configuration object containing model-specific parameters
        Required attributes:
        - schedule_file (str): Path to pickle file with transmission schedule
        
    @return IModel
        Initialized instance of ModelCosmacDownlink
        
    @raises AssertionError: If _ownernodeins or _loggerins is None
    @raises AttributeError: If required attributes are missing from _modelArgs
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    return ModelCosmacDownlink(_ownernodeins, 
                          _loggerins,
                          _modelArgs.schedule_file)
