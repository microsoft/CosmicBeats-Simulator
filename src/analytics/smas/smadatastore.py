'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 13 Jul 2023
@desc
    This is the implementation of the Single Model Analyzer (SMA) for the DataStore (source file: modeldatastore.py).
    It operates by analyzing the logs generated by the modelDataStore and producing a table in the specified format:

        1. timestamp
        2. action
        3 .id
        4. sourceNodeID
        5. creationTime
        6. timeDelay
        7. queueSize
        8. nodeID
    The "action" can take one of the following values: Queuing, Dequeuing, or Dropping.
'''

from src.analytics.smas.isma import ISMA
import dask.dataframe as dd
from pandas import DataFrame
from dask import delayed 

class SMADataStore(ISMA):
    '''
    @desc
        This class analyzes the logs produced by the modelDataStore and produces a table in the specified format:
        1. timestamp
        2. action
        3 .id
        4. sourceNodeID
        5. creationTime
        6. timeDelay
        7. queueSize
        8. nodeID
    The "action" can take one of the following values: Queuing, Dequeuing, or Dropping.
    '''

    __supportedSMANames = [] # No dependency on any other SMA
    __supportedModelNames = ['ModelDataStore'] # Dependency on the DataStore model

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
        
        #we should have the following columns: logLevel, timestamp, modelName, message
        #We only need the ones where modelName matches the DataStore
        _modelLogData = _logData[_logData['modelName'] == "ModelDataStore"]
        
        #We are only interested in the following string:
        #[Action] data id: [id]. Created at: [timestamp]. Source: [sourceNodeID]. Time delay: [delay]. Current queue size: [size]
        #Let's ignore the rest
        
        _modelLogData['action'] = _modelLogData['message'].apply(lambda x: x.split(' ')[0], meta=('logType', 'str'))     
        _interestedMessages = ['Dequing', 'Dropping', 'Queuing']
        _interestedData = _modelLogData[_modelLogData['action'].isin(_interestedMessages)]
        
        #Now, let's use regular expressions to extract the information from the log messages. Each one of the following is a dask series
        _times = dd.to_datetime(_interestedData['timestamp'])
        _actions = _interestedData['action']
        _ids = _interestedData['message'].str.extract(r'dataID: (\d+)', expand=False)
        _sources = _interestedData['message'].str.extract(r'sourceNodeID: (\d+)', expand=False)
        _generationTimes = _interestedData['message'].str.extract(r'creationTime: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', expand=False)
        _timeDelay = _interestedData['message'].str.extract(r'timeDelay: (\d+\.\d+)', expand=False)
        _queueSize = _interestedData['message'].str.extract(r'queueSize: (\d+)', expand=False)
        
        #let's create the results table. We do it this way because we want to keep things in parallel and not in local mem as much as possible
        _columns = ['timestamp', 'action', 'dataID', 'sourceNodeID', 'creationTime', 'timeDelay', 'queueSize']
        _seriesList = [_times, _actions, _ids, _sources, _generationTimes, _timeDelay, _queueSize]
        _dfList = [s.to_frame(name=label) for s, label in zip(_seriesList, _columns)]
        
        _results = dd.concat(_dfList, axis=1)
        _results = _results.reset_index(drop=True)
        
        #Let's also add in a column for the nodeID
        _results['nodeID'] = self.__nodeID
        
        #Let's now make everything the right types
        _dataTypes = {
            'timestamp': 'datetime64[ns]',
            'action': 'str',
            'dataID': 'int64',
            'sourceNodeID': 'int64',
            'creationTime': 'datetime64[ns]',
            'timeDelay': 'float64',
            'queueSize': 'int64',
            'nodeID': 'int64'
        }
        self.__results = _results.astype(_dataTypes)
                
    def get_Results(self) -> DataFrame:
        '''
        @desc
            This method returns the results of the SMA in the form of a DataFrame table once it is executed.
        @return
            A DataFrame table containing the results of the SMA.
        '''
        #make the dask dataframe into a pandas dataframe
        _pandasDataframe = self.__results.compute()
        return _pandasDataframe
    
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

def init_SMADataStore(**_kwargs) -> ISMA:
    '''
    @desc
        Initializes the SMADataStore class
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
    sma = SMADataStore(_kwargs['modelLogPath'])
    return sma
