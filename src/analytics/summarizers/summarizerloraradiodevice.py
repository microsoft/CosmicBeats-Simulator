'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 14 Jul 2023
@desc 
    This module processes the outputs of the two LoraRadioDevice SMAs and calculates the following metrics:

        1. numFramesDroppedMTU: Number of frames dropped due to MTU
        2. numFramesDroppedTxBusy: Number of frames dropped due to TX busy
        3. numFramesDroppedRX: Number of frames dropped due to RX busy
        4. numFramesCollided: Number of frames collided
        5. average/minimum/maximum PLRTX (Packet Loss Ratio TX) 
        6. average/minimum/maximum PERTX (Packet Error Rate TX)   
'''
from src.analytics.summarizers.isummarizers import ISummarizer
from pandas import DataFrame
import pandas as pd

class SummarizerLoraRadioDevice(ISummarizer):
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
        return ['SMALoraRadioDeviceRx', 'SMALoraRadioDeviceTx']

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
        self.__results = {}
        
        _txResults = self.__txSMA.get_Results()
        #_txResults columns are frameId,sourceAddress,frameSize,payloadSize,mtuDrop,busyDrop,noValidChannelDrop,instanceIDs,
        #destinationNodeIDs,destinationRadioIDs,snrs,secondsToTransmits,plrs,pers,timestamp,nodeID
        self.__results['numFramesDroppedMTU'] = _txResults['mtuDrop'].sum()
        self.__results['numFramesDroppedTxBusy'] = _txResults['busyDrop'].sum()
        
        #_txResults['plrs'] is a list of lists. We need to explode it to get a list of all the plrs
        _allPLRs = _txResults['plrs'].explode() 
        self.__results['avgPLRTX'] = _allPLRs.mean()
        self.__results['minPLRTX'] = _allPLRs.min()
        self.__results['maxPLRTX'] = _allPLRs.max()
        
        _allPERs = _txResults['pers'].explode()
        self.__results['avgPERTX'] = _allPERs.mean()
        self.__results['minPERTX'] = _allPERs.min()
        self.__results['maxPERTX'] = _allPERs.max()
        
        #frameID, collision, collisionFrameIDs, plrDrop. perDrop, txBusyDrop, crbwDrop, nodeID, timestamp
        _rxResults = self.__rxSMA.get_Results()
        self.__results['numFramesDroppedRX'] = _rxResults['plrDrop'].sum() + _rxResults['perDrop'].sum() + _rxResults['txBusyDrop'].sum()
        self.__results['numFramesCollided'] = _rxResults['collision'].sum()
        
        _totalNumFrames = _rxResults['frameID'].count()
        self.__results['PLRRX'] = _rxResults['plrDrop'].sum() / _totalNumFrames 
        self.__results['PERRX'] = _rxResults['perDrop'].sum() / _totalNumFrames
        
    def get_Results(self) -> 'dict':
        '''
        @desc
            This method returns the results of the  in the form of a dictionary where the key is the name of the metric and the value is the results.
        @return
            The results of the summarizer in the form of a dictionary where the key is the name of the metric and the value is the results.
        '''
        return self.__results
    
    def __init__(self, 
        _rxSMA: 'iSMA',
        _txSMA: 'iSMA'):
        """
        @desc
            The constructor of the class
        @param[in] _rxSMA
            The LoraRadioDeviceRx SMA(s)
        @param[in] _txSMA
            The LoraRadioDeviceTx SMA(s)
        """
        self.__rxSMA = _rxSMA
        self.__txSMA = _txSMA
        self.__results = None
        
def init_SummarizerLoraRadioDevice(**kwargs):
    '''
    @desc
        Initializes the init_SummarizerLoraRadioDevice class
    @param[in] _kwargs
        Keyworded arguments that are passed to the constructor of the init_SummarizerLoraRadioDevice class.
        It should have the following (key, value) pairs:
        @key _rxSMA
            The LoraRadioDeviceRx SMA which are storing the data. See smaloraradiodevicerx.py
        @key _txSMA
            The LoraRadioDeviceTx SMA which are storing the data. See smaloraradiodevicetx.py    
    @return
        An instance of the init_SummarizerLoraRadioDevice class
    '''
    _rxSMA = kwargs['_rxSMA']
    _txSMA = kwargs['_txSMA']
    
    return SummarizerLoraRadioDevice(_rxSMA, _txSMA)