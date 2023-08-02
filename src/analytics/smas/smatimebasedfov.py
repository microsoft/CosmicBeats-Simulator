'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 11 Jul 2023
@desc
    This module serves as the implementation of the Single Model Analyzer (SMA) for the Field of View (FOV) model (src file: modelfovtimebased.py).

    The SMA generates a dataframe with the following columns:
        1. nodeID
        2. otherNodeID
        3. nodeType
        4. startTimes
        5. endTimes
    
    The SMA specifically focuses on the following string:
    "Pass. nodeID: (int). nodeType: (int). startTimeUnix: (float). endTimeUnix: (float)"
'''

from src.analytics.smas.isma import ISMA
from pandas import DataFrame
import pandas as pd
import dask.dataframe as dd

class SMAFovTimeBased(ISMA):
    '''
    This class implements the SMA for the power model. It takes the time based logs of the power model and generates basic power related insights.
    For example, how much power was generated, how much power was consumed by which component, etc. 
    '''
    __supportedSMANames = [] # No dependency on any other SMA
    __supportedModelNames = ['ModelFovTimeBased'] # Dependency on the power model

    @property
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the SMA class. For example, smapower 
            Note that the name should exactly match to your class name. 
        """
        return self.__class__.__name__
    

    @property
    def supportedModelNames(self) -> 'list[str]':
        '''
        @type
            String
        @desc
           supportedModelNames gives the list of name of the models, the log of which this SMA can process.
        '''
        return self.__supportedModelNames
    
    @property
    def supportedSMANames(self) -> 'list[str]':
        '''
        @type
            String
        @desc
            supportedSMANames gives the list of name of the SMAs, the output of which this SMA can process.
        '''
        return self.__supportedSMANames

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

    def Execute(self):
        """
        This method executes the tasks that needed to be performed by the SMA.
        """
        #let's read the whole log file. Let's use dask because this log file might be huge
        _logData = dd.read_csv(self.__logFile, quotechar='"', delimiter=',', skipinitialspace=True)
        _modelInfo = _logData[_logData['modelName'] == "ModelFovTimeBased"]
        
        #We are only interested in the following string:
        #Pass. nodeID: (int). nodeType: (int). startTimeUnix: (float). endTimeUnix: (float)
        #Let's extract all the information in the following format:
        
        _regex = r'Pass\. nodeID: (?P<otherNodeID>\d+)\. nodeType: (?P<nodeType>\d+)\. startTimeUnix: (?P<startTimeUnix>[\d.]+)\. endTimeUnix: (?P<endTimeUnix>[\d.]+)'
        
        #Let's create a new dataframe with the extracted information
        _extracted = _modelInfo['message'].str.extractall(_regex)
        
        #Let's hope that the extracted dataframe fits into memory
        _df = _extracted.compute()
        
        #Before we convert to lists, let's make sure that the columns are in the right data type
        _dtypes = {'otherNodeID': int, 'nodeType': int, 'startTimeUnix': float, 'endTimeUnix': float}
        _df = _df.astype(_dtypes)
        
        #Let's now aggregate the extracted dataframe to combine the start and end times if the otherNodeID is the same
        _df = _df.groupby('otherNodeID').agg(list).reset_index() #This will make everything but the otherNodeID column as a list
        
        #Make the start and end times DatetimeIndex objects so it is easier to work with
        def __convertToDatetimeIndex(_list):
            return pd.to_datetime(_list, unit='s', utc=True)
        _newStartTime = _df['startTimeUnix'].apply(__convertToDatetimeIndex)
        _newEndTime = _df['endTimeUnix'].apply(__convertToDatetimeIndex)

        #Let's now create the final dataframe
        _resultsDf = pd.DataFrame({'nodeID': self.__nodeID,
                                   'otherNodeID': _df['otherNodeID'],
                                   'nodeType': _df['nodeType'].apply(lambda x: int(x[0])), #convert the list to a single value
                                   'startTimes': _newStartTime,
                                   'endTimes': _newEndTime})        
        
        self.__result = _resultsDf

    def get_Results(self) -> DataFrame:
        '''
        @desc
            This method returns the results of the SMA in the form of a DataFrame table once it is executed.
        @return
            A DataFrame table containing the results of the SMA.
        '''
        return self.__result

    def __init__(self,
                 _modelLogPath: str):
        '''
        @desc
            Constructor
        @param[in] _modelLogPath
            Path to the log file of the model
        '''
        self.__logFile = _modelLogPath
        self.__nodeID = self.__logFile.split('/')[-1].split('_')[-1].split('.')[0] #get the nodeID from the log file name
        self.__result = None
        
def init_SMAFovTimeBased(**_kwargs) -> ISMA:
    '''
    @desc
        Initializes the SMAFovTimeBased class
    @param[in] _kwargs
        Keyworded arguments that are passed to the constructor of the SMAFovTimeBased class.
        It should have the following (key, value) pairs:
        @key modelLogPath
            Path to the log file of the model
    @return
        An instance of the SMAFovTimeBased class
    '''
    #check if the keyworded arguments has the key 'modelLogPath'
    if 'modelLogPath' not in _kwargs:
        raise Exception('[Simulator Exception] The keyworded argument modelLogPath is missing')
    
    #create an instance of the SMAPowerBasic class
    sma = SMAFovTimeBased(_kwargs['modelLogPath'])
    return sma
    
