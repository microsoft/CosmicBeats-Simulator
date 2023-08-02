'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 11 Jul 2023
@desc
    This implements the single model analyzer (SMA) interface. 
'''

from abc import ABC, abstractmethod
from pandas import DataFrame

class ISMA(ABC):
    '''
    This serves as an interface implementation for the Single Model Analyzer (SMA).
    Each SMA implementation should inherit from this interface.
    The SMA is responsible for analyzing the outcomes of a single model.
    It accepts the logs of a single model from a node or the output of an existing SMA implementation as input.
    It then analyzes the logs, generates the results, and presents them in a table format.    
    '''
    
    @property
    @abstractmethod
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the SMA class. For example, smapower 
            Note that the name should exactly match to your class name. 
        """
        pass
    
    @property
    @abstractmethod
    def supportedModelNames(self) -> 'list[str]':
        '''
        @type
            String
        @desc
            supportedModelNames gives the list of name of the models, the log of which this SMA can process.
        '''
        pass

    @property
    @abstractmethod
    def supportedSMANames(self) -> 'list[str]':
        '''
        @type
            String
        @desc
            supportedSMANames gives the list of name of the SMAs, the output of which this SMA can process.
        '''
        pass


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
    def get_Results(self) -> DataFrame:
        '''
        @desc
            This method returns the results of the SMA in the form of a DataFrame table once it is executed.
        @return
            A DataFrame table containing the results of the SMA.
        '''
        pass