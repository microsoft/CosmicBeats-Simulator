'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 22 June 2023
@desc
    This module is an extension of the original LoraRadioModel so that we can distinguish between the two lora radios.
    This is used for the aggregator node in the network, i.e., satellite in case of direct-to-satellite communication.
'''

from src.models.models_radio.modelloraradio import ModelLoraRadio
from src.models.imodel import EModelTag, IModel
from src.nodes.inode import INode
from src.simlogging.ilogger import ILogger
from src.models.models_radio.modelloraradio import ModelLoraRadio

class ModelAggregatorRadio(ModelLoraRadio):
    _modeltag = EModelTag.BASICLORARADIO

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

    ##REST IS SAME AS BEFORE
    
def init_ModelAggregatorRadio(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:


    assert _ownernodeins is not None
    assert _loggerins is not None
    assert _modelArgs is not None

    if 'radioID' in _modelArgs:
        _radioId = _modelArgs.radioId
    else:
        _radioId = _ownernodeins.nodeID
    
    _queueSize = -1
    if 'queue_size' in _modelArgs:
        _queueSize = _modelArgs.queueSize
    
    _selfCtrl = True
    if 'self_ctrl' in _modelArgs:
        _selfCtrl = _modelArgs.self_ctrl
    
    _radioPhySetup = None
    if 'radio_physetup' in _modelArgs:
        _radioPhySetup = _modelArgs.radio_physetup

    return ModelAggregatorRadio(_ownernodeins, 
                          _loggerins, 
                          _radioId,
                          _radioPhySetup, 
                          _queueSize, 
                          _selfCtrl)