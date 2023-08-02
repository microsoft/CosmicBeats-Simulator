'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 12 Oct 2022
@desc
    This module implements the Topology class that inherits the ITopology
'''
from io import StringIO

from src.nodes.inode import ENodeType, INode
from src.nodes.itopology import ITopology

class Topology(ITopology):
    '''
    Topology class that holds the nodes. It inherits the ITopology interface.
    '''
    __nodes: 'list[INode]'
    __id: int
    __name: str

    @property
    def id(self) -> int:
        '''
        @type
            Integer
        @desc
            ID of the topology. Each topology should have an unique ID
        '''
        return self.__id

    @property
    def name(self) -> str:
        '''
        @type
            String
        @desc
            Name of the topology
        '''
        return self.__name
    
    def add_Node(
            self, 
            _node: INode):
        '''
        @desc
            Adds the node given in the argument to the list
        @param[in]  _node
            Node to be added to the list
        '''
        if(_node is not None):
            self.__nodes.append(_node)
            if _node.nodeID not in self.__nodeIDToNodeMap:
                self.__nodeIDToNodeMap[_node.nodeID] = _node
            else:
                raise Exception("Node ID already exists in the topology")
    
    def get_Node(
            self, 
            _nodeId: int) -> INode:
        '''
        @desc
            Get a node from this topology with node id.
        @param[in]  _nodeId
            ID of the node that is being looked for
        @return
            INode instance of the node. None if not found
        '''
        return self.__nodeIDToNodeMap.get(_nodeId, None)
    
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
        _ret: 'list[INode]' = []
        for _node in self.__nodes:
            if(_node.nodeType == _nodeType):
                _ret.append(_node)
        return _ret
    
    @property
    def nodes(self) -> 'list[INode]':
        '''
        @type
            List of INode
        @desc
            All the nodes of this topology instance
        '''
        return self.__nodes
    
    def __init__(
            self, 
            _name: str, 
            _id: int) -> None:
        '''
        @desc
            Constructor of the topology
        @param[in]  _name
            Name of the topology
        @param[in]  _id
            ID of the topology
        '''
        self.__name = _name
        self.__id = _id
        self.__nodes = []
        self.__nodeIDToNodeMap = {}
    
    def __str__(self) -> str:
        '''
        @desc
            Overriding the __str__() method
        '''
        _string = "".join(["Topology ID: ", str(self.__id), ", ",
                "Topology name: ", self.__name, ", ",
                "Number of nodes: ", str(len(self.__nodes)), "\n"])
        
        _stringIOObject = StringIO(_string)
        for _node in self.__nodes:
            _stringIOObject.write(_node.__str__())
        
        return _stringIOObject.getvalue()