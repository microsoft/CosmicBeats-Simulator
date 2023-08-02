"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 27 Sep 2022

This module includes the interface definition of the node. 
"""

from abc import ABC, abstractmethod
from enum import Enum

from src.models.imodel import EModelTag, IModel
from src.utils import Location
from src.utils import Time

class ENodeType(Enum):
    """
    An enum listing the types of the type.
    Each node implementation should have a type.
    """
    SAT = 0
    GS = 1
    IOTDEVICE = 2

class INode(ABC):
    """
    This is an interface implementation for the nodes. 
    Each node implementation such as satellite, ground station, terminal, among others should inherit this interface
    """

    @property
    @abstractmethod
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the node class. For example, NodeSatellite 
            Note that the name should exactly match to your class name. 
        """
        pass

    @property
    @abstractmethod
    def nodeType(self) -> ENodeType:
        """
        @type
            ENodeType
        @desc
            The node type for the implemented node class
        """
        pass

    @property
    @abstractmethod
    def nodeID(self) -> int:
        """
        @type 
            int
        @desc
            The ID of a node in the topology. It basically distinguishes a node from another node.  
        """
        pass

    @property
    @abstractmethod
    def topologyID(self) -> int:
        """
        @type 
            int
        @desc
            The ID of the topology that the node instance is part of
        """
        pass

    @abstractmethod
    def get_Position(
            self,
            _time: Time) -> Location:
        """
        @desc
            This method returns the position of the node at the time provided in the argument. 
            The implementing class can keep location as a private variable and return it through this method. 
        @param[in]  _time
            The time at which the location is being looked for
        @return
            Location of the node, if available
            otherwise, none
        """
        pass

    @property
    @abstractmethod
    def managerInstance(self):
        """
        @type
            Manager class
        @desc
            Manager instance of the simulator that is holding this node instance  
        """
        pass

    @property
    @abstractmethod
    def timestamp(self) -> Time:
        """
        @type
            Time
        @desc
            Current timestamp of the node instance 
        """
        pass

    @property
    @abstractmethod
    def simStartTime(self) -> Time:
        """
        @type
            Time
        @desc
            Start timestamp of the node instance for simulation 
        """
        pass

    @property
    @abstractmethod
    def simEndTime(self) -> Time:
        """
        @type
            Time
        @desc
            End timestamp of the node instance for simulation
        """
        pass

    @property
    @abstractmethod
    def deltaTime(self) -> float:
        """
        @type
            Float
        @desc
            time granularity for the simulation of this node (in seconds).
            Time gap between two simulation epochs
        """
        pass

    @abstractmethod
    def Execute(self) -> bool:
        """
        @desc
            This method executes the models of the node instance one by one. 
            This is one time execution of the models.
        @return
            True:   If the execution is successful
            False:  Otherwise
        """
        pass

    @abstractmethod
    def ExecuteCntd(self):
        """
        @desc
        This method executes the models of the node instance one by one continuously until
        it reaches simulation end time.
        """
        pass

    @abstractmethod
    def add_Models(
            self, 
            _modelsToAdd: 'list[IModel]'):
        """
        @desc
            This method adds a model to the node
        @param[in]  _modelsToAdd    
           The list of models to be added
        """
        pass
    
    @abstractmethod
    def has_ModelWithTag(
            self, 
            _modelTag: EModelTag) -> IModel:
        """
        @desc
            This method checks whether this node instance has a model implemented having the provided modeltag.
            If so, it returns the model.
        @param[in]  _modelTag    
           Tag of the model that is being looked for
        @return
            Instance of the model if it was found.
            Otherwise, None 
        """
        pass
    
    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def add_ManagerInstance(_managerIns):
        '''
        @desc
            Adds manager instance to this node instance
        @param[in]  _managerIns
            Manager instance as IManager
        '''
        pass