'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 07 Nov 2022
@desc
    This module implements the simulator class. It's the face of simulation pipeline.
'''

from src.sim.orchestrator import Orchestrator
from src.sim.imanager import IManager
from src.sim.managerparallel import ManagerParallel


class Simulator():
    '''
    This is the entry class to our simulation pipeline. 
    It invokes the orchestrator and hands over the simulation environment to the manager.  
    '''
    _configFilePath: str
    _orchestrator: Orchestrator
    _manager: IManager

    def __init__(
            self,
            _configfilepath: str,
            _numWorkers: int = 1) -> None:
        '''
        @desc
            Constructor of the simulator class.
        @param[in]  _configfilepath
            File path to the configuration file
        @param[in]  _numWorkers
            Number of workers to be used for parallel execution
        '''
        self.__configFilePath = _configfilepath

        #  invoke the orchestrator to create the simulation environment
        self.__orchestrator = Orchestrator(self.__configFilePath)
        self.__orchestrator.create_SimEnv()
        __simEnv = self.__orchestrator.get_SimEnv()

        # hand over the simulation environment to the manager
        self.__manager = ManagerParallel(
                                    topologies = __simEnv[0], 
                                    numOfSimSteps = __simEnv[1],
                                    numOfWorkers = _numWorkers
                                    )

    def call_RuntimeAPIs(self, 
                        _api: str, 
                        **_kwargs):
        '''
        This method acts as a runtime API interface of the manager. 
        An API offered by the manager can be invoked through this method in runtime.
        @param[in] _api
            Name of the API. Each model should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''

        _ret = None        
       # check that manager is not None
        if(self.__manager is None):
            raise Exception("[Simulator]: Manager is not initialized")
        
        #check that the API name is not None
        if(_api is None):
            raise Exception("[Simulator]: API name needs to be provided")
        
        # call the API from the manager
        try:
            _ret = self.__manager.call_APIs(_api, **_kwargs)
        except Exception as e:
            raise Exception(f"[Simulator]: The API call returned an exception: {e}")
        
        return _ret
      
    def execute(self):
        '''
        @desc
            Executes the simulation
        '''
        self.__manager.run_Sim()