"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 30 Sep 2022

This module implements a logger that uses python print function for logging
"""

from src.simlogging.ilogger import ELogType, ILogger
from src.utils import Time

class LoggerCmd(ILogger):
   '''
    This class inherits the ILogger interface.
    It writes the log in cmd interface.
   '''
   __loggeneratorname: str
   __logTypeLevel: ELogType

   def write_Log(
        self, 
        _message: str, 
        _logType: ELogType, 
        _timeStamp: Time = None,
        _modelName: str = None,) -> bool:
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
        #check whether the log type of the message can be handled by this logger instance
        if (self.__logTypeLevel == ELogType.LOGALL or 
            self.__logTypeLevel == _logType):
                _logMessage = "".join(["[", _logType.__str__(), "]", ", ",
                                self.__loggeneratorname, ", ",
                                (_timeStamp.to_str() if _timeStamp is not None else "NTA"), ", ", 
                                (_modelName if _modelName is not None else "NMA"), ": ",
                                _message , "\n"])
                print(_logMessage)
                _ret = True
        return _ret
   
   def __init__(
        self, 
        _logLevel: ELogType, 
        _logGeneratorName: str) -> None:
        '''
        @desc
            Constructor of the class.
        @param[in]  _logLevel
            Depending on the log level of a logger it handles the log message type
            For example, if logLevel = LOGERROR, it handles log messages of LOGERROR type 
        @param[in]  _logGeneratorName
            Name of the log generator. It could be the name of the instance that generates the log message for this logger
        '''
        self.__logTypeLevel = _logLevel
        self.__loggeneratorname = _logGeneratorName
   
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

def init_LoggerCmd(
        _loglevel: ELogType, 
        _logGeneratorName: str, 
        __simsetupDetails) -> ILogger:
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
            for this class no info is required
        }
    '''
    assert _loglevel is not None
    assert _logGeneratorName != ""

    return LoggerCmd(_loglevel, _logGeneratorName)

           
    
        


        


