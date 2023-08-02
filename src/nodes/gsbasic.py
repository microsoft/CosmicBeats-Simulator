'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 08 Nov 2022
@desc
    This module implements the basic ground station (GS) class
'''
from io import StringIO

from src.nodes.inode import INode, ENodeType
from src.utils import Time, Location
from src.simlogging.ilogger import ILogger, ELogType
from src.models.imodel import IModel, EModelTag
from src.sim.imanager import IManager

class GSBasic(INode):
    '''
    This class implements the basic ground station functionalities.
    It inherits INode interface
    '''
    
    __nodetype = ENodeType.GS
    __nodeid: int
    __topologyid: int
    __position: Location
    __managerinstance = None
    __logger: ILogger
    __timestamp: Time
    __endTimeStamp: Time
    __timedelta: float              #time granularity for the simulation
    __models: 'list[IModel]'          # List of models
    
    @property
    def iName(self)-> str:
        """
        @type 
            str
        @desc
            A string representing the name of the node class. For example, NodeSatellite 
            Note that the name should exactly match to your class name. 
        """
        return self.__class__.__name__
    
    @property
    def nodeType(self) -> ENodeType:
        """
        @type
            ENodeType
        @desc
            The node type for the implemented node class
        """
        return self.__nodetype
    
    @property
    def nodeID(self) -> int:
        """
        @type 
            int
        @desc
            The ID of a node in the topology. It basically distinguishes a node from another node.  
        """
        return self.__nodeid
    
    @property
    def topologyID(self) -> int:
        """
        @type 
            int
        @desc
            The ID of the topology that the node instance is part of
        """
        return self.__topologyid
    
    @property
    def timestamp(self) -> Time:
        """
        @type
            Time
        @desc
            Current timestamp of the node instance 
        """
        return self.__timestamp
    @property
    def simStartTime(self) -> Time:
        """
        @type
            Time
        @desc
            Start timestamp of the node instance for simulation 
        """
        return self.__startTimeStamp

    @property
    def simEndTime(self) -> Time:
        """
        @type
            Time
        @desc
            End timestamp of the node instance for simulation
        """
        return self.__endTimeStamp
    
    @property
    def deltaTime(self) -> float:
        """
        @type
            Float
        @desc
            time granularity for the simulation of this node (in seconds).
            Time gap between two simulation epochs
        """
        return self.__timedelta
    
    @property
    def position(self) -> Location:
        """
        @type
            Location
        @desc
            The position of the node. The implementing class can keep location as a private variable and return it through this method. 
        """
        return self.__position
    
    @property
    def managerInstance(self):
        """
        @type
            Manager class
        @desc
            Manager instance of the simulator that is holding this node instance  
        """
        return self.__managerinstance

    def add_Models(
            self, 
            _modelsToAdd: 'list[IModel]'):
        """
        @desc
            This method adds a model to the node
        @param[in]  _modelsToAdd    
           The instance of the model to be added
        """
        assert _modelsToAdd is not None

        self.__models.extend(_modelsToAdd)
    
    def has_ModelWithTag(
            self, 
            _modelTag: EModelTag) -> IModel:
        """
        @desc
            This method checks whether this node instance has a model implemented having the provided model tag.
            If so, it returns the model.
        @param[in]  _modelTag    
           Tag of the model that is being looked for
        @return
            Instance of the model if it was found.
            Otherwise, None 
        """
        _ret = None

        for _model in self.__models:
            if _model.modelTag.value == _modelTag.value:
                _ret = _model
                break
        
        return _ret
    
    def get_Models(self) -> 'list[IModel]':
        """
        @desc
            This method returns the list of models implemented by this node instance
        @return
            List of models implemented by this node instance
        """
        return self.__models
    
    def has_ModelWithName(
            self, 
            _modelName: str) -> IModel:
        """
        @desc
            This method checks whether this node instance has a model implemented having the provided model implementation name (iName).
            If so, it returns the model.
        @param[in]  _modelName    
           Implementation name (iName) of the model that is being looked for
        @return
            Instance of the model if it was found.
            Otherwise, None 
        """
        _ret = None

        for _model in self.__models:
            if _model.iName == _modelName:
                _ret = _model
                break
        
        return _ret

    def update_Position(
            self, 
            _newLocation: Location,
            _time: Time = None):
        """
        @desc
            This method updates the position of the node. 
            As we ar considering it as a static GS implementation, we don't expect time in the argument.
        @param[in]  _newLocation
            New location of the node
        @param[in]  _time
            None
        """
        assert _newLocation is not None

        self.__position = _newLocation

    def get_Position(
            self,
            _time: Time = None) -> Location:
        """
        @desc
            This method returns the position of the node.
             As we ar considering it as a static GS implementation, we don't expect time in the argument.
        @param[in]  _time
            None
        @return
            Location of the node, if available
            otherwise, none
        """

        _ret = None

        _ret = self.__position

        return _ret
    
    @property
    def lat(self) -> float:
        """
        @type
            float
        @desc
            Latitude of the node
        """
        return self.__lat
    
    @property
    def lon(self) -> float:
        """
        @type
            float
        @desc
            Longitude of the node
        """
        return self.__lon
    
    @property
    def alt(self) -> float:
        """
        @type
            float
        @desc
            Altitude of the node
        """
        return self.__alt

    def add_ManagerInstance(
            self, 
            _managerIns: IManager):
        '''
        @desc
            Adds manager instance to this node instance
        @param[in]  _managerIns
            Manager instance as IManager
        '''
        assert _managerIns is not None
        self.__managerinstance = _managerIns
    
    def __init__(
            self, 
            _nodeID: int, 
            _topologyID: int, 
            _location: Location, 
            _timeDelta: float, 
            _timeStamp: Time, 
            _endtime: Time, 
            _Logger: ILogger, 
            *_additionalArgs) -> None:
        '''
        @desc
            Constructor of the satellite basic class
        @param[in]  _nodeID
            The ID of a node in the topology. It basically distinguishes a node from another node.
        @param[in]  _topologyID
            The ID of the topology that the node instance is part of
        @param[in]  _location
            Location of the ground station on earth
        @param[in]  _timeDelta
            time granularity for the simulation of this node (in seconds)
        @param[in]  _timeStamp
            Timestamp for the node. Typically, start time 
        @param[in]  _endtime
            End timestamp of the simulation for this node
        @param[in]  _Logger
            Logger instance
        '''
        self.__nodeid = _nodeID
        self.__topologyid = _topologyID
        self.__position = _location
        self.__lat, self.__lon, self.__alt = _location.to_lat_long() #Saves us from calling the function multiple times
        self.__timedelta = _timeDelta
        self.__timestamp = _timeStamp.copy()
        self.__startTimeStamp = _timeStamp
        self.__endTimeStamp = _endtime
        self.__logger = _Logger
        self.__models = []
    
    def Execute(self) -> bool:
        """
        @desc
            This method executes the models of the node instance one by one. 
            This is one time execution of the models.
        @return
            True:   If the execution is successful
            False:  Otherwise
        """
        _ret = False
        if self.__timestamp <= self.__endTimeStamp:
            self.__logger.write_Log("Executing", ELogType.LOGDEBUG, self.__timestamp)
            
            # execute the models one by one, if any
            for _model in self.__models:
                _model.Execute() 

            # update the time of the node
            self.__timestamp.add_seconds(self.__timedelta)
            _ret = True
        
        return _ret
    
    def ExecuteCntd(self):
        """
        @desc
        This method executes the models of the node instance one by one continuously until
        it reaches simulation end time.
        """
        while self.__timestamp <= self.__endTimeStamp:
            self.__logger.write_Log("Executing", ELogType.LOGDEBUG, self.__timestamp)
            
            # execute the models one by one, if any
            for _model in self.__models:
                _model.Execute() 

            # update the time of the node
            self.__timestamp.add_seconds(self.__timedelta)
    
    def __str__(self):      

        _nodeDetails = "".join(["GS node ID:: ", str(self.__nodeid), ", ",
                        "Topology ID: ", str(self.__topologyid), ", "
                        "Current location: ", self.__position.to_str(), ", ",
                        "Current time: ", self.__timestamp.to_str(), ", ",
                        "End time: ", self.__endTimeStamp.to_str(), ", ",
                        "Models (if any): "])

        _stringIOObject = StringIO(_nodeDetails)
        for _model in self.__models:
            _stringIOObject.write(_model.__str__())
            _stringIOObject.write(", ")

        return _stringIOObject.getvalue()

def init_GSBasic(
        _nodeDetails, 
        _timeDetails, 
        _topologyID, 
        _logger)-> INode:
    '''
    @desc
        This method initializes an instance of SatelliteBasic class
    @param[in]  _nodeDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "nodeid": 1,
            "latitude": 49.3,
            "longitude": -122.2,
            "elevation": 0.0,
            "additionalargs": ""
        }
    @param[in]  _timeDetails
        It's a converted JSON object containing the simulation timing related info. 
        The JOSN object must have the literals as follows (values are given as example).
        {
            "starttime": "2022-10-14 12:00:00",
            "endtime": "2022-10-14 13:00:00",
            "delta": 5.0
        }
    @param[in]  _topologyID
        The ID of the topology that the node instance is part of
    @param[in]  _logger
        Logger instance
    @return
        Created instance of the class
    '''
    # Check whether the arguments contain required parameter
    assert type(_nodeDetails.nodeid) is int
    assert type(_nodeDetails.latitude) is float
    assert type(_nodeDetails.longitude) is float
    assert type(_nodeDetails.elevation) is float

    _location = Location().from_lat_long(
                    _nodeDetails.latitude, 
                    _nodeDetails.longitude, 
                    _nodeDetails.elevation)

    assert _timeDetails is not None

    assert _timeDetails.starttime != ''
    _simStartTime = Time().from_str(_timeDetails.starttime)

    assert _timeDetails.endtime != ''
    _simEndTime = Time().from_str(_timeDetails.endtime)

    assert _timeDetails.delta > 0
    _timeDelta = _timeDetails.delta

    assert _logger is not None

    _newNode = GSBasic(
                _nodeDetails.nodeid, 
                _topologyID, 
                _location, 
                _timeDelta, 
                _simStartTime, 
                _simEndTime, 
                _logger, 
                _nodeDetails.additionalargs)
    return _newNode