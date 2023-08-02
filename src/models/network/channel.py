'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 06 Jan 2023
@desc
    This module implements the base network channel class.
'''

from abc import ABC, abstractmethod

class Channel(ABC):
    '''
    This class abstracts out the base functionalities of a network channel. 
    A radio device uses channel to communicate with other radio devices. 
    '''
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_NumDevices(self) -> int:
        '''
        @desc
            Get the number of devices part of this channel
        @return
            Number of devices part of this channel
        '''
        pass
    
    @abstractmethod
    def get_Devices(self) -> list:
        '''
        @desc
            Get the list of radio devices that are part of this channel
        @return
            List of radio devices
        '''
        pass