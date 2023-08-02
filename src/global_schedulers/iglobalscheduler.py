'''
Created by: Om Chabra
Created on: 27 Jul 2023
@desc
    This is a generic interface for a global scheduler.
    In the real world, a global scheduler (likely in the cloud) will run a simulation of the network and
    perform some algorithm to determine some desired results and then transmit this
    information to the nodes.
    
    Here, what we are doing is that we will first run a simulation of the network and
    while doing so will collect information about the network and run some algorithm.
    
    We then have two options: 
    1. Pickle this information and rerun the simulation with the pickled information.
    2. Use the ManagerParallel's API "call_ModelAPIsByModelName" to call a model and directly send the information to the nodes
'''

from abc import ABC, abstractmethod
from pandas import DataFrame

class IGlobalScheduler(ABC):    
    @abstractmethod
    def call_APIs(
            self, 
            _apiName: str, 
            **_kwargs):
        '''
        This method acts as an API interface of the SMA. 
        An API offered by the SMA can be invoked through this method.
        @param[in] _apiName
            Name of the API. Each SMA should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        pass

    @abstractmethod
    def Execute(self):
        """
        This method executes the tasks that needed to be performed by the SMA.
        """
        pass

    @abstractmethod
    def save_Schedule(self):
        """
        This method saves the schedule to a file. 
        """
        pass
    
    @abstractmethod
    def setup_Simulation(self):
        """
        This method setups the simulation.
        """
        pass