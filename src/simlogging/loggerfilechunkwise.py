"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 17 July 2023

This module implements a logger that uses a separate file for each instance creator to dump its log.
The log is dumped in chunks, i.e., the log is dumped in the file only when the log size reaches a certain limit.   
"""

from src.simlogging.ilogger import ELogType, ILogger # for logger interface
from src.utils import Time # for time stamp
import os # for file operations
import shutil # for file operations
import atexit

try:
    from cStringIO import StringIO
except:
    from io import StringIO

class LoggerFileChunkwise(ILogger):
   '''
    This class inherits the ILogger interface.
    It writes the log in a dedicated file for each instance.
    It dumps the log in chunks, i.e., the log is dumped in the file only when the log size reaches a certain limit.
   '''
   __fileExtension = '.log'
   __filePath: str
   __logTypeLevel: ELogType
   __currentChunkSize: int #in characters
   __maxChunkSize: int #in characters
   __currentLogChunkBuffer: StringIO # string buffer to store the log chunk
   
   __overwritePermission: bool = False # whether all the log files can be overwritten without asking the user
   
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
        #check whether the log type of the message can be handled by this logger instance
        if (self.__logTypeLevel == ELogType.LOGALL or self.__logTypeLevel == _logType or
            self.__logTypeLevel.value >= _logType.value):
            
            if "\"" in _message:
                raise Exception("[Simulator Exception] Log message can't contain double quote (\") character. Write the log message without double quote.")
            
            # add the log message to the current log chunk using string IO
            _logmessage = "".join(["[", _logType.__str__(), "]", ", ",
                            (_timeStamp.to_str() if _timeStamp is not None else "NTA"), ", ", 
                            (_modelName if _modelName is not None else "NMA"), ", \"",
                            _message , "\"\n"])
                                               
            self.__currentLogChunkBuffer.write(_logmessage)
            # check whether the current log chunk size has reached the maximum chunk size
            self.__currentChunkSize = self.__currentLogChunkBuffer.tell()

            if(self.__currentChunkSize >= self.__maxChunkSize):
                # dump the current log chunk in the file
                try:
                    with open(self.__filePath, "a") as _file:
                        self.__currentLogChunkBuffer.seek(0)
                        shutil.copyfileobj(self.__currentLogChunkBuffer, _file, -1)
                        _ret = True
                    # _file = open(self.__filePath, "a")
                    # _file.write(self.__currentLogChunkBuffer.getvalue())
                    # _file.close()
                    # _ret = True
                except:
                    raise Exception(f"[Simulator Exception] Couldn't open the log file at {self.__filePath}") 
                
                # reset the current log chunk buffer
                self.__currentLogChunkBuffer = StringIO()
                self.__currentChunkSize = 0 
        
        return _ret
   
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
   
   def closing(self):
        '''
        @desc
            Destructor of the class.
            It dumps the current log chunk in the file before the instance is destroyed
        '''
        try:
            if(self.__currentChunkSize > 0):
                with open(self.__filePath, "a") as _file:
                        self.__currentLogChunkBuffer.seek(0)
                        shutil.copyfileobj(self.__currentLogChunkBuffer, _file, -1)
        except Exception as e:
            raise Exception(f"[Simulator Exception] Couldn't open the log file at {self.__filePath}: " + str(e))
   
   def __init__(
        self, 
        _logLevel: ELogType, 
        _logGeneratorName: str, 
        _logDir: str,
        _logChunkSize) -> None:
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
        @param[in]  _logChunkSize
            Size of the log chunk in bytes
        '''        
        self.__logTypeLevel = _logLevel
        self.__maxChunkSize = _logChunkSize
        self.__currentChunkSize = 0
        self.__currentLogChunkBuffer = StringIO()
        
        self.__filePath = _logDir + "/" + "Log_" + _logGeneratorName + self.__fileExtension
        
        # check whether the log directory exists. If not, create one
        if(not os.path.isdir(_logDir)):
            os.mkdir(_logDir)               # let it throw exception if it can't create the directory 

        # create the file
        try:
            __file = open (self.__filePath, "w")
            __file.write("logType, timestamp, modelName, message\n")
            __file.close()
        except:
            raise Exception("[Simulator Exception] Couldn't create the log file.") 
        
        #Setup close at exit
        atexit.register(self.closing)

def init_LoggerFileChunkwise(
        _loglevel: ELogType, 
        _logGeneratorName: str, 
        _logSetupDetails) -> ILogger:
    '''
    @desc
        This method initializes an instance of LoggerFileChunkwise class and returns
    @param[in]  _loglevel
        Depending on the log level of a logger it handles the log message type
        For example, if logLevel = LOGERROR, it handles log messages of LOGERROR type 
    @param[in]  _logGeneratorName
        Name of the log generator. It could be the name of the instance that generates the log message for this logger
    @param[in]  _logSetupDetails
        It's a converted JSON object containing the logging setup related related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "logfolder": "C:\\spacesim\logs",
            "logcunksize": 1024
        }
        where
        @logfolder
            Path to the directory where the log will be saved
        @logchunksize
            Size of the log chunk in characters
    '''
    assert _loglevel is not None
    assert _logGeneratorName != ""

    #check whether the log setup details are valid
    assert _logSetupDetails is not None
    assert _logSetupDetails.logfolder != ""
    assert _logSetupDetails.logchunksize > 0

    return LoggerFileChunkwise(
                _loglevel, 
                _logGeneratorName, 
                _logSetupDetails.logfolder,
                _logSetupDetails.logchunksize)


           
    
        


        


