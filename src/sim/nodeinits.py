'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 31 Oct 2022
@desc
    In this module, we list the initialization methods for different node class implementations.
    Initialization method must be written in the same module as where class implementation is written. 
    The initialization method must be added in the dictionary below as the value against the key as "iname" (implementation name) of the class
    The prototype of the initialization method goes below.
    
    init_ClassName(__nodeDetails, __timeDetails, __topologyID, __logger, _managerInstance) -> INode
    Here,
    @param[in]  __nodeDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            give example of the literals that your initialization methods look for
        }
    @param[in]  __timeDetails
        It's a converted JSON object containing the simulation timing related info. 
        The JOSN object must have the literals as follows (values are given as example).
        {
            give example of the literals that your initialization methods look for
        }
    @param[in]  __topologyID
        The ID of the topology that the node instance is part of
    @param[in]  __logger
        Logger instance
    @return
        Created instance of the class
'''

# import the node class here
from src.nodes.satellitebasic import init_SatelliteBasic
from src.nodes.gsbasic import init_GSBasic
from src.nodes.iotbasic import init_IoTBasic


nodeInitDictionary = {
    "SatelliteBasic" : init_SatelliteBasic,
    "GSBasic": init_GSBasic,
    "IoTBasic": init_IoTBasic
    }