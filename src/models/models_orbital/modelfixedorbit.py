"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 8 June 2023

@desc
    This is an orbital model class used for testing purposes. You can pass in a location, and the satellite will be CONSTANTLY at that location.
"""

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from skyfield.positionlib import Barycentric
from src.utils import Location

class ModelFixedOrbit(IModel):
    '''
    This model class basically calculates the orbital propagation of the satellite based on the TLE.
    It takes the timestamp of the node and updates the location of the node, i.e., satellite
    '''
    __modeltag = EModelTag.ORBITAL
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = []
    __logger: ILogger

    
    @property
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the model class. For example, ModelPower 
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
    
    def __in_Sunlight(self, **_kwargs) -> bool:
        '''
        This method checks if the satellite is in sunlight
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this method
        @return
            True if the satellite is in sunlight, false otherwise
        '''
        return self.__sunlit

    def __get_RelativeMotion(self, **_kwargs) -> 'Tuple[float, float]':
        '''
        This method calculates the relative motion between the satellite and a ground device such as ground station, IoT device.
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
                @key _gs
                    The ground device (Assumed that the ground device is stationary)
        @return
            Tuple (distance, relative velocity) in m and m/s respectively
        '''
        pos = self.__ownernode.get_Position()
        gsPos = _kwargs['_gs'].get_Position()
        dist = pos.get_distance(gsPos)
        
        return (dist, 0) 
    
    def __get_Position(self, **kwargs):
        """
        This method calculates the position of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
                @key _time
                    The time at which the position is to be calculated (utils.Time)
        @return
            utils.Location object containing the position of the satellite
        """
        return self.__position
    
    def __get_Velocity(self, **kwargs):
        """
        This method calculates the velocity of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
                @key _time
                    The time at which the velocity is to be calculated (utils.Time)
        @return
            The velocity of the satellite at the given time (x, y, z) in m/s (tuple of floats)
        """
        return (0, 0, 0)
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "in_Sunlight": __in_Sunlight,
        "get_RelativeMotion": __get_RelativeMotion,
        "get_Position": __get_Position,
        "get_Velocity": __get_Velocity
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
            print(f"[ModelFixedOrbit]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
        
        return _ret
        
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _pos: 'Location', 
            _sunlit: bool) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _pos
            Location of the satellite
        @param[in]  _sunlit
            True if the satellite is in sunlight, false otherwise
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins

        self.__position = _pos
        self.__sunlit = _sunlit

    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self.__modeltag.__str__()])

    def Execute(self):
        """
        @desc
            This method executes the tasks that needed to be performed by the model.
        """
        #nothing to do
        pass

def init_ModelFixedOrbit(
        _ownernodeins: INode, 
        _loggerins: ILogger, 
        _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelFixedOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key lat
            Latitude of the satellite in degrees
        @key lon
            Longitude of the satellite in degrees
        @key alt
            Altitude of the satellite in meters
        @key sunlit
            True if the satellite is in sunlight, false otherwise
    @return
        Instance of the model class
    '''
    assert _ownernodeins is not None
    assert _loggerins is not None

    if 'lat' not in _modelArgs or 'lon' not in _modelArgs or 'alt' not in _modelArgs or 'sunlit' not in _modelArgs:
        raise Exception("ModelFixedOrbit: Missing arguments. Expected: lat, lon, alt, sunlit")
    
    # should take in lat, lon, alt, sunlit
    _pos = Location().from_lat_long(_modelArgs.lat, _modelArgs.lon, _modelArgs.alt)
    _sunlit = _modelArgs.sunlit
    
    return ModelFixedOrbit(_ownernodeins, _loggerins, _pos, _sunlit)