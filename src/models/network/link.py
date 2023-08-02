'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 06 Jan 2023
@desc
    This module implements the base wireless link between two radio devices.
'''

from abc import ABC, abstractmethod
from src.models.network.radiodevice import RadioDevice

class Link(ABC):
    '''
    This class abstracts out the concept of wireless link between two radio devices.
    '''

    def get_Src(self) -> RadioDevice:
        '''
        @desc
            Get the source radio device of the link.
        @return
            Src radio device
        '''
        pass
    
    def get_Dstn(self) -> RadioDevice:
        '''
        @desc
            Get the destination radio device of the link.
        @return
            Src radio device
        '''
        pass

    def get_PropagationLoss(self) -> float:
        '''
        @desc
            Get the Propagation Loss of the link
        @return
            Propagation Loss
        '''
        pass
    
    def get_PropagationDelay(self) -> float:
        '''
        @desc
            Get the datarate of thr channel
        @return
            Data rate
        '''
        pass
    
    def get_TimeOnAir(
                    self, 
                    _frameLength: int)->float:
        '''
        @desc
            Calculates the time on air for frame given the modulation config setup and frame length.
        @param _frameLength
            Length of the frame in bytes
        @return
            Time on the air in msec
        '''
        pass