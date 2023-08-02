'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 11 Jul 2023
@desc
    This finds the overall power consumption of the system.
'''
import sys
import os

#Let's add the path to the src folder so that we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..')) 

from src.analytics.smas.smapowerbasic import init_SMAPowerBasic
from src.analytics.summarizers.summarizerpower import init_SummarizerPower
from src.analytics.summarizers.summarizermultiplepower import init_SummarizerMultiplePower

if __name__ == '__main__':
    _directoryOfLogs = sys.argv[1]
    
    #Let's get all the log files which are satellite logs
    _files = os.listdir(_directoryOfLogs)
    _satFiles = [i for i in _files if i.split('_')[3] == 'SAT']
    
    #Now, let's setup the SMAs
    _satSMAs = []
    for _satFile in _satFiles:
        _fullPath = os.path.join(_directoryOfLogs, _satFile)
        _satSMAs.append(init_SMAPowerBasic(modelLogPath=_fullPath))
        
    #Now, let's run the SMAs.    
    for _sma in _satSMAs:
        _sma.Execute()
        
    #Now, let's setup the summarizers
    _satSummarizers = []
    for _sma in _satSMAs:
        _satSummarizers.append(init_SummarizerPower(_powerModelSMA = _sma))
        _satSummarizers[-1].Execute()
    
    #Now, let's print the results of one of the summarizers so we can see what the data looks like
    print("One Sample Satellite", _satFiles[0], " Has output: ",_satSummarizers[0].get_Results())
    
    #Now let's run the overall summarizer
    _overallSummarizer = init_SummarizerMultiplePower(_powerSummarizers = _satSummarizers)
    _overallSummarizer.Execute()
    print("\nOverall Results Across Satellites: ", _overallSummarizer.get_Results())
    

