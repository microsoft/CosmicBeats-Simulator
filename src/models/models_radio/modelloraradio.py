'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 1 Feb 2023
@desc
    This is a lora communication model which manages the communication between two nodes that support LoRa communication.
    This model is an implementation of the IModel interface. It controls a LoRa Radio device and schedules when to transmit and receive frames.
    This model has two frame queues - reception and transmission which can be accessed externally through the appropriate APIs
'''

from src.sim.imanager import EManagerReqType
from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.network.lora.loraradiodevice import LoraRadioDevice
from src.models.network.lora.lorachannel import LoraChannel
from src.models.imodel import EModelTag

from src.models.models_radio.modelgenericradio import ModelGenericRadio

class ModelLoraRadio(ModelGenericRadio):
    '''
    This model class implements the radio functionalities of node having LoRa Radios. 
    This radio class enables communication, i.e., exchange of LoRa frames between nodes. 
    '''
    __dependencies = [['ModelHelperFoV', 'ModelFovTimeBased']]
    
    _modeltag = EModelTag.BASICLORARADIO
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

    def _radioDeviceClass(self):
        return LoraRadioDevice
    
    def _update_Channel(self):
        """
        @desc
            This method updates the channels of the radio device.
            This should only be called when the node is transmitting
        """
        # first update the radio device's channel
        _newChannel = LoraChannel()
        _newChannel.add_Device(self._radioDevice)

        #Now let's add all the devices to the channel - let's find which devices are in the view
        _visibleNodeIDs = []
        #let's call the FoV model to get the view
        if self._ownernode.nodeType is not ENodeType.SAT:
            _visibleNodeIDs = self._ownernode.has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                                            "get_View", 
                                                                                            _isDownView = False,
                                                                                            _targetNodeTypes = [ENodeType.SAT],
                                                                                            _myTime = None,
                                                                                            _myLocation = None)
        else:
            _visibleNodeIDs = self._ownernode.has_ModelWithTag(EModelTag.VIEWOFNODE).call_APIs(
                                                                                            "get_View", 
                                                                                            _isDownView = True,
                                                                                            _targetNodeTypes = [ENodeType.GS, ENodeType.IOTDEVICE],
                                                                                            _myTime = None,
                                                                                            _myLocation = None)
        self._logger.write_Log("Node {} has {} nodes in its view".format(self._ownernode.nodeID, len(_visibleNodeIDs)), \
            ELogType.LOGINFO, self._ownernode.timestamp, self.iName)
        
        #if there are no visible nodes, then set the channel to empty
        if len(_visibleNodeIDs) == 0:
            self._radioDevice.set_Channels([])
            return
        
        #Now let's get the nodes from the node IDs
        _topologyID = self._ownernode.topologyID
        _topologies = self._ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        _myTopology:'ITopology' = None
        for _topology in _topologies:
            if _topology.id == _topologyID:
                _myTopology = _topology
                break
        
        _nodes = [_myTopology.get_Node(_nodeId) for _nodeId in _visibleNodeIDs]
        
        #now let's get the radio devices from the nodes
        _loraModels = []
        for _node in _nodes:
            for _model in _node.get_Models():
                if _model.modelTag == EModelTag.BASICLORARADIO and _model._get_Frequency() == self._get_Frequency():
                    _loraModels.append(_model)

        self._logger.write_Log("Node {} has {} devices on the same frequency".format(self._ownernode.nodeID, len(_loraModels)), \
            ELogType.LOGINFO, self._ownernode.timestamp, self.iName)
        
        #None of the visible nodes may be on the same frequency 
        if len(_loraModels) == 0:
            self._radioDevice.set_Channels([])
            return
        
        _devices = [_model.call_APIs("get_RadioDevice") for _model in _loraModels] 
        
        #Now let's add all the devices to the channel        
        for _device in _devices:
            _newChannel.add_Device(_device)
        _newChannel.add_Device(self._radioDevice)
        
        self._radioDevice.set_Channels([_newChannel])

    ##REST IS SAME AS BEFORE

def init_ModelLoraRadio(
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
    
    _selfCtrl = True
    if 'self_ctrl' in _modelArgs:
        _selfCtrl = _modelArgs.self_ctrl
    
    _radioPhySetup = None
    if 'radio_physetup' in _modelArgs:
        _radioPhySetup = _modelArgs.radio_physetup

    return ModelLoraRadio(_ownernodeins, 
                          _loggerins, 
                          _radioId,
                          _radioPhySetup, 
                          _queueSize, 
                          _selfCtrl)