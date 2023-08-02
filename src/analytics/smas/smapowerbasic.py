'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 11 Jul 2023
@desc
    This is the implementation of the Single Model Analyzer (SMA) for the time-based Field of View (src file: modelpowerbasic.py).

    The SMA generates a dataframe with the following columns:

    1. timestamp
    2. currentCharge
    3. chargeGenerated
    4. outOfPower
    5. tag0
    6. requested0
    7. granted0
    8. consumed0
    9. tag1
    10. requested1
    11. granted1
    12 .consumed1
    ...
    This column structure allows easy addition and removal of columns/tags in the future.

    The SMA is specifically interested in the following string:
    "PowerStats. CurrentCharge: [float] J. ChargeGenerated: [float] J. OutOfPower: [bool]. Tag: [str], Requested: [bool/NA], Granted: [bool/NA], Consumed: [float] J"
    (Note: The brackets in the log message are included as part of the string. The last four values - tag, requested, granted, and consumed - are repeated for each tag.)
'''

from src.analytics.smas.isma import ISMA
from pandas import DataFrame
import pandas as pd
import dask.dataframe as dd

class SMAPowerBasic(ISMA):
    '''
    This class implements the SMA for the power model. It takes the time based logs of the power model and generates basic power related insights.
    For example, how much power was generated, how much power was consumed by which component, etc. 
    '''

    __supportedSMANames = [] # No dependency on any other SMA
    __supportedModelNames = ['ModelPower'] # Dependency on the power model

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
        _powerData = _logData[_logData['modelName'] == "ModelPower"]
        
        #We are only interested in the following string:
        #PowerStats. CurrentCharge: [float] J. ChargeGenerated: [float] J. OutOfPower: [bool]. [Tag: [str], Requested: [bool/NA], Granted: [bool/NA], Consumed: [float] J] [Tag: [str], Requested: [bool/NA], Granted: [bool/NA], Consumed: [float] J] ...
        #(The brackets are actually included in the string)
        _interestingLogs = _powerData[_powerData['message'].str.contains('PowerStats')]
        
        #Let's extract all the information in the brackets
        _regex = r"\[(.*?)\]"
        
        #Let's create a new dataframe with the extracted information
        _extracted = _interestingLogs['message'].str.extractall(_regex)
        
        #This should now be a dask multi-index series. We need to turn it into a dataframe
        #Let's hope this can fit into memory
        _df = _extracted.compute()
        
        #Let's unstack it from multi-index to a dataframe
        _results = _df.unstack().reset_index(drop=True)
        
        #let's also add the timestamp column as the first column
        _results.insert(0, 'timestamp', _interestingLogs['timestamp'].compute().reset_index(drop=True))
        
        #Let's label the columns
        _numColumns = len(_results.columns)
        _columns = ['timestamp', 'currentCharge', 'chargeGenerated', 'outOfPower']
        for i in range(4, _numColumns, 4):
            _columns.append('tag' + str((i-4)//4))
            _columns.append('requested' + str((i-4)//4))
            _columns.append('granted' + str((i-4)//4))
            _columns.append('consumed' + str((i-4)//4))

        _results.columns = _columns
        
        #Make everything but the timestamp column numeric
        _results = _results.apply(pd.to_numeric, errors='ignore')
        self.__result = _results
        

    def get_Results(self) -> DataFrame:
        '''
        @desc
            This method returns the results of the SMA in the form of a DataFrame table once it is executed.
        @return
            A DataFrame table containing the results of the SMA.
        '''
        if self.__result is None:
            raise Exception('[Simulator Exception] The SMA has not been executed yet')
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
        self.__result = None

def init_SMAPowerBasic(**_kwargs) -> ISMA:
    '''
    @desc
        Initializes the SMAPowerBasic class
    @param[in] _kwargs
        Keyworded arguments that are passed to the constructor of the SMAPowerBasic class.
        It should have the following (key, value) pairs:
        @key modelLogPath
            Path to the log file of the model
    @return
        An instance of the SMAPowerBasic class
    '''
    #check if the keyworded arguments has the key 'modelLogPath'
    if 'modelLogPath' not in _kwargs:
        raise Exception('[Simulator Exception] The keyworded argument modelLogPath is missing')
    #create an instance of the SMAPowerBasic class
    sma = SMAPowerBasic(_kwargs['modelLogPath'])
    return sma
