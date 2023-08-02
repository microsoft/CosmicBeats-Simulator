'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 14 Jul 2023
@desc
    This module analyzes the logs produced by the modelDataGenerator and produces a table in the specified format:
        1. timestamp
        2. action
        3. id
        4. queueSize
        5. sourceNodeID
    The expected log message from the modelDataGenerator must precisely match the following format:
    [Action] dataID: [id]. queueSize: [size]

    The "Action" field currently supports values "Generated" or "Dropped," but it can accommodate any other value as well.
'''

from src.analytics.smas.isma import ISMA
import dask.dataframe as dd
import dask
from pandas import DataFrame
from dask import delayed 

class SMADataGenerator(ISMA):
    '''
    @desc
        This class analyzes the logs produced by the modelDataGenerator and produces a table in the specified format:
        timestamp
        action
        id
        queueSize
        sourceNodeID
    The expected log message from the modelDataGenerator must precisely match the following format:
    [Action] dataID: [id]. queueSize: [size]
    '''
    __supportedSMANames = [] # No dependency on any other SMA
    __supportedModelNames = ['ModelDataGenerator'] # Dependency on the model
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
        '''
        This method executes the tasks that needed to be performed by the SMA.
        '''
        
        #let's read the whole log file. Let's use dask because this log file might be huge
        _logData = dd.read_csv(self.__logFile, quotechar='"', delimiter=',', skipinitialspace=True)
        
        #we should have the following columns: logLevel, timestamp, modelName, message
        #We only need the ones where modelName matches our dependencyModelName
        _modelLogData = _logData[_logData['modelName'] == "ModelDataGenerator"]

        #We are only interested in the following string:
        #[Action] dataID: [id]. queueSize: [size]
        #This string should be the only one this model creates
        
        #Now, let's use regular expressions to extract the information from the log messages. Each one of the following is a dask series
        _times = dd.to_datetime(_modelLogData['timestamp'])
        _actions = _modelLogData['message'].str.extract(r'(\b\w+) ', expand=False)
        _ids = _modelLogData['message'].str.extract(r'dataID: (\d+)', expand=False)
        _queueSize = _modelLogData['message'].str.extract(r'queueSize: (\d+)', expand=False)
        
        #let's create the results table. We do it this way because we want to keep things in parallel as much as possible
        _columns = ['timestamp', 'action', 'id', 'queueSize']
        _seriesList = [_times, _actions, _ids, _queueSize]
        _dfList = [s.to_frame(name=label) for s, label in zip(_seriesList, _columns)]
        
        _results = dd.concat(_dfList, axis=1, ignore_unknown_divisions=True)
        _results = _results.reset_index(drop=True)
        
        #Let's also add in a column for the nodeID
        _results['sourceNodeID'] = self.__nodeID

        #Let's now make everything to the right types
        _dataTypes = {
            'timestamp': 'datetime64[ns]',
            'action': 'str',
            'id': 'int64',
            'queueSize': 'int64',
            'sourceNodeID': 'int64'
        }
        _results = _results.astype(_dataTypes)
        
        self.__results = _results
        
    def get_Results(self) -> DataFrame:
        '''
        @desc
            This method returns the results of the SMA in the form of a DataFrame table once it is executed.
        @return
            A DataFrame table containing the results of the SMA.
        '''
        #make the dask dataframe into a pandas dataframe
        result = dask.compute(self.__results)[0]
        return result

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
        self.__results = None

def init_SMADataGenerator(**_kwargs) -> ISMA:
    '''
    @desc
        Initializes the SMADataGenerator class
    @param[in] _kwargs
        Keyworded arguments that are passed to the constructor of the SMADataGenerator class.
        It should have the following (key, value) pairs:
        @key modelLogPath
            Path to the log file of the model
    @return
        An instance of the SMAPowerBasic class
    '''
    #check if the keyworded arguments has the key 'modelLogPath'
    if 'modelLogPath' not in _kwargs:
        raise Exception('[Simulator Exception] The keyworded argument modelLogPath is missing')
    
    #create an instance of the SMADataGenerator class
    _sma = SMADataGenerator(_kwargs['modelLogPath'])
    return _sma
