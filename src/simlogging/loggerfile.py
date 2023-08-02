"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 30 Sep 2022

This module implements a logger that uses a separate file for each instance creator to dump its log
"""

from src.simlogging.ilogger import ELogType, ILogger
from src.utils import Time
import os

class LoggerFile(ILogger):
    '''
    This class inherits the ILogger interface.
    It writes the log in a dedicated file for each instance.
    '''
    __fileExtension = '.log'
    __filePath: str
    __logTypeLevel: ELogType
        
    def write_Log(
        self, 
        _message: str, 
        _logType: ELogType, 
        _timeStamp: Time = None,
        _modelName: str = None ) -> bool:
        '''
        @desc
            This method writes log message passed in the argument
        @param[in]  _message
            Log message in string format
        @param[in]  _logType
            Type of the log message
        @param [in] _timeStamp
            Time stamp for the log message
        @param[in]  _modelName
            Name of the model that generates the log message
        '''
        _ret = False
        
        #print(_message, _logType, _timeStamp, _modelName)
        #print(self.__logTypeLevel, _logType, self.__logTypeLevel.value, _logType.value, self.__logTypeLevel.value >= _logType.value)
        
        #check whether the log type of the message can be handled by this logger instance
        if (self.__logTypeLevel == ELogType.LOGALL or
            self.__logTypeLevel.value >= _logType.value):
            #check whether log directory exists
            if(os.path.isfile(self.__filePath)):
                try:
                     with open(self.__filePath, "a") as _file:

                        _logmessage = "".join(["[", _logType.__str__(), "]", ", ",
                                (_timeStamp.to_str() if _timeStamp is not None else "NTA"), ", ", 
                                (_modelName if _modelName is not None else "NMA"), ", \"",
                                _message , "\" \n"])
                        
                        _file.write(_logmessage)
                        
                        _ret = True

                except:
                    raise Exception(f"[Simulator Exception] Couldn't open the log file at {self.__filePath}") 
            else:
                raise Exception(f"[Simulator Exception] Couldn't find the log file at {self.__filePath}" ) 
        
        return _ret

    def __init__(
        self, 
        _logLevel: ELogType, 
        _logGeneratorName: str, 
        _logDir: str) -> None:
        '''
        @desc
            Constructor of the class.
        @param[in]  _logLevel
            Depending on the log level of a logger it handles the log message type
            For example, if logLevel = LOGERROR, it handles log messages of LOGERROR type 
        @param[in]  _logGeneratorName
            Name of the log generator. It could be the name of the instance that generates the log message for this logger
        @param[in]  _logDir
            Path to the directory where the log will be saved
        '''
        self.__logTypeLevel = _logLevel
        self.__filePath = _logDir + "/" + "Log_" + _logGeneratorName + self.__fileExtension
        
        # check whether the log directory exists. If not, create one
        if(not os.path.isdir(_logDir)):
            os.mkdir(_logDir)               # let it throw exception if it can't create the directory 
            
        # create the file
        try:
            __file = open (self.__filePath, "w")
            __file.write("logLevel, timestamp, modelName, message\n")
            __file.close()
        except:
            raise Exception("[Simulator Exception] Couldn't create the log file.") 
    
    @property
    def logTypeLevel(self) -> ELogType:
        '''
        @type
            ELogType
        @desc
            Depending on the log type level of a logger it handles the log message type
            For example, if logTypeLevel = LOGERROR, it handles log messages of LOGERROR type 
        '''
        return self.__logTypeLevel

def init_LoggerFile(
        _loglevel: ELogType, 
        _logGeneratorName: str, 
        _simsetupDetails) -> ILogger:
    '''
    @desc
        This method initializes an instance of LoggerCmd class and returns
    @param[in]  _loglevel
        Depending on the log level of a logger it handles the log message type
        For example, if logLevel = LOGERROR, it handles log messages of LOGERROR type 
    @param[in]  _logGeneratorName
        Name of the log generator. It could be the name of the instance that generates the log message for this logger
    @param[in]  _simsetupDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "logfolder": "C:\\spacesim\logs"
        }
    '''
    assert _loglevel is not None
    assert _logGeneratorName != ""
    assert _simsetupDetails is not None
    assert _simsetupDetails.logfolder != ""

    return LoggerFile(
                _loglevel, 
                _logGeneratorName, 
                _simsetupDetails.logfolder)


           
    
        


        


