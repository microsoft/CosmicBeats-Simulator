'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 17 May 2023
@desc
    This is a ISL communication model which manages the communication between two satellites specified in the config file. 
    This model is an implementation of the IModel interface. It controls a ISL Radio device and schedules when to transmit and receive frames.
    This model only has one queue - rx. The tx queue will be managed by another model, e.g., a network model.
    To send a frame, use the send_Data() API. 
'''

from src.sim.imanager import EManagerReqType
from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ILogger
from src.models.imodel import EModelTag

from src.models.models_radio.modelgenericradio import ModelGenericRadio

from src.models.network.isl.islradiodevice import ISLRadioDevice
from src.models.network.isl.islchannel import ISLChannel

class ModelISL(ModelGenericRadio):
    '''
    This model class implements the radio functionalities of node having LoRa Radios. 
    This radio class enables communication, i.e., exchange of LoRa frames between nodes. 
    '''

    _modeltag = EModelTag.ISL
    @property
    def modelTag(self) -> EModelTag:
        """
        @type
            EModelTag
        @desc
            The model tag for the implemented model
        """
        return self._modeltag
    
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

    def _radioDeviceClass(self):
        return ISLRadioDevice
    
    def _update_Channel(self):
        """
        @desc
            This method updates the channels of the radio device.
            This should only be called when the node is transmitting
        """
        _topologyID = self._ownernode.topologyID
        _topologies = self._ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        _myTopology: 'ITopology' = None
        for _topology in _topologies:
            if _topology.id == _topologyID:
                _myTopology = _topology
                break
        
        assert _myTopology is not None
        
        self.__connectedNodes = [_myTopology.get_Node(_nodeId) for _nodeId in self.__connectedNodeIDs]
        
        # first update the radio device's channels        
        _newChannels = [ISLChannel() for _ in self.__connectedNodes]
        
        __nodes = self.__connectedNodes
        #now let's get the radio devices from the nodes
        __models = [_node.has_ModelWithName("ModelISL") for _node in __nodes]
        _devices = [_model.call_APIs("get_RadioDevice") for _model in __models]
        
        assert len(_devices) == len(__nodes)
        assert len(_newChannels) == len(_devices)
        
        for _channel, _device in zip(_newChannels, _devices):
            _channel.add_Device(_device)

        self._radioDevice.set_Channels(_newChannels)
    
    def __init__(
        self, 
        _ownernodeins: INode, 
        _loggerins: ILogger,
        _radioID: int, 
        _radioPhySetup,
        _queueSize: int = 0,
        _selfCtrl: bool = True,
        _connectedNodeIDs: 'list' = []) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _radioID
            ID of the radio device in a node
        @param[in]  _radioPhySetup
            Dictionary that contains the radio device physical setup
        @param[in]  _queueSize
            Size of the queue. By default, it is infinite
        @param[in]  _selfCtrl
            True: The transmission of the frames would be done automatically in the execution method
            False: The transmission of the frames or handling received frame would be externally controlled 
        @param[in]  _connectedNodeIDs
            List of node IDs that are connected to this node
        '''
        
        super().__init__(_ownernodeins, _loggerins, _radioID, _radioPhySetup, _queueSize, _selfCtrl)
        self.__connectedNodeIDs = _connectedNodeIDs
    
def init_ModelISL(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelLoraRadio class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key radioID
            The ID to set the radio device to. If not provided, the node ID will be used
        @key queue_size
            The size of the queue. If not provided, the queue size will be infinite
        @key self_ctrl
            If true, the model will automatically send the data in the queue. 
            Default is true. If false, use send_Data API to send the data
        @key radio_physetup
            The radio phy setup to pass to the radio device. If not provided, None will be used
        @key connected_nodeIDs
            A list of node IDs that are connected to this node via ISL
    @return
        Instance of the model class
    '''
    assert _ownernodeins is not None
    assert _loggerins is not None
    assert _modelArgs is not None

    if 'radioID' in _modelArgs:
        _radioId = _modelArgs.radioId
    else:
        _radioId = _ownernodeins.nodeID
    
    _queueSize = -1
    if 'queue_size' in _modelArgs:
        _queueSize = _modelArgs.queue_size
    
    _selfCtrl = False
    if 'self_ctrl' in _modelArgs:
        _selfCtrl = _modelArgs.self_ctrl
    
    _connectedNodeIDs = _modelArgs.connected_nodeIDs
    
    _radioPhySetup = _modelArgs.radio_physetup

    return ModelISL(_ownernodeins, 
                          _loggerins, 
                          _radioId,
                          _radioPhySetup,
                          _queueSize,
                          _selfCtrl,
                          _connectedNodeIDs)