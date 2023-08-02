'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 1 Feb 2023
@desc
    This implements a radio model to model an imaging satellite's radio model. 
    See the link model (src/models/network/imaging/imaginglink.py) for more details.
    This is based off of the generic radio model (src/models/models_radio/modelgenericradio.py) and inherits from it. 
'''

from src.sim.imanager import EManagerReqType
from src.models.imodel import IModel, EModelTag
from src.nodes.inode import ENodeType, INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.imodel import EModelTag

from src.models.network.imaging.imagingchannel import ImagingChannel
from src.models.network.imaging.imagingradiodevice import ImagingRadioDevice
from src.models.models_radio.modelgenericradio import ModelGenericRadio

class ModelImagingRadio(ModelGenericRadio):
    _modeltag = EModelTag.IMAGINGRADIO
    __dependencies = [['ModelHelperFoV', 'ModelFovTimeBased']]

    def _radioDeviceClass(self):
        return ImagingRadioDevice
    
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
    
    def _update_Channel(self):
        """
        @desc
            This method updates the channels of the radio device.
            This should only be called when the node is transmitting
        """

        #Let's get all the possible devices that we can transmit to - let's find which devices are in the view
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
        
        self._logger.write_Log("Node {} has {} nodes in its view".format(self._ownernode.nodeID, len(_visibleNodeIDs)), ELogType.LOGINFO, self._ownernode.timestamp)
        
        if len(_visibleNodeIDs) == 0:
            return
        
        _topologyID = self._ownernode.topologyID
        _topologies = self._ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
        
        _myTopology:'ITopology' = None
        for _topology in _topologies:
            if _topology.id == _topologyID:
                _myTopology = _topology
                break
        
        _nodes = [_myTopology.get_Node(_nodeId) for _nodeId in _visibleNodeIDs]
        #now let's get the radio devices from the nodes
        _models = []
        for _node in _nodes:
            for _model in _node.get_Models():
                if _model.modelTag == EModelTag.IMAGINGRADIO and _model._get_Frequency() == self._get_Frequency():
                    _models.append(_model)

        _devices = [_model.call_APIs("get_RadioDevice") for _model in _models]

        _channels = []
        for _device in _devices:
            _channel = ImagingChannel()
            _channel.add_Device(_device)
            _channel.add_Device(self._radioDevice)
            _channels.append(_channel)
            
        self._radioDevice.set_Channels(_channels)

    ##REST IS SAME AS BEFORE

def init_ModelImagingRadio(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelImagingRadio class
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

    return ModelImagingRadio(_ownernodeins, 
                          _loggerins, 
                          _radioId,
                          _radioPhySetup, 
                          _queueSize, 
                          _selfCtrl)