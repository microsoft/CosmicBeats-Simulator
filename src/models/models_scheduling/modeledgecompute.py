'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 16 July 2023
@desc
    This model represents a scheduler for a satellite performing edge computing.
    
    In this model, the satellite has to decide whether it should perform the computation locally
    or send it to the ground station.
    
    For now, let's assume that a satellite should always have something to transmit and compute.
'''
from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ELogType, ILogger
from src.utils import Time

import pickle

class ModelEdgeCompute(IModel):
    __modeltag = EModelTag.SCHEDULER
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = [['ModelPower'], ['ModelCompute'], ['ModelImagingRadio']]
    
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
        return "Model name: " + self.iName + "; " + "Model tag: " + self.__modeltag.__str__()
        
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
            _ret = self.__apiHandlerDictionary[_apiName](self, **_kwargs)
        except Exception as e:
            print(f"[ModelEdgeCompute]: An unhandled API request has been received by {self.iName}:", e)
        
        return _ret
    
    def Execute(self):
        if self.__radioModel is None:
            self.__radioModel = self.__ownernode.has_ModelWithTag(EModelTag.IMAGINGRADIO)
            self.__dataStorage = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE)
            self.__computeModel = self.__ownernode.has_ModelWithTag(EModelTag.COMPUTE)
            
        if self.__currentImage is None:
            #let's see if we have some data to transmit here
            self.__currentImage = self.__dataStorage.call_APIs("get_Data")
            
        if self.__currentImage is not None:
            #Let's find the spot in the schedule. The schedule is a list of (id, starttime) tuples. 
            #The end time is 1 minute after the start time
            _wantedID = None
            _currTime = self.__ownernode.timestamp
            
            #If we have a schedule, let's find out where who we should transmit to
            if self.__schedule is not None:
                for _id, _starttime, _endtime in self.__schedule:
                    if _currTime >= _starttime and _currTime <= _endtime:
                        _wantedID = _id
                        break
            
                #If we have found a spot in the schedule, let's transmit the image
                if _wantedID is not None:
                    self.__logger.write_Log("Tranmitting to {}".format(_wantedID), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                    #Let's see if we can transmit it to the ground station
                    _res = self.__radioModel.call_APIs("send_Packet", _packet = self.__currentImage, _destinationID = _wantedID)
                    if _res:
                        #We have transmitted the image. Let's set the current image to None
                        self.__currentImage = None
            else:
                #If we don't have a schedule, let's just try to transmit it to the ground station
                _res = self.__radioModel.call_APIs("send_Packet", _packet = self.__currentImage)
                if _res:
                    #We have transmitted the image. Let's set the current image to None
                    self.__currentImage = None
                    
            #else, we will try to transmit it again in the next iteration
        
        if self.__currentImage is None:
            #let's see if we have some data to transmit here
            self.__currentImage = self.__dataStorage.call_APIs("get_Data")
        
        #Now, let's check if we are running computation
        if self.__computeModel.call_APIs("get_QueueSize") == 0:
            self.__computeModel.call_APIs("add_Data", _data = self.__currentImage)
            self.__currentImage = None
        
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _schedulePath: str = None
            ) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _schedulePath
            Path of the schedule file
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        self.__currentImage = None
        
        self.__radioModel = None
        
        if _schedulePath is not None:
            self.__schedule = pickle.load(open(_schedulePath, "rb"))
        else:
            self.__schedule = None

def init_ModelEdgeCompute(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelEdgeCompute class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key schedule_path
            A pickle file containing the schedule of the satellite. 
            It should be a list of (destinationID, starttime, endtime) tuples. See a global scheduler for more details.
            This is optional. If not provided, the model will default to the first ground station in the list of ground stations.
    @return
        Instance of the model class
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    
    _schedulePath = None
    if hasattr(_modelArgs, "schedule_path"):
        _schedulePath = _modelArgs.schedule_path
        
    return ModelEdgeCompute(_ownernodeins, 
                          _loggerins,
                          _schedulePath)