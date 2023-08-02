"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 27 Sep 2022

This module includes the interface implementation of topology. 
"""

from abc import ABC, abstractmethod
from src.nodes.inode import INode, ENodeType

class ITopology(ABC):
    """
    This is an interface for the node topology. Learn more about topology from README.md
    """

    @property
    @abstractmethod
    def id(self) -> int:
        '''
        @type
            Integer
        @desc
            ID of the topology. Each topology should have an unique ID
        '''
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        '''
        @type
            String
        @desc
            Name of the topology
        '''
        pass

    @abstractmethod
    def add_Node(
            self, 
            _node: INode):
        '''
        @desc
            Adds the node given in the argument to the list
        @param[in]  _node
            Node to be added to the list
        '''
        pass
    
    @abstractmethod
    def get_Node(
            self, 
            _nodeId: int) -> INode:
        '''
        @desc
            Get a node from this topology with node id.
        @param[in]  _nodeId
            ID of the node that is being looked for
        @return
            INode instance of the node
        '''
        pass
    
    @abstractmethod 
    def get_NodesOfAType(
            self, 
            _nodeType: ENodeType) -> 'list[INode]':
        '''
        @desc
            Get the list of all nodes of a type provided in the argument
        @param[in]  _nodeType
            Type of the node
        @return
            List of the nodes
        '''
        pass
    
    @property
    @abstractmethod
    def nodes(self) -> 'list[INode]':
        '''
        @type
            List of INode
        @desc
            All the nodes of this topology instance
        '''
        pass
