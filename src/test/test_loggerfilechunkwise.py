'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 18 Jul 2023
@desc
    We conduct the unit test here for LoggerFileChunkWise class
'''

import unittest
import os
from src.simlogging.loggerfilechunkwise import LoggerFileChunkwise
from src.simlogging.ilogger import ELogType

class TestLoggerFile(unittest.TestCase):

    def setUp(self):
        self.__logger = LoggerFileChunkwise(ELogType.LOGALL, "TestFileLogger", os.getcwd(), 400)

    def test_WriteLog(self):
        for i in range(1, 500):
            __result = self.__logger.write_Log("Test log", ELogType.LOGDEBUG)
            if(i%10 == 0):
                # The max chunk size is 400 characters and each log message length is 40 characters. So, after 10 writes, the chunk should be dumped in the file.
                self.assertTrue(__result)
    
    def tearDown(self) -> None:
        _path = os.path.join(os.getcwd(), "Log_TestFileLogger.log")
        if os.path.isfile(_path):
            os.remove(_path)
        