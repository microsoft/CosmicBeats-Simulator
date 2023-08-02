'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 22 Dec 2022
@desc
    This module implements the field of view (FoV) operation for a node. 
    It offers improved performance compared to the normal "modelhelperfov" model, especially when the timestep is small (refer to the fov test case for performance comparisons). 
    The FoV operation is based on finding the time of intersection with a satellite, and it does not involve calculating the elevation angles. 
    One unique aspect of this model is the presence of a static variable that holds all the pass times. 
    This design choice aims to avoid redundant computations. 
    Once the pass times for a satellite are calculated, they are reused in the ground station to prevent unnecessary recalculation.
'''
import threading

import numpy as np

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.nodes.itopology import ITopology
from src.simlogging.ilogger import ILogger
from src.sim.imanager import EManagerReqType
from src.simlogging.ilogger import ILogger, ELogType

class ModelFovTimeBased(IModel):
   
    __modeltag = EModelTag.VIEWOFNODE
    __ownernode: INode
    __supportednodeclasses = []  
    __dependencies = []
    __logger: ILogger
    
    __nodeToTimes = {} #Static variable to hold the pass times for each node. Node id is the key and the value is a numpy array of (start, end, nodeID, ENodeType) tuples 
    __nodeToNode = {} #static variable to see if this pair of nodes has been calculated. Node id is the key and the value is a list of node ids
    __preloaded = False #static variable to see if the pass times have been preloaded
    __nodeToTimesLock = threading.Lock() #Lock for the static variable
    
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

    def __get_View(
            self,
            **_kwargs) -> list:
        """
        @desc
            This method generates the view for the parent node at the given time and location.
            If the _time and location are not provided it picks the latest location of the node based on the current node time. 
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _targetNodeTypes
                List of the node types that we are interested in 
            @key:  _myTime
                Time of the FoV search. Optional. If not provided, it uses the current node time
        @return
            A list of node IDs that can be seen of the target node types
        """        
        if '_targetNodeTypes' not in _kwargs:
            raise Exception("Missing _targetNodeTypes keyworded argument")
        if '_myTime' not in _kwargs or _kwargs['_myTime'] is None:
            _myTime = self.__ownernode.timestamp
        else:
            _myTime = _kwargs['_myTime']  
        
        _targetNodeTypes = _kwargs['_targetNodeTypes']
        
        #If the pass times have not been preloaded, don't bother searching
        if not ModelFovTimeBased.__preloaded:
            self.__find_Passes(_targetNodeTypes = _targetNodeTypes)

        # _fp is an np array of nx4 where each column is start (datetime), end (datetime), nodeID (int), ENodeType (int - value of ENodeType)
        _fp = ModelFovTimeBased.__nodeToTimes.get(self.__ownernode.nodeID) 
        if _fp is None or len(_fp) == 0:
            return []
                
        #Find the indices of the passes that are in the current time
        _datetime = _myTime.to_datetime()
        _targetNodeInt = [i.value for i in _targetNodeTypes]
        
        _fpDesiredInds = np.argwhere((_fp[:,0] <= _datetime) & (_fp[:,1] >= _datetime) & (np.isin(_fp[:,3], _targetNodeInt)))
        _fpDesiredInds = _fpDesiredInds.flatten()
        _ret = [i[2] for i in _fp[_fpDesiredInds]]
        
        #if len(_fpDesiredInds) > 0 and _myTime not in _kwargs:
        #    #Let's update the list. We don't need to keep the old ones 
        #    ModelFovTimeBased.__nodeToTimes[self.__ownernode.nodeID] = _fp[_fpDesiredInds[0]:] 
        
        return _ret
    
    def __log_Pass(self, _otherNode:INode, _startTime:'Time', _endTime:'Time'):
        """
        @desc
            This method logs the pass of the target node in the current node. 
        @param[in]  _otherNode
            The other node
        @param[in]  _startTime
            The start time of the pass
        @param[in]  _endTime
            The end time of the pass
        """
        _otherNodeType = str(_otherNode.nodeType.value)
        _startTimeUnix = _startTime.to_unix()
        _endTimeUnix = _endTime.to_unix()
        
        _loggerStr = "".join(["Pass. nodeID: ", str(_otherNode.nodeID), ". nodeType: ", _otherNodeType, ". startTimeUnix: ", str(_startTimeUnix), ". endTimeUnix: ", str(_endTimeUnix)])
        self.__logger.write_Log(_loggerStr, ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
            
    def __find_Passes(self, **_kwargs):
        """
        @desc
            This method finds the passes of the target nodes in the whole simulation time.
            This will update the __nodeToTimes dictionary with the passes of the target nodes. 
            This won't return anything.
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _targetTypes
                List of the node types that we are interested in
        """              
        _targetTypes = _kwargs['_targetNodeTypes']
        
        # Get the node topology ID and find the corresponding topology (node list) from the manager
        _topologyID = self.__ownernode.topologyID
        _topologies = self.__ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        _myTopology:ITopology = None
        for _topology in _topologies:
            if _topology.id == _topologyID:
                _myTopology = _topology
                break
        
        assert _myTopology is not None, "[Simulation Error]: A topology should have been found for an existing node"
        
        #let's find all the target nodes
        _targetNodes = [_myTopology.get_NodesOfAType(_targetType) for _targetType in _targetTypes]
        _targetNodes = [item for sublist in _targetNodes for item in sublist]
        
        #This should be relatively thread safe. The worst that can happen is that we will find the same pass twice
        #That has less of an impact than locking the whole thing
        _currentOnes = ModelFovTimeBased.__nodeToNode[self.__ownernode.nodeID]
        _nodesToCheck = [_node for _node in _targetNodes if _node.nodeID not in _currentOnes]
        
        #let's find the passes
        for _node in _nodesToCheck:
                #Same as above
                ModelFovTimeBased.__nodeToNode[self.__ownernode.nodeID].append(_node.nodeID)
                ModelFovTimeBased.__nodeToNode[_node.nodeID].append(self.__ownernode.nodeID)
                
                #Let's find out what kind of node this is:
                if _orbitModel := self.__ownernode.has_ModelWithTag(EModelTag.ORBITAL):
                    _satelliteNode = self.__ownernode
                    _groundStationNode = _node
                else:
                    _satelliteNode = _node
                    _orbitModel = _node.has_ModelWithTag(EModelTag.ORBITAL)
                    _groundStationNode = self.__ownernode
                    
                _minElevation = max(self.__minElevation, _otherModel.__minElevation if (_otherModel := _node.has_ModelWithName(self.iName)) else 0)
                _startTime = max(self.__ownernode.simStartTime, self.__ownernode.timestamp)
                _passes = _orbitModel.call_APIs("get_Passes", _gs = _groundStationNode, _start = _startTime, _end = self.__ownernode.simEndTime, _minElevation=_minElevation)

                for _pass in _passes:
                    self.__log_Pass(_node, _pass[0], _pass[1])

                if _passes is None:
                    raise Exception(f"[FovTimeBased Error]: The passes could not be found for the nodes {_node.nodeID} and {self.__ownernode.nodeID}. If there is no api handler for the get_Passes API. ")
                
                if len(_passes) > 0:
                    #now let's add the passes to the dictionary
                    _satPasses = [(ps[0].to_datetime(), ps[1].to_datetime(), _groundStationNode.nodeID, _groundStationNode.nodeType.value) for ps in _passes]
                    _gsPasses = [(ps[0].to_datetime(), ps[1].to_datetime(), _satelliteNode.nodeID, _satelliteNode.nodeType.value) for ps in _passes]
                    
                    #Let's acquire the lock
                    #We need a lock here because the static variable is shared among all the instances of this class
                    ModelFovTimeBased.__nodeToTimesLock.acquire()
                    
                    #let's get the original values. These are numpy arrays
                    _origSat = ModelFovTimeBased.__nodeToTimes[_satelliteNode.nodeID]
                    _origGs = ModelFovTimeBased.__nodeToTimes[_groundStationNode.nodeID]
                    
                    #Add the new passes
                    if _origSat is None:
                        _newSat = np.array(_satPasses)    
                    else:                    
                        _newSat = np.append(_origSat, _satPasses, axis=0)
                    assert _newSat.shape[1] == 4, "[FovTimeBased Error]: The shape of the newSat array is not correct"
                    
                    if _origGs is None:
                        _newGs = np.array(_gsPasses)
                    else:
                        _newGs = np.append(_origGs, _gsPasses, axis=0)
                    assert _newGs.shape[1] == 4, "[FovTimeBased Error]: The shape of the newGs array is not correct"
                    
                    #Let's sort the rows by the start time
                    _newSat = _newSat[_newSat[:,0].argsort()]
                    _newGs = _newGs[_newGs[:,0].argsort()]
                    
                    #Now let's update the dictionary
                    ModelFovTimeBased.__nodeToTimes[_satelliteNode.nodeID] = _newSat
                    ModelFovTimeBased.__nodeToTimes[_groundStationNode.nodeID] = _newGs
                    
                    ModelFovTimeBased.__nodeToTimesLock.release()                
                
    def __get_GlobalDictionary(self, **_kwargs):
        """
        @desc
            This method returns the global dictionary of the model. 
            Technically, this is not an API of an individual node's model but global. But it's here
        @return
            A dictionary where the key is the node ID and the value is a list of the passes of the node. See __find_Passes for the format of the pass
        """
        return ModelFovTimeBased.__nodeToTimes
    
    def __set_GlobalDictionary(self, **_kwargs):
        """
        @desc
            This method sets the global dictionary of the model. 
            Technically, this is not an API of an individual node's model but global. But it's here
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _globalDictionary
                A dictionary where the key is the node ID and the value is a list of the passes of the node. See __find_Passes for the format of the pass
        """
        ModelFovTimeBased.__nodeToTimes = _kwargs['_globalDictionary']
        #If we are setting the global dictionary, this means that all the passes are already found. 
        ModelFovTimeBased.__preloaded = True
        
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "get_View": __get_View,
        "find_Passes": __find_Passes,
        "log_Pass": __log_Pass,
        "get_GlobalDictionary": __get_GlobalDictionary,
        "set_GlobalDictionary": __set_GlobalDictionary
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
            print(f"[ModelFoVTimeBased]: An unhandled API request has been received by {self.__ownernode.nodeID}: ", e)
        
        return _ret
        
    def __init__(
        self, 
        _ownernodeins: INode, 
        _loggerins: ILogger,
        _minElevation: float) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _minElevation
            Minimum elevation angle of view in degrees
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        self.__minElevation = _minElevation
        
                            
        ModelFovTimeBased.__nodeToTimes[self.__ownernode.nodeID] = None
        ModelFovTimeBased.__nodeToNode[self.__ownernode.nodeID] = []
        
    def Execute(self) -> None:
        pass
                    
def init_ModelFovTimeBased(
                    _ownernodeins: INode, 
                    _loggerins: ILogger, 
                    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelFovTimeBased class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key min_elevation
            Minimum elevation angle of view in degrees
    @return
        Instance of the model class
    '''
    # check the arguments
    assert _ownernodeins is not None
    assert _loggerins is not None
    
    if "min_elevation" not in _modelArgs:
        raise Exception("[ModelFovTimeBased Error]: The model arguments should contain the min_elevation parameter.")
    
    return ModelFovTimeBased(_ownernodeins, _loggerins, _modelArgs.min_elevation)
