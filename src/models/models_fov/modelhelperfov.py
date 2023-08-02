'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 22 Dec 2022
@desc
    This module implements the field of view (FoV) operation for a node. 
    For example, which ground stations a satellite can see from its current position and vice versa.
'''

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode, ENodeType
from src.nodes.itopology import ITopology
from src.simlogging.ilogger import ILogger
from src.utils import Time, Location
from src.sim.imanager import EManagerReqType
from src.simlogging.ilogger import ILogger, ELogType
import numpy as np

class ModelHelperFoV(IModel):
    """
    This class implements the field of view (FoV) functionality for a node.
    For example, which ground stations a satellite can see from its current position and vice versa.
    Note that it can be ONLY used for up or down view. For example, it does not give a satellite the view of other satellites. Same holds for the ground nodes.
    The execute method is empty. So it is recommended to used this model like a helper model for other models.
    """
    __modeltag = EModelTag.VIEWOFNODE
    __ownernode: INode
    __supportednodeclasses = []
    
    # Although this model doesn't depend on any other model as it just takes the position of a node for it's calculation, 
    # it is recommend for the satellite to incorporate ModelOrbitOneFullUpdate and execute the same in the first place.
    # ModelOrbitOneFullUpdate model updates all the positions of the satellite for the satellite simulation time. 
    # So it becomes better for the ModelHelperFoV in calculating the elevation angle at any point. 
    # However, it would not break, even if the ModelOrbitOneFullUpdate is not used.
    __dependencies = []     
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

    def Execute(self):
        """
        @desc
            This method typically executes the tasks that needed to be performed by the model.
            As this model is designed like a helper model, there is nothing to execute.
        """
        pass
        
    def __get_View(
            self,
            **_kwargs) -> list:
        """
        @desc
            This method generates the view for the parent node at the given time and location.
            If the _time and location are not provided it picks the latest location of the node based on the current node time. 
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _isDownView
                True: A view of a node in space
                False: A view of a node on ground
            @key:  _targetNodeTypes
                List of the node types that we want to cover in the view.
                Ensure that the consistency has been kept with the view selection.
                For example, DO NOT select the nodes in space if it's a down view
            @key:  _myTime
                Time of the FoV search
            @key:  "_myLocation"
                Location of the node
        @return
            A list containing the visible node IDs of the target node types 
        """
        _ret = None

        # retrieve the arguments from the keyworded arguments

        _isDownView = _kwargs["_isDownView"]
        _targetNodeTypes = _kwargs["_targetNodeTypes"]
        _myTime = _kwargs["_myTime"]
        _myLocation = _kwargs["_myLocation"]

        # Check whether time is provided
        if _myTime is None:
            # time is not provided, take the current time of the node
            _myTime  = self.__ownernode.timestamp
            _myLocation = self.__ownernode.get_Position(_myTime)
        
        # Get the node topology ID and find the corresponding topology (node list) from the manager
        _topologyID = self.__ownernode.topologyID
        _topologies = self.__ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        _myTopology:ITopology = None
        for _topology in _topologies:
            if _topology.id == _topologyID:
                _myTopology = _topology
                break
        
        assert _myTopology is not None, "[Simulation Error]: A topology should have been found for an existing node"
        
        # Based on the up or down view, the calculation differs. 
        # So let's check the view first

        # Load all the nodes having the target node types from the topology if the node is in space
        _targetNodeTypes = set(_targetNodeTypes)
        
        _myNodes = _myTopology.nodes # All the nodes in my topology
        _nodeIDToElevation = np.zeros((len(_myNodes), 2)) # A 2D array for holding nodeID of view target nodes and corresponding elevation angle (initially zero)
        _targetNodeLocations = np.zeros((len(_myNodes), 3)) # A array holding the position vectors of the target nodes
        
        _index = 0
        for _node in _myNodes:
            if _node.nodeType in _targetNodeTypes:
                _targetNodePosition = _node.get_Position(_myTime)
                if _targetNodePosition is not None:
                    _nodeIDToElevation[_index] = (_node.nodeID, 0.0)
                    _targetNodeLocations[_index] = _targetNodePosition.to_tuple()
                    _index = _index + 1
        
        _totalNumOfNodes = _index

        if _totalNumOfNodes > 0:
            # truncate the array as we took it as the size of all nodes in the topology
            _nodeIDToElevation = _nodeIDToElevation[:_totalNumOfNodes, ]
            _targetNodeLocations = _targetNodeLocations[:_totalNumOfNodes, ]
           
            if _isDownView:
                # It's a down view. So all the target nodes should be on the ground
                # calculate the Norm of ground node positions
                _targetNodeLocationNorms = np.linalg.norm(_targetNodeLocations, axis=1)

                # calculate the unit vector for ground node locations
                _groundNodeLocationUnitVec = np.divide(_targetNodeLocations.T, _targetNodeLocationNorms).T
                
                # Calculate the delta position vectors for the satellite location and ground node locations
                _deltaSatToGroundNodeLocations = _myLocation.to_tuple() - _targetNodeLocations # the delta vector between the positions of satellite and each ground node
                
                # calculate the Norm of delta position vectors
                _deltaSatToGroundNodeLocationNorms = np.linalg.norm(_deltaSatToGroundNodeLocations, axis=1)

                # calculate the unit vectors for delta position vectors
                _deltaSatToGroundNodeLocationUnitVec = np.divide(
                                                            _deltaSatToGroundNodeLocations.T, 
                                                            _deltaSatToGroundNodeLocationNorms).T
                # calculate the elevation angles
                _elevations = np.arcsin( np.einsum(
                                            'ij, ij->i', 
                                            _deltaSatToGroundNodeLocationUnitVec, 
                                            _groundNodeLocationUnitVec)) * 180/np.pi
                
                # copy the elevation angles against the node IDs
                _nodeIDToElevation[:_totalNumOfNodes, 1:2] =  _elevations.reshape(_totalNumOfNodes, 1)
                
                self.__logger.write_Log(f"Node ID vs the elevation angle: \n {_nodeIDToElevation}", ELogType.LOGDEBUG, _myTime)

            else:
                # It's a down view. So all the target nodes should be in the space. So the viewer node must be on the ground
                _groundNodeLoaction = np.asarray(_myLocation.to_tuple())

                # calculate the Norm of ground node positions
                _groundNodeLocationNorm = np.linalg.norm(_groundNodeLoaction)

                # calculate the unit vector for ground node locations
                _groundNodeLocationUnitVec = np.divide(_groundNodeLoaction.T, _groundNodeLocationNorm).T

                # Calculate the delta position vectors for the satellite locations and ground node location
                _deltaSatToGroundNodeLocations = _targetNodeLocations - _groundNodeLoaction # the delta vector between the positions of satellites and each ground node

                # calculate the Norm of delta position vectors
                _deltaSatToGroundNodeLocationNorms = np.linalg.norm(_deltaSatToGroundNodeLocations, axis=1)

                # calculate the unit vectors for delta position vectors
                _deltaSatToGroundNodeLocationUnitVec = np.divide(
                                                            _deltaSatToGroundNodeLocations.T, 
                                                            _deltaSatToGroundNodeLocationNorms).T
                # calculate the elevation angles
                _elevations = np.arcsin(np.dot(
                                            _deltaSatToGroundNodeLocationUnitVec, 
                                            _groundNodeLocationUnitVec)) * 180/np.pi
                
                # copy the elevation angles against the node IDs
                _nodeIDToElevation[:_totalNumOfNodes, 1:2] =  _elevations.reshape(_totalNumOfNodes, 1)
                self.__logger.write_Log(f"Node ID vs the elevation angle: \n {_nodeIDToElevation}", ELogType.LOGDEBUG, _myTime)                
        else:
            self.__logger.write_Log("No target node types in the topology", ELogType.LOGWARN, _myTime)
            return _ret
        
        #now we have the node ID vs elevation angle array. We need to find the nodes which are greater than our minimum elevation angle
        _ret = _nodeIDToElevation[_nodeIDToElevation[:, 1] >= self.__minElevation, 0].tolist()
        return _ret
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "get_View": __get_View
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
            print(f"[ModelHelperFov Warning]: An unhandled API request has been received by {self.__ownernode.nodeID}", e)
        
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
            Minimum elevation angle in degrees
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        self.__minElevation = _minElevation

def init_ModelHelperFoV(
                    _ownernodeins: INode, 
                    _loggerins: ILogger, 
                    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelHelperFoV class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key min_elevation
            Minimum elevation angle in degrees
    @return
        Instance of the model class
    '''
    # check the arguments
    assert _ownernodeins is not None
    assert _loggerins is not None

    if "min_elevation" not in _modelArgs:
        raise Exception("ModelHelperFoV: min_elevation is not found in the model arguments")
    return ModelHelperFoV(_ownernodeins, _loggerins, _modelArgs.min_elevation)