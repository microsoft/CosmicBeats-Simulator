'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
Created by: Om Chabra
Created on: 11 Jul 2023
@desc
    This finds the end-to-end delay of data moving throughout the system.
'''
import sys
import os

#Let's add the path to the src folder so that we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.analytics.smas.smadatagenerator import init_SMADataGenerator
from src.analytics.smas.smadatastore import init_SMADataStore
from src.analytics.summarizers.summarizerdatalayer import init_SummarizerDataLayer

if __name__ == '__main__':
    _directoryOfLogs = sys.argv[1]
    
    #Let's get all the log files which are satellite logs
    _files = os.listdir(_directoryOfLogs)
    _iotFiles = [i for i in _files if i.split('_')[3] == 'IoT']
    _gsFiles = [i for i in _files if i.split('_')[3] == 'GS']
    _satFiles = [i for i in _files if i.split('_')[3] == 'SAT']
    
    #Now, let's setup the SMAs
    _iotSMAs = []
    for _iotFile in _iotFiles:
        _iotSMAs.append(init_SMADataGenerator(modelLogPath=os.path.join(_directoryOfLogs, _iotFile)))
    
    _gsSMAs = []
    for _gsFile in _gsFiles:
        _gsSMAs.append(init_SMADataStore(modelLogPath=os.path.join(_directoryOfLogs, _gsFile)))
    
    _satSMAs = []
    for _satFile in _satFiles:
        _satSMAs.append(init_SMADataStore(modelLogPath=os.path.join(_directoryOfLogs, _satFile)))
        
    #Now, let's run the SMAs.
    print("Running IoT SMAs")
    for _sma in _iotSMAs:
        _sma.Execute()
    print("Running GS SMAs")
    for _sma in _gsSMAs:
        _sma.Execute()
    print("Running SAT SMAs")
    for _sma in _satSMAs:
        _sma.Execute()

    _sumarizer = init_SummarizerDataLayer(_gsDataStoreSMAs = _gsSMAs, _generatorSMAs = _iotSMAs, _satelliteDataStoreSMAs=_satSMAs)
    print("Running Summarizer")
    _sumarizer.Execute()
    print("Results: ", _sumarizer.get_Results())