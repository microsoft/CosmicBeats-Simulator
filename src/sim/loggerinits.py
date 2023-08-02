'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 31 Oct 2022
@desc
    In this module, we list the initialization methods for different logger class implementations.
    Initialization method must be written in the same module as where class implementation is written. 
    The initialization method must be added in the dictionary below as the value against the key as the name of class
    The prototype of the initialization method goes below.
    
    init_LoggerFile(__loglevel : ELogType, __logGeneratorName : str, __simsetupDetails) -> ILogger:
    @desc
        This method initializes an instance of LoggerCmd class and returns
    @param[in]  __loglevel
        Depending on the log level of a logger it handles the log message type
        For example, if logLevel = LOGERROR, it handles log messages of LOGERROR type 
    @param[in]  __logGeneratorName
        Name of the log generator. It could be the name of the instance that generates the log message for this logger
    @param[in]  __simsetupDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
           give example of the literals that your initialization methods look for
        }
    @return
        Logger class instance
'''

from src.simlogging.ilogger import ELogType

# import the logger classes here
from src.simlogging.loggercmd import init_LoggerCmd
from src.simlogging.loggerfile import init_LoggerFile
from src.simlogging.loggerfilechunkwise import init_LoggerFileChunkwise


loggerInitDictionary = {
    "LoggerCmd" : init_LoggerCmd,
    "LoggerFile": init_LoggerFile,
    "LoggerFileChunkwise": init_LoggerFileChunkwise
    }

loggerTypeDictionary = {
    "error" : ELogType.LOGERROR,
    "warn"  : ELogType.LOGWARN,
    "debug" : ELogType.LOGDEBUG,
    "info"  : ELogType.LOGINFO,
    "logic" : ELogType.LOGLOGIC,
    "all"   : ELogType.LOGALL
}