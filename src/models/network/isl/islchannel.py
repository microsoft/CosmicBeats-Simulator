'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 22 May 2023
@desc
    This module implements the ISL channel class.
'''

from src.models.network.channel import Channel
from src.models.network.isl.islradiodevice import ISLRadioDevice
class ISLChannel(Channel):
    '''
    This class implements the ISL channel inheriting the base channel class 
    '''
    def __init__(self) -> None:
        super().__init__()
        self.__devices: 'list[ISLRadioDevice]' = []

    def add_Device(
                self, 
                _radio) -> bool:
        '''
        @desc
            Add the radio device to the channel
        @param[in]  _radio
            The radio device instance to add
        @return
            True: If the device has been added
            False: Otherwise
        '''
        self.__devices.append(_radio)
        
    def get_NumDevices(self) -> int:
        '''
        @desc
            Get the number of devices part of this channel
        @return
            Number of devices part of this channel
        '''
        return len(self.__devices)
    
    def get_Devices(self) -> list():
        '''
        @desc
            Get the list of radio devices that are part of this channel
        @return
            List of radio devices
        '''
        return self.__devices