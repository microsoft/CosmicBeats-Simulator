'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 14 Jul 2023
@desc
    SummarizerMultiplePower is a summarizer designed to consolidate the results of multiple power models.
    It calculates and presents the following metrics:

        1. percentCharging: The percentage of time when the battery was charging
        2. averagePowerGeneration: The average power generation
        3. averageNumberOfTimesWhenBatteryWasEmpty: The average number of times when the battery was empty
        4. averageBatteryLevel: The average battery level
        5. maximumComponent: The most common component that consumed the maximum power
'''
from src.analytics.summarizers.isummarizers import ISummarizer
import pandas as pd

class SummarizerMultiplePower(ISummarizer):
    @property
    def iName(self) -> 'str':
        """
        @type 
            str
        @desc
            A string representing the name of the summarizer class. For example, summarizerlatency 
            Note that the name should exactly match to your class name. 
        """
        return self.__class__.__name__
    
    @property
    def supportedSMANames(self) -> 'list[str]':
        '''
        @type
            String
        @desc
            supportedSMANames gives the list of name of the SMAs, the output of which this SMA can process.
        '''
        return []

    @property
    def supportedSummarizerNames(self) -> 'list[str]':
        '''
        @type
            List of String
        @desc
            supportedSummarizerNames gives the list of name of the Summarizers, the output of which this Summarizer can process.
        '''
        return []

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
    
    def Execute(self):
        """
        This method executes the tasks that needed to be performed by the summarizer.
        """
        #The power metrics are the following:
        #percentCharging, averagePowerGeneration, averagePowerConsumption, numberOfTimesWhenBatteryWasEmpty, averageBatteryLevel, 
        # averagePowerConsumptionByComponent, maxComponent, numberOfDenials
        
        #let's create a dataframe where the columns are the power metrics and the rows are the power models
        _listOfDicts = []
        for _powerModel in self.__powerSummarizers:
            _listOfDicts.append(_powerModel.get_Results())
        _df = pd.DataFrame(_listOfDicts)

        outDict = {}
        outDict['percentCharging'] = _df['percentCharging'].mean()
        outDict['averagePowerGeneration'] = _df['averagePowerGeneration'].mean()
        outDict['avgNumberOfTimesWhenBatteryWasEmpty'] = _df['numberOfTimesWhenBatteryWasEmpty'].mean()
        outDict['averageBatteryLevel'] = _df['averageBatteryLevel'].mean()
        outDict['mostCommonMax'] = _df['maxComponent'].mode()[0]
        self.__results = outDict
        
    def get_Results(self) -> 'dict':
        '''
        @desc
            This method returns the results
        @return
            The results of the summarizer in the form of a dictionary where the key is the name of the metric and the value is the results.
        '''
        return self.__results
    
    def __init__(self,
                 _powerSummarizers: 'List[ISummarizer]'):
        '''
        @desc
            Constructor of the class
        @param[in] _powerModelResult
            The result of the power model
        '''
        self.__powerSummarizers = _powerSummarizers
        self.__results = {}

def init_SummarizerMultiplePower(**_kwargs):
    """
    @desc
        Initializes the SummarizerMultiplePower class
    @param[in] _kwargs
        Keyworded arguments that are passed to the constructor of the SummarizerMultiplePower class
        @key _powerSummarizers
            List of power summarizers
    @return
        An instance of the SummarizerMultiplePower class
    """
    
    if '_powerSummarizers' in _kwargs:
        return SummarizerMultiplePower(_powerSummarizers=_kwargs['_powerSummarizers'])
    else:
        raise Exception('[Simulator Exception] SummarizerMultiplePower: No _powerSummarizers provided')