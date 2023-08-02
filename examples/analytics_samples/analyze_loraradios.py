'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
Created by: Om Chabra
Created on: 11 Jul 2023
@desc
    This finds out how many collisions among other things that are happening in the satelite's radio
'''
import sys
import os

#Let's add the path to the src folder so that we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..')) 

from src.analytics.smas.smaloraradiodevicerx import init_SMALoraRadioDeviceRx
from src.analytics.smas.smaloraradiodevicetx import init_SMALoraRadioDeviceTx
from src.analytics.summarizers.summarizerloraradiodevice import init_SummarizerLoraRadioDevice

if __name__ == '__main__':
    _directoryOfLogs = sys.argv[1]
    
    #Let's get all the log files which are satellite logs
    _files = os.listdir(_directoryOfLogs)
    _satFiles = [i for i in _files if i.split('_')[3] == 'SAT']
    
    #Now, let's setup the SMAs
    _txSmas = []
    _rxSMAs = []
    for _satFile in _satFiles:
        _fullPath = os.path.join(_directoryOfLogs, _satFile)
        _txSmas.append(init_SMALoraRadioDeviceTx(modelLogPath=_fullPath))
        _rxSMAs.append(init_SMALoraRadioDeviceRx(modelLogPath=_fullPath))
        
    #Now, let's run the SMAs.    
    for _sma in _txSmas:
        _sma.Execute()
    for _sma in _rxSMAs:
        _sma.Execute()
        
    #Now, let's setup the summarizers
    _satSummarizers = []
    for _sat in range(len(_satFiles)):
        _satSummarizers.append(init_SummarizerLoraRadioDevice(_txSMA = _txSmas[_sat], _rxSMA = _rxSMAs[_sat]))
    
    for _summarizer in _satSummarizers:
        _summarizer.Execute()
    
    _res = []
    for _summarizer in _satSummarizers:
        _res.append(_summarizer.get_Results())
    print("One sample satellite: ", _satFiles[0], " has output: ", _res[0])
    
    print("\nTotal collisions across all satellites: ", sum([i['numFramesCollided'] for i in _res]))

