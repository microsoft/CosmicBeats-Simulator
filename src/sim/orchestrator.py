'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 17 Oct 2022
@desc
    This is the implementation of orchestrator class.
    As the name suggests, this class orchestrates the simulation environment from the config file
'''

import json
import os
from argparse import Namespace
from typing import List

from src.utils import Time
from src.nodes.inode import INode
from src.nodes.itopology import ITopology
from src.nodes.topology import Topology
from src.simlogging.ilogger import ILogger
from src.models.imodel import IModel
from src.sim.nodeinits import nodeInitDictionary
from src.sim.loggerinits import loggerInitDictionary, loggerTypeDictionary
from src.sim.modelinits import modelInitDictionary

class Orchestrator():
    '''
    This class orchestrates the simulation environment. 
    The main jobs are, reading the config file, creating the nodes accordingly having asked models, resolving the dependencies of models, allocating resources (e.g., thread, VM) to the nodes.
    '''
    __configFilePath: str
    __configdata = None
    __topologies: 'list[ITopology]'
    __numOfSimSteps: int
    __dependencyResolvedSetsOfModels = []

    def create_SimEnv(self):
        '''
        @desc
            This function takes care of the main job of the orchestrator class, i.e., preparing the nodes with proper models
        '''
        # read the config file first in the JSON format
        if os.path.isfile(self.__configFilePath):
            try:
                with open(self.__configFilePath, 'r') as __configFile:
                    self.__configdata = json.load(__configFile, object_hook=lambda d: Namespace(**d))
            except:
                raise Exception(f"[Simulator Exception] Couldn't read the config file at: {self.__configFilePath}")
        else:
            raise Exception(f"[Simulator Exception] Couldn't find the config file at: {self.__configFilePath}")

        # Read the simulation time related parameters
        assert self.__configdata.simtime is not None
    
        assert self.__configdata.simtime.starttime != ''
        self.__simStartTime = Time().from_str(self.__configdata.simtime.starttime)

        assert self.__configdata.simtime.endtime != ''
        self.__simEndTime = Time().from_str(self.__configdata.simtime.endtime)

        assert self.__configdata.simtime.delta > 0
        self.__timeDelta = self.__configdata.simtime.delta

        self.__numOfSimSteps = self.__simEndTime.difference_in_seconds(self.__simStartTime)/self.__timeDelta
        assert self.__numOfSimSteps > 0

        #  Create topologies and the nodes for each topology
        for _topologyConfig in self.__configdata.topologies:
            # get the topology node and ID
            assert _topologyConfig.name != ''
            assert _topologyConfig.id is not None

            _topologyIns = Topology(_topologyConfig.name, _topologyConfig.id)
            self.__topologies.append(_topologyIns)

            # Let's config the node as the user wants to do
            for _nodeConfig in _topologyConfig.nodes:
                try:
                    # initialize logger by looking the at the logger init dictionary. 
                    # We just look for the log handler that user wants to use and the corresponding initialization function from the dictionary
                    _loggerName = ("" + str(_topologyConfig.name) + "_" 
                                    + str(_topologyConfig.id) + "_" 
                                    + _nodeConfig.type + "_" 
                                    + str(_nodeConfig.nodeid))
                    _logger = loggerInitDictionary[self.__configdata.simlogsetup.loghandler](
                                                                                            loggerTypeDictionary[_nodeConfig.loglevel], 
                                                                                            _loggerName, 
                                                                                            self.__configdata.simlogsetup)
                    assert _logger is not None
                    
                    # initialize the node by looking at the node init dictionary. 
                    # User mentions the iname (implementation class name of a node) of the node and we try to find the corresponding initialization function in the dictionary 
                    _newNode = nodeInitDictionary[_nodeConfig.iname](
                                                                    _nodeConfig, 
                                                                    self.__configdata.simtime, 
                                                                    _topologyConfig.id, 
                                                                    _logger)
                    assert _newNode is not None
                   
                    # Node is ready. Now, it's time to add models to the node
                    _modelConfig = _nodeConfig.models
                    self._add_Models(_newNode, _logger, _modelConfig)
                    
                    # Models have been added to the node. Now, we can add the  node to the topology
                    _topologyIns.add_Node(_newNode)
                except:
                    raise Exception(f"[Simulator Exception] Error in initializing node of topology: {str(_topologyConfig.id)}, node: {str(_nodeConfig.nodeid)}")
    
    def _add_Models(
            self, 
            _nodeInstance: INode, 
            _loggerins: ILogger, 
            _modelDetails):
        '''
        @desc
            This method reads the configuration, creates, and adds the models for a node after checking the compatibility
        @param[in]  _nodeInstance
            Instance of the node for which this method would create models
        @param[in]  _loggerins
            Logger instance that's needed to be passed to the model instance
        @param[in]  _modelDetails
            Details of the model in the JSON array format
        '''
        _tempModelList: List[IModel] = []
        _modelNameSet = set()
        
        for _thisModelDetails in _modelDetails:
            #first, try to create the model instance by looking at the model init dictionary
            try:
                _modelIns:IModel = modelInitDictionary[_thisModelDetails.iname](
                                                                        _nodeInstance, 
                                                                        _loggerins, 
                                                                        _thisModelDetails)
            except:
                raise Exception(f"[Simulator Exception] Error in initializing model: {_thisModelDetails.iname}")
            
            # check whether this node is supported by the model
            _isThisNodeSupported = False
            # if the supported node class list is empty, the model supports any node. End of story.
            if len(_modelIns.supportedNodeClasses) == 0:
                _isThisNodeSupported = True
            else:
                # Supported node list is not empty. So, check whether the node is supported or not
                # Now check whether the name of _nodeInstance is in the supported node list or not
                for _supportedNodeClass in _modelIns.supportedNodeClasses:
                    if _nodeInstance.iName == _supportedNodeClass:
                        _isThisNodeSupported = True
                        break
            
            if _isThisNodeSupported:
                # The node is supported by the model.
                # But, is it a duplicate model? User might have added the same model twice in the config file? 
                # Let's, check duplicate model
                if (_modelNameSet != set() and 
                    _modelIns.iName in _modelNameSet):
                    # Ah! It's a duplicate model. Raise the exception and let the user know.
                    print(f"[Simulator Warning] Model {_modelIns.iName} has been added to node {str(_nodeInstance.nodeID)} multiple times.")
                else:
                    # It's not a duplicate model
                    # So we can consider it as a "good to add" model so far in this node 
                    _modelNameSet.add(_modelIns.iName)
                    _tempModelList.append(_modelIns)
            else:
                # Ah! This node is not supported by the model. Let the user know.
                raise Exception("[Simulator Exception] Model {_modelIns.iName} does not support node {_nodeInstance.iName}")

        # We are here without any exception means the node is supported by the all models that the user included in the config file
        # Now, resolve the model inter-dependency. 
        _dependencyResolved = False

        # First, check whether we already resolved dependency for this group of models earlier
        for _dependencyResolvedSet in self.__dependencyResolvedSetsOfModels:
            if _modelNameSet == _dependencyResolvedSet:
                # We have resolved dependency for this model group earlier!!! Phew! No further computation then.
                _dependencyResolved = True
                break

        if not _dependencyResolved:
            # Nope, we didn't resolve dependency for this group of models earlier.
            # Let's try to resolve the dependency then.

            # Turning on the dependency resolved flag. If we can resolve the dependency, we will turn it off.
            _dependencyResolved = True

            #check the dependency for each model that user listed
            for _modelToBeChecked in _tempModelList:
                if len(_modelToBeChecked.dependencyModelClasses) == 0:
                    # This model doesn't have any dependency. Move to the next one.
                    continue
                else:
                    # This model has dependency. Let's check whether we can resolve it or not.
                    for _dependencySublist in _modelToBeChecked.dependencyModelClasses:
                        # We have a sublist of dependency models. Let's check whether we can resolve this dependency or not.
                        _isThisDependencyResolved = False
                        for _dependencyModelClassName in _dependencySublist:
                            # Let's check whether this dependency is met by any of the models that we have listed in this node
                            for _aModelFromTheList in _tempModelList:
                                # To meet the requirement, the specific model type and implementation should match along with minimum patch/feature version 
                                if (_aModelFromTheList.iName == _dependencyModelClassName):
                                    # We are resolved for this dependency. Move to the next one.
                                    _isThisDependencyResolved = True
                                    break
                            # if the dependency is resolved for this sublist, we don't need to check further, so break the loop
                            if _isThisDependencyResolved:
                                break
                            
                        # if the dependency is not resolved, we don't need to check further, so break the loop
                        if not _isThisDependencyResolved:
                            # Models that the user included in this node are not enough to resolve this dependency.
                            _dependencyResolved = False
                            break
                
                if not _dependencyResolved:
                    # Dependency not resolved. Let the user know with an exception
                    raise Exception(f"[Simulator Exception] Model {_modelToBeChecked.iName } has dependency mismatch inside node ID: {str(_nodeInstance.nodeID)} Model wanted: {str(_modelNameSet)}")
                    
            
            # update the set of uVersions in the dependency resolved sets of models for easing future computation 
            if len(_modelNameSet) > 1:
                self.__dependencyResolvedSetsOfModels.append(_modelNameSet)
        
        # finally, add the models to the node
        if len(_tempModelList) > 0:
            _nodeInstance.add_Models(_tempModelList)
        

    def __init__(
            self, 
            _configfilepath) -> None:
        '''
        @desc
            Constructor of the orchestrator class
        @param[in]  _configfilepath
            Path to the configuration JSON file
        '''
        self.__configFilePath = _configfilepath
        self.__topologies = []

    def get_SimEnv(self):
        '''
        @desc
            Returns the simulation environment 
        @return
            Simulation environment including the following parameters in a list
            [
                topologies : List[ITopology]
                numOfSimSteps: int
            ]
        '''
        _retSimEnv = []

        _retSimEnv.append(self.__topologies)

        _retSimEnv.append(self.__numOfSimSteps)

        _retSimEnv.append(self.__timeDelta)

        return _retSimEnv



