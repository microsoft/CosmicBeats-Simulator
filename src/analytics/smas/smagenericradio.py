'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 14 Jul 2023
@desc  
    This module analyzes the logs produced by the ModelGenericRadio and creates a table in the specified format:
    1. timestamp
    2. action
    3. objectType
    4. objectID
    5. nodesInChannel
    6. rxQueueSize
    7. txQueueSize
    8. nodeID
    The log message to be processed must strictly adhere to the following structure:
    "Action: {_action}. ObjectType: {_objectType}. ObjectID: {_objectID}. NodesInChannels: {[listOfNodes]}. RxQueueSize: {_rxQueueSize}. TxQueueSize: {_txQueueSize}"
    (Note: The brackets in the log message are placeholders to indicate the actual values that will replace them.)
'''

from src.analytics.smas.isma import ISMA
import dask.dataframe as dd
import dask
from pandas import DataFrame

class SMAGenericRadio(ISMA):
    '''
    @desc
        This class analyzes the logs produced by the ModelGenericRadio and creates a table in the specified format:
        1. timestamp
        2. action
        3. objectType
        4. objectID
        5. nodesInChannel
        6. rxQueueSize
        7. txQueueSize
        8. nodeID
        The log message to be processed must strictly adhere to the following structure:
        "Action: {_action}. ObjectType: {_objectType}. ObjectID: {_objectID}. NodesInChannels: {[listOfNodes]}. RxQueueSize: {_rxQueueSize}. TxQueueSize: {_txQueueSize}"
        (Note: The brackets in the log message are placeholders to indicate the actual values that will replace them.)
    '''
    __supportedSMANames = [] # No dependency on any other SMA
    __supportedModelNames = ['SMAGenericRadio'] # Dependency on the model
    
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
        #We only need the ones where modelName matches our dependencyModelName
        _modelLogData = _logData[_logData['modelName'] == self.__radioModel]
        
        _regex = r"Action: (?P<action>[\w]+)\. ObjectType: (?P<objectType>[\w]+)\. ObjectID: (?P<objectID>[\w]+)\. " + \
            "NodesInChannels:\s*\[(?P<nodesInView>(?:\d+\s*,\s*)*\d*)\]. RxQueueSize: (?P<rxQueueSize>[\w]+)\. TxQueueSize: (?P<txQueueSize>[\w]+)"
        _extracted = _modelLogData['message'].str.extract(_regex)

        #Extracted should have the following columns: action, objectType, objectID, nodesInView, rxQueueSize, txQueueSize
        #Let's add in the timestamp and the nodeID
        _extracted['timestamp'] = _modelLogData['timestamp']
        _extracted['nodeID'] = self.__nodeID

        #Let's now make everything to the right types
        _dataTypes = {
            'timestamp': 'datetime64[ns]',
            'action': 'str',
            'objectType': 'str',
            'objectID': 'int',
            'nodesInView': 'object',
            'rxQueueSize': 'int',
            'txQueueSize': 'int',    
        }
        _results = _extracted.astype(_dataTypes)
        
        #Also, reset the index
        _results = _results.reset_index(drop=True)
        
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
                 _modelLogPath: str,
                 _radioModel: str):
        '''
        @desc
            Constructor
        @param[in] _modelLogPath
            Path to the log file of the model
        @param[in] _radioModel
            The name of the specific radio model which extends the ModelGenericRadio class
        '''
        self.__logFile = _modelLogPath
        self.__nodeID = self.__logFile.split('/')[-1].split('_')[-1].split('.')[0] #get the nodeID from the log file name
        self.__results = None
        self.__radioModel = _radioModel

def init_SMAGenericRadio(**_kwargs) -> ISMA:
    '''
    @desc
        Initializes the SMAGenericRadio class
    @param[in] _kwargs
        Keyworded arguments that are passed to the constructor of the SMAGenericRadio class.
        It should have the following (key, value) pairs:
        @key modelLogPath
            Path to the log file of the model
        @key radioModelName
            Name of the specific radio model which extends the ModelGenericRadio class
    @return
        An instance of the SMAGenericRadio class
    '''
    if 'modelLogPath' not in _kwargs:
        raise Exception('[Simulator Exception] The keyworded argument modelLogPath is missing')
    
    #create an instance of the SMADataGenerator class
    _sma = SMAGenericRadio(_kwargs['modelLogPath'], _kwargs['radioModelName'])
    return _sma
