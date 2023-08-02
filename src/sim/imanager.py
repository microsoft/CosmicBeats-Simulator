'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 19 Oct 2022
@desc
    This module implements the manager interface for the simulator
'''

from abc import ABC, abstractmethod
from enum import Enum

class EManagerReqType(Enum):
    '''
    An enum listing the request types that a manager handles
    '''
    GET_TOPOLOGIES = 0
    GET_TIMESTEPLENGTH = 1

class IManager(ABC):
    '''
    Interface of the simulation runtime manager.
    It handles the simulation in the runtime.  
    '''
    @abstractmethod
    def req_Manager(
            self, 
            _reqType: EManagerReqType, 
            **_kwargs):
        '''
        @desc
           Send a request to the manager through this method
        @param[in]  _reqType
            Type of the request
        @param[in] _kwargs
            Keyworded arguments to be passed to the request handler function.
            Take a look at the request handler function definition to know the keyworded argument lists pertinent to that
        @return
            Returns the results (if any)
        '''
        pass
    

    def run_Sim(self):
        '''
        @desc
            This method is called to run the simulation.
        '''
        pass

