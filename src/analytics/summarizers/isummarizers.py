'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 11 Jul 2023
@desc
    This implements the summarizer interface for processing the outputs of SMA(s) or other summarizers. 
'''

from abc import ABC, abstractmethod


class ISummarizer(ABC):
    '''
    This serves as an interface implementation for the summarizer.
    Each summarizer implementation should inherit from this interface.
    The summarizer is responsible for summarizing the results obtained after processing the outputs of one or multiple SMAs and/or existing summarizers.
    It takes the output of SMAs and existing summarizer implementations as input, and then analyzes the inputs to generate a summary of the results in dictionary format.   
    '''
    
    @property
    @abstractmethod
    def iName(self) -> 'str':
        """
        @type 
            str
        @desc
            A string representing the name of the summarizer class. For example, summarizerlatency 
            Note that the name should exactly match to your class name. 
        """
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

    @property
    @abstractmethod
    def supportedSummarizerNames(self) -> 'list[str]':
        '''
        @type
            List of String
        @desc
            supportedSummarizerNames gives the list of name of the Summarizers, the output of which this Summarizer can process.
        '''
        pass

    @abstractmethod
    def call_APIs(
            self, 
            _apiName: str, 
            **_kwargs):
        '''
        This method acts as an API interface of the summarizer. 
        An API offered by the summarizer can be invoked through this method.
        @param[in] _apiName
            Name of the API. Each summarizer should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        pass

    @abstractmethod
    def Execute(self):
        """
        This method executes the tasks that needed to be performed by the summarizer.
        """
        pass
    
    @abstractmethod
    def get_Results(self) -> 'dict':
        '''
        @desc
            This method returns the results of the  in the form of a dictionary where the key is the name of the metric and the value is the results.
        @return
            The results of the summarizer in the form of a dictionary where the key is the name of the metric and the value is the results.
        '''
        pass