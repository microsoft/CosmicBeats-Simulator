"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 29 Sep 2022

This module includes the interface definition of the logger.
"""

from enum import Enum
from abc import ABC, abstractmethod
from src.utils import Time

class ELogType(Enum):
    '''
    An enum listing the types of log.
    Each log message should have one of these types
    '''
    LOGERROR = 0
    LOGWARN = 1
    LOGINFO = 2
    LOGDEBUG = 3
    LOGLOGIC = 4
    LOGALL = 5

class ILogger(ABC):
    '''
    This is an interface implementation of the logger. 
    '''
    @property
    @abstractmethod
    def logTypeLevel(self) -> ELogType:
        '''
        @type
            ELogType
        @desc
            Depending on the log type level of a logger it handles the log message type
            For example, if logTypeLevel = LOGERROR, it handles log messages of LOGERROR type 
        '''
        pass
    
    @abstractmethod
    def write_Log(
            self, 
            _message: str, 
            _logType: ELogType, 
            _timeStamp: Time,
            _modelName: str) -> bool:
        '''
        @desc
            This method writes log message passed in the argument
        @param[in]  _message
            Log message in string format
        @param[in]  _logType
            Type of the log message
        @param [in] _timeStamp
            Time stamp for the log message
        @param [in] _modelName
            Name of the instance that is writing the log message
        '''
        pass