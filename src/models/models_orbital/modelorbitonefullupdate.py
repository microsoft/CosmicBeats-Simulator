"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 21 Dec 2022

@desc
    This module implements the orbital propagation model for the satellite.  
    It updates the positions of a satellite for the whole simulation period all at once at in the first execution.  
"""

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from skyfield.api import load, EarthSatellite
from src.utils import Location, Time

class ModelOrbitOneFullUpdate(IModel):
    '''
    This model class calculates the orbital propagation of the satellite based on the TLE. 
    It generates the location of the node, i.e., satellite against the time. 
    Its execute method updates the positions of a satellite for the whole simulation period all at once at in the first call. 
    '''
    __modeltag = EModelTag.ORBITAL
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = []
    __earthsatellite: EarthSatellite
    __logger: ILogger

    # model operation related parameters
    __simStartTime: Time
    __simEndTime: Time
    __simInterval: Time
    __isPositionUpdated: bool           # indicates whether the positions of the parent node have been updated
    
    
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
        
        This model does not offer any API
        '''
        pass
    
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

        # initiate the earth satellite instance
        self.__earthsatellite = None

        # Load the time of simulation
        self.__simStartTime = None
        self.__simEndTime = None
        self.__simInterval = None

        # make sure that the position update flag is down
        self.__isPositionUpdated = False

    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self.__modeltag.__str__()])

    def Execute(self):
        """
        @desc
            This method executes the tasks that needed to be performed by the model.
            The model updates all the positions of its parent node throughout the simulation time at one go
        """
        # check the flag to make sure that the positions haven't been updated yet
        if not self.__isPositionUpdated:
            # get timing info
            self.__simInterval = self.__ownernode.deltaTime
            self.__simStartTime = self.__ownernode.simStartTime
            self.__simEndTime = self.__ownernode.simEndTime
            
            # get TLE and set up the EarthSatellite
            _tlelines = self.__ownernode.get_TLE()
        
            if len(_tlelines) == 2:
                self.__earthsatellite = EarthSatellite(_tlelines[0], _tlelines[1])
            elif len(_tlelines) == 3:
                self.__earthsatellite = EarthSatellite(_tlelines[1], _tlelines[2])
            else:
                raise Exception("[Simulator Exception] Invalid number of TLE lines in " + self.iName)
        
            #initiate the time scale for skyfield operation 
            self.__skyfieldts = load.timescale()

            _nodeTime = self.__simStartTime

            while _nodeTime  <= self.__simEndTime:
                # calculate the time of the node
                _utcTime = self.__skyfieldts.utc(_nodeTime.to_datetime())

                # calculate the location
                _gcrsLocation = self.__earthsatellite.at(_utcTime)
                _itrs = _gcrsLocation.itrf_xyz().m
                _newLocation = Location(_itrs[0], _itrs[1], _itrs[2])

                self.__logger.write_Log(
                                    f"Location of node {self.__ownernode.nodeID} is: {_newLocation.to_str()}",
                                    ELogType.LOGINFO, 
                                    _nodeTime)

                # update the location
                self.__ownernode.update_Position(_newLocation, _nodeTime)

                # update the time for the next position
                _nodeTime.add_seconds(self.__simInterval)
            
            # remember to set the flag to avoid multiple updates
            self.__isPositionUpdated = True

def init_ModelOrbitOneFullUpdate(
        _ownernodeins: INode, 
        _loggerins: ILogger, 
        _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        The JSON object does NOT require ANY arguments specifically for this model.
    @return
        Instance of the model class
    '''
    # check the arguments
    assert _ownernodeins is not None
    assert _loggerins is not None

    return ModelOrbitOneFullUpdate(
                            _ownernodeins, 
                            _loggerins)