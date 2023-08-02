'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 14 Jul 2023
@desc
    This module is responsible for implementing the summarization at the data layer. It calculates and generates the following metrics:
        1. endToEndPLR: End to end packet loss rate
        2. generatorToSatPLR: Packet loss rate from the generator to the satellite
        3. satToGroundPLR: Packet loss rate from the satellite to the ground
        4. endToEndLatency: End to end latency
        5. generatorToSatLatency: Latency from the generator to the satellite
        6. satToGSLatency: Latency from the satellite to the ground
        7. generationRate: Rate at which the data is generated
        8. satelliteAggregationRate: Rate at which the satellite is aggregating the data
        9. gsAggregationRate: Rate at which the groundstation is aggregating the data
'''
from src.analytics.summarizers.isummarizers import ISummarizer
from pandas import DataFrame
import pandas as pd

class SummarizerDataLayer(ISummarizer):
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
        return ['SMADataGenerator', 'SMADataStore']

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
    
    def __get_CumulativeData(self):
        """
        @desc
            Let's take the outputs of the SMAs and generate a new table which has the following columns:
            'dataID', 'sourceNodeID', 'generatedTime', 'gsReceivedNodeID', 'gsReceivedTime', 'satReceivedNodeID', 'satReceivedTime', 'firstGSReceivedTime', 'firstSatReceivedTime'
            The types of the columns are as follows:
            int, int, datetime, list[int], DatetimeIndex, list[int], DatetimeIndex, datetime, datetime
        @return
            The dataframe containing the data produced
        """
        #Let's first populate the first 3 columns from the outputs of the generator SMAs
        _generatorFrames = []
        for _generatorSMA in self.__generatorSMAs:
            _results = _generatorSMA.get_Results()

            if len(_results.index) == 0:
                continue

            #_results is a dataframe with the following columns: 
            #timestamp, action, id, queueSize, sourceNodeID
            #Let's just keep the following columns: 'timestamp', 'id', 'sourceNodeID'. We'll keep the data regardless of whether they were queued or not
            _useful = _results[['id', 'sourceNodeID', 'timestamp']] 
            _useful.columns = ['dataID', 'sourceNodeID', 'generatedTime']
            _generatorFrames.append(_useful)

        _cumulativeData = pd.concat(_generatorFrames, ignore_index=True)    
                
        #Let's setup a dataframe to hold all the data that was received by the groundstations
        #I expect multiple rows. Each row is one time the data was received by a groundstation
        #I want the dataframe (_gsAggregatedData) to have columns=['dataID', 'gsReceivedNodeID', 'receivedTime'].
        _gsFrames = []
        for _gsDataStoreSMA in self.__gsDataStoreSMAs:
            _data = _gsDataStoreSMA.get_Results()
            
            if len(_data.index) == 0:
                continue

            #We need the following columns: 'timestamp', 'dataID', 'nodeID'
            _data = _data[['dataID', 'nodeID', 'timestamp']]
            _data.columns = ['dataID', 'gsReceivedNodeID', 'gsReceivedTime']
            #Let's add the data to the aggregated dataframe
            _gsFrames.append(_data)
        
        _gsAggregatedData = pd.concat(_gsFrames, ignore_index=True)
        
        #Now, let's group the data by dataID. Make the nodeIDs and timestamps into lists
        _gsAggregatedData = _gsAggregatedData.groupby(['dataID']).agg({'gsReceivedNodeID': list, 'gsReceivedTime': list}).reset_index()

        #Now, let's do the same for the satellite data store (_satelliteAggregatedData)
        #we want columns=['dataID', 'satelliteReceivedNodeID', 'receivedTime']
        _satFrames = []     
        for _satDataStoreSMA in self.__satelliteDataStoreSMAs:
            _data = _satDataStoreSMA.get_Results()
            if len(_data.index) == 0:
                continue
            
            _data = _data[['dataID', 'nodeID', 'timestamp']]
            _data.columns = ['dataID', 'satReceivedNodeID', 'satReceivedTime']
            _satFrames.append(_data)
        
        _satelliteAggregatedData = pd.concat(_satFrames, ignore_index=True)
        #Now, let's group the data by dataID. Make the nodeIDs and timestamps into lists
        _satelliteAggregatedData = _satelliteAggregatedData.groupby(['dataID']).agg({'satReceivedNodeID': list, 'satReceivedTime': list}).reset_index()

        #Now, let's merge all three dataframes
        #If a dataID is not present in the _gsAggregatedData, then it means that the packet was not received by any groundstation
        #If a dataID is not present in the _satelliteAggregatedData, then it means that the packet was not received by the satellite
        #These values will be None in the final dataframe
        #Currently, _cumulativeData has the following columns: 
        #'dataID', 'sourceNodeID', 'generatedTime', 'gsReceivedNodeID', 'gsReceivedTime', 'satReceivedNodeID', 'satReceivedTime',
        _cumulativeData = _cumulativeData.merge(_gsAggregatedData, how='left', on='dataID')
        _cumulativeData = _cumulativeData.merge(_satelliteAggregatedData, how='left', on='dataID')
        
        #Let's make sure all the times are pandas timestamps
        _cumulativeData['generatedTime'] = pd.to_datetime(_cumulativeData['generatedTime'])
        
        #These will become DatetimeIndex. See https://pandas.pydata.org/docs/reference/api/pandas.DatetimeIndex.html
        _cumulativeData['gsReceivedTime'] = _cumulativeData['gsReceivedTime'].apply(pd.to_datetime)
        _cumulativeData['satReceivedTime'] = _cumulativeData['satReceivedTime'].apply(pd.to_datetime)
        
        #Let's add the last two columns
        _cumulativeData['firstGSReceivedTime'] =_cumulativeData['gsReceivedTime'].apply(lambda x: x.min() if isinstance(x, pd.DatetimeIndex) else pd.NaT) 
        _cumulativeData['firstSatReceivedTime'] = _cumulativeData['satReceivedTime'].apply(lambda x: x.min() if isinstance(x, pd.DatetimeIndex) else pd.NaT)
        _cumulativeData['firstGSReceivedTime'] = pd.to_datetime(_cumulativeData['firstGSReceivedTime'])
        _cumulativeData['firstSatReceivedTime'] = pd.to_datetime(_cumulativeData['firstSatReceivedTime'])
        
        return _cumulativeData
    
    def __get_EndToEndPLR(self, _cumulativeData: 'DataFrame') -> 'float':
        """
        @desc
            This method calculates the end to end PLR
        @param[in] _cumulativeData
            The dataframe containing the data produced
        @return
            The PLR from 0 to 1
        """
        #We need the number of packets that were generated and not received by the groundstation
        _numPacketsGenerated = len(_cumulativeData.index)
        print("num packets generated", _numPacketsGenerated)
        _numPacketsReceivedByGS = len(_cumulativeData[_cumulativeData['gsReceivedNodeID'].notnull()].index)
        print("num packets received by gs", _numPacketsReceivedByGS)
        return (_numPacketsGenerated - _numPacketsReceivedByGS) / _numPacketsGenerated

    def __get_generatorToSatPLR(self, _cumulativeData: 'DataFrame') -> 'float':
        """
        @desc
            This method calculates the number of packets that were generated but not received by the satellite
        @param[in] _cumulativeData
            The dataframe containing the data produced
        @return
            The PLR from 0 to 1
        """
        _numPacketsGenerated = len(_cumulativeData.index)
        _numPacketsReceivedBySat = len(_cumulativeData[_cumulativeData['satReceivedNodeID'].notnull()].index)
        print("num packets received by sat", _numPacketsReceivedBySat)
        return (_numPacketsGenerated - _numPacketsReceivedBySat) / _numPacketsGenerated
    
    def __get_SatToGroundPLR(self, _cumulativeData: 'DataFrame') -> 'float':
        """
        @desc
            This method calculates the number of packets that were received by the satellite but not received by the groundstation
        @param[in] _cumulativeData
            The dataframe containing the data produced
        @return
            The PLR from 0 to 1
        """
        _numPacketsReceivedBySat = len(_cumulativeData[_cumulativeData['satReceivedNodeID'].notnull()].index)
        _numPacketsReceivedByGS = len(_cumulativeData[_cumulativeData['gsReceivedNodeID'].notnull()].index)
        return (_numPacketsReceivedBySat - _numPacketsReceivedByGS) / _numPacketsReceivedBySat
    
    def __get_EndToEndLatency(self, _cumulativeData: 'DataFrame') -> 'float':
        """
        @desc
            This method calculates the end to end latency
        @param[in] _cumulativeData
            The dataframe containing the data produced
        @return
            The latency in seconds
        """
        #We need the time when the packet was generated and the time when it was received by the groundstation        
        _latency = _cumulativeData['firstGSReceivedTime'] - _cumulativeData['generatedTime']
        #Let's drop the rows where the packet was not received by the groundstation
        _latency = _latency.dropna()
        _mean = _latency.mean()
        return _mean.total_seconds()
    
    def __get_generatorToSatLatency(self, _cumulativeData: 'DataFrame') -> 'float':
        """
        @desc
            This method calculates the latency between the generation of the packet and its reception by the satellite
        @param[in] _cumulativeData
            The dataframe containing the data produced
        @return
            The latency in seconds
        """
        #same as __get_EndToEndLatency but we need to use the firstSatReceivedTime
        _latency = _cumulativeData['firstSatReceivedTime'] - _cumulativeData['generatedTime']
        _latency = _latency.dropna()
        _mean = _latency.mean()
        return _mean.total_seconds()
    
    def __get_SatToGSLatency(self, _cumulativeData: 'DataFrame') -> 'float':
        #same as __get_EndToEndLatency but we need to use the firstGSReceivedTime and the firstSatReceivedTime
        _latency = _cumulativeData['firstGSReceivedTime'] - _cumulativeData['firstSatReceivedTime']
        _latency = _latency.dropna()
        _mean = _latency.mean()
        return _mean.total_seconds()

    def Execute(self):
        """
        This method executes the tasks that needed to be performed by the summarizer.
        """
        #Let's combine the outputs of the SMAs into a single dataframe
        _cumulativeData = self.__get_CumulativeData()
        
        #Now, let's actually calculate the metrics
        self.__results = {}
        
        _endToEndPLR = self.__get_EndToEndPLR(_cumulativeData)
        _generatorToSatPLR = self.__get_generatorToSatPLR(_cumulativeData)
        _satToGroundPLR = self.__get_SatToGroundPLR(_cumulativeData)
        _endToEndLatency = self.__get_EndToEndLatency(_cumulativeData)
        _generatorToSatLatency = self.__get_generatorToSatLatency(_cumulativeData)
        _satToGSLatency = self.__get_SatToGSLatency(_cumulativeData)
        
        _totalTime = (_cumulativeData['generatedTime'].max() - _cumulativeData['generatedTime'].min()).total_seconds()
        #_generationRate is the number of packets generated per second
        _generationRate = len(_cumulativeData.index) / _totalTime
        #_satelliteAggregationRate is the number of packets received by the satellite per second
        _satelliteAggregationRate = len(_cumulativeData[_cumulativeData['satReceivedNodeID'].notnull()].index) / _totalTime 
        #_gsAggregationRate is the number of packets received by the groundstation per second
        _gsAggregationRate = len(_cumulativeData[_cumulativeData['gsReceivedNodeID'].notnull()].index) / _totalTime
        
        self.__results['endToEndPLR'] = _endToEndPLR
        self.__results['generatorToSatPLR'] = _generatorToSatPLR
        self.__results['satToGroundPLR'] = _satToGroundPLR
        self.__results['endToEndLatency'] = _endToEndLatency
        self.__results['generatorToSatLatency'] = _generatorToSatLatency
        self.__results['satToGSLatency'] = _satToGSLatency
        self.__results['generationRate'] = _generationRate
        self.__results['satelliteAggregationRate'] = _satelliteAggregationRate
        self.__results['gsAggregationRate'] = _gsAggregationRate

    def get_Results(self) -> 'dict':
        '''
        @desc
            This method returns the results of the  in the form of a dictionary where the key is the name of the metric and the value is the results.
        @return
            The results of the summarizer in the form of a dictionary where the key is the name of the metric and the value is the results.
        '''
        return self.__results
    
    def __init__(self, 
        _generatorSMAs: 'list[iSMA]',
        _gsDataStoreSMAs: 'list[iSMA]',
        _satelliteDataStoreSMAs: 'list[iSMA]'):
        """
        @desc
            The constructor of the class
        @param[in] _generatorSMAOutputs
            The list of the outputs of the generator SMA(s)
        @param[in] _gsDataStoreSMAOutputs
            The list of the outputs of the gsDataStore SMA(s)
        @param[in] _satelliteDataStoreSMAOutputs
            The list of the outputs of the satelliteDataStore SMA(s). Can be an empty list if the satellite is generating data directly.
        """
        
        self.__generatorSMAs = _generatorSMAs
        self.__gsDataStoreSMAs = _gsDataStoreSMAs
        self.__satelliteDataStoreSMAs = _satelliteDataStoreSMAs
        self.__results = None
        
def init_SummarizerDataLayer(**kwargs):
    '''
    @desc
        Initializes the SummarizerDataLayer class
    @param[in] _kwargs
        Keyworded arguments that are passed to the constructor of the SMAPowerBasic class.
        It should have the following (key, value) pairs:
        @key _generatorSMAs
            The list of the generator SMA(s) which are producing the data. See smadatagenerator.py
        @key _gsDataStoreSMAs
            The list of the gsDataStore SMA(s) which are storing the data. See smadatastore.py
        @key _satelliteDataStoreSMAs
            The list of the satelliteDataStore SMA(s) which are storing the data. See smadatastore.py
    @return
        An instance of the SMAPowerBasic class
    '''
    _generatorSMAs = kwargs['_generatorSMAs']
    _gsDataStoreSMAs = kwargs['_gsDataStoreSMAs']
    _satelliteDataStoreSMAs = kwargs['_satelliteDataStoreSMAs']
    
    return SummarizerDataLayer(_generatorSMAs, _gsDataStoreSMAs, _satelliteDataStoreSMAs)