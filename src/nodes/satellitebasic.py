'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 13 Oct 2022
@desc
    It implements a very basic satellite class inheriting INode
'''


from src.nodes.inode import INode, ENodeType
from src.utils import Location
from src.simlogging.ilogger import ELogType, ILogger
from src.utils import Time
from src.models.imodel import IModel, EModelTag
from src.sim.imanager import IManager
from io import StringIO

class SatelliteBasic(INode):
    '''
    A satellite class implementing the basic satellite functionalities 
    '''
    __nodetype = ENodeType.SAT
    __nodeid: int
    __topologyid: int
    __tle: 'list[str]'
    __positionDictionary: dict
    __managerinstance = None
    __logger: ILogger
    __timestamp: Time
    __endTimeStamp: Time
    __timedelta: float                      # time granularity for the simulation
    __models: 'list[IModel]'                 # List of models

    
    @property
    def iName(self) -> str:
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
    def managerInstance(self):
        """
        @type
            Manager class
        @desc
            Manager instance of the simulator that is holding this node instance  
        """
        if self.__managerinstance is None:
            raise Exception("Manager instance is not set yet")
        return self.__managerinstance
    
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
            self.__logger.write_Log(f"Executing All Models At Once {str(self)}", ELogType.LOGDEBUG, self.__timestamp)
            
            # execute the models one by one, if any
            for _model in self.__models:
                _model.Execute() 

            # update the time of the node
            self.__timestamp.add_seconds(self.__timedelta)
    
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
        for _model in _modelsToAdd:
            self.__tagToModels[_model.modelTag] = _model
    
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
        return self.__tagToModels.get(_modelTag, None)
    
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
    
    def get_Models(self) -> 'list[IModel]':
        """
        @desc
            This method returns the list of models implemented by this node instance
        @return
            List of models implemented by this node instance
        """
        return self.__models

    def update_Position(
            self, 
            _newLocation: Location,
            _time: Time):
        """
        @desc
            This method updates the position of the node against a time provided in the argument
        @param[in]  _newLocation
            New location of the node
        @param[in]  _time
            The time when location is captured
        """
        assert _newLocation is not None
        assert _time is not None

        self.__positionDictionary[_time.to_str()] = _newLocation

    def get_Position(
            self,
            _time: Time=None) -> Location:
        """
        @desc
            This method returns the position of the node at the time provided in the argument. 
        @param[in]  _time
            The time at which the location is being looked for
        @return
            Location of the node, if available
            otherwise, none
        """
        if _time is None:
            _time = self.__timestamp
        assert _time is not None

        _ret = None

        _ret = self.__positionDictionary.get(_time.to_str())
        #There's a chance that the position is not calculated yet, so let's try to calculate it
        if _ret is None:
            #let's first see if we can calculate the position at this time
            _modelOrbit = self.has_ModelWithTag(EModelTag.ORBITAL)
            if _modelOrbit is not None:
                _ret = _modelOrbit.call_APIs("get_Position", _time=_time)
                if _ret is not None:
                    return _ret
            
            #if we are here, it means that we cannot calculate the position at this time    
            raise Exception(f"Position not found for node  {str(self.nodeID)} at time: {_time.to_str()}. Calculated times are: {str(self.__positionDictionary.keys())}")
        
        return _ret

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

    def get_TLE(self) -> 'list[str]':
        '''
        @desc
            Get the TLE of this node
        @return
            TLE lines in a list of strings
        '''
        return self.__tle

    def __init__(
            self, 
            _nodeID: int, 
            _topologyID: int, 
            _tleline1: str, 
            _tleline2: str, 
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
        @param[in]  _tleline1
            The first TLE line of the satellite
        @param[in]  _tleline2
            The second TLE line of the satellite
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
        self.__tle = [_tleline1, _tleline2]
        self.__timedelta = _timeDelta
        self.__timestamp = _timeStamp.copy()
        self.__startTimeStamp = _timeStamp.copy()
        self.__endTimeStamp = _endtime
        self.__logger = _Logger
        self.__models = []
        self.__positionDictionary = dict()
        self.__tagToModels = {}
    
    def __str__(self):
        
        _nodeDetails = "".join(["Satellite node ID: ", str(self.__nodeid), ", ",
                            "Topology ID: ", str(self.__topologyid), ", "
                            "TLE line 1: ", self.__tle[0], ", ",
                            "TLE line 2: ", self.__tle[1], ", ",
                            "Current time: ", self.__timestamp.to_str(), ", ",
                            "End time: ", self.__endTimeStamp.to_str(), ", ",
                            "Models (if any): "])
        
        _stringIOObject = StringIO(_nodeDetails)
        for _model in self.__models:
            _stringIOObject.write(_model.__str__())
            _stringIOObject.write(", ")

        return _stringIOObject.getvalue()

def init_SatelliteBasic(
        _nodeDetails, 
        _timeDetails, 
        _topologyID, 
        _logger) -> INode:
    '''
    @desc
        This method initializes an instance of SatelliteBasic class
    @param[in]  _nodeDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "nodeid": 1,
            "tle_1": "1 50985U 22002B   22290.71715197  .00032099  00000+0  13424-2 0  9994",
            "tle_2": "2 50985  97.4784 357.5505 0011839 353.6613   6.4472 15.23462773 42039",
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
    assert _nodeDetails.tle_1 is not None
    assert _nodeDetails.tle_2 is not None

    assert _timeDetails is not None

    assert _timeDetails.starttime != ''
    _simStartTime = Time().from_str(_timeDetails.starttime)
    
    assert _timeDetails.endtime != ''
    _simEndTime = Time().from_str(_timeDetails.endtime)

    assert _timeDetails.delta > 0
    _timeDelta = _timeDetails.delta

    assert _logger is not None

    _newNode = SatelliteBasic(
            _nodeDetails.nodeid, 
            _topologyID, 
            _nodeDetails.tle_1, 
            _nodeDetails.tle_2, 
            _timeDelta, 
            _simStartTime, 
            _simEndTime, 
            _logger, 
            _nodeDetails.additionalargs)
    return _newNode
