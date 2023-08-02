'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 31 Oct 2022
@desc
    In this module, we list the initialization methods for different model class implementations.
    Initialization method must be written in the same module as where class implementation is written. 
    The initialization method must be added in the dictionary below as the value against the key as the name of the class
    The prototype of the initialization method goes below.
    
    init_Classname(_ownernodeins:INode, _loggerins:ILogger, _modelArgs) -> IModel
    Here,
    @desc
        This method initializes an instance of ModelOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "tle_1": "1 50985U 22002B   22290.71715197  .00032099  00000+0  13424-2 0  9994",
            "tle_2": "2 50985  97.4784 357.5505 0011839 353.6613   6.4472 15.23462773 42039",
        }
    @return
        Instance of the model class
'''

# import the node class here
from src.models.models_orbital.modelorbit import init_ModelOrbit
from src.models.models_orbital.modelorbitonefullupdate import init_ModelOrbitOneFullUpdate
from src.models.models_orbital.modelfixedorbit import init_ModelFixedOrbit

from src.models.models_fov.modelhelperfov import init_ModelHelperFoV
from src.models.models_fov.modelfovtimebased import init_ModelFovTimeBased

from src.models.models_power.modelpower import init_ModelPower

from src.models.models_radio.modelisl import init_ModelISL

from src.models.models_radio.modelloraradio import init_ModelLoraRadio
from src.models.models_radio.modelaggregatorradio import init_ModelAggregatorRadio
from src.models.models_radio.modeldownlinkradio import init_ModelDownlinkRadio
from src.models.models_radio.modelimagingradio import init_ModelImagingRadio

from src.models.models_data.modeldatagenerator import init_ModelDataGenerator
from src.models.models_data.modeldatarelay import init_ModelDataRelay
from src.models.models_data.modeldatastore import init_ModelDataStore

from src.models.models_mac.modelmacttnc import init_ModelMACTTnC
from src.models.models_mac.modelmacgateway import init_ModelMACgateway
from src.models.models_mac.modelmaciot import init_ModelMACiot
from src.models.models_mac.modelmacgs import init_ModelMACgs

from src.models.models_scheduling.modelcompute import init_ModelCompute
from src.models.models_scheduling.modeledgecompute import init_ModelEdgeCompute

from src.models.models_tumbling.modeladacs import init_ModelADACS

from src.models.models_imaging.modelimaginglogicbased import init_ModelImagingLogicBased

modelInitDictionary = {
    "ModelOrbit" : init_ModelOrbit,
    "ModelOrbitOneFullUpdate": init_ModelOrbitOneFullUpdate,
    "ModelFixedOrbit": init_ModelFixedOrbit,
    
    "ModelHelperFoV": init_ModelHelperFoV,
    "ModelFovTimeBased": init_ModelFovTimeBased,

    "ModelDataGenerator": init_ModelDataGenerator,
    
    "ModelPower": init_ModelPower,

    "ModelISL": init_ModelISL,

    "ModelLoraRadio": init_ModelLoraRadio,
    "ModelAggregatorRadio": init_ModelAggregatorRadio,
    "ModelDownlinkRadio": init_ModelDownlinkRadio,
    "ModelImagingRadio": init_ModelImagingRadio,

    "ModelDataStore": init_ModelDataStore,
    "ModelDataRelay": init_ModelDataRelay,

    "ModelMACTTnC": init_ModelMACTTnC,
    "ModelMACgateway": init_ModelMACgateway,
    "ModelMACiot": init_ModelMACiot,
    "ModelMACgs": init_ModelMACgs,
    
    "ModelCompute": init_ModelCompute,
    "ModelEdgeCompute": init_ModelEdgeCompute,
    
    "ModelADACS": init_ModelADACS,
    
    "ModelImagingLogicBased": init_ModelImagingLogicBased
    }