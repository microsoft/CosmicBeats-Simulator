'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 12 Oct 2022
@desc
    We conduct the unit test here for FileLogger class
'''

import unittest
import os
from src.simlogging.loggerfile import LoggerFile
from src.simlogging.ilogger import ELogType

class TestLoggerFile(unittest.TestCase):

    def setUp(self):
        self.__logger = LoggerFile(ELogType.LOGALL, "TestFileLogger", os.getcwd())

    def test_WriteLog(self):
        for i in range(1, 500):
            __result = self.__logger.write_Log("Test log", ELogType.LOGDEBUG)
            if(i%10 == 0):
                self.assertTrue(__result)
        
    def tearDown(self) -> None:
        _path = os.path.join(os.getcwd(), "Log_TestFileLogger.log")
        if os.path.isfile(_path):
            os.remove(_path)
        