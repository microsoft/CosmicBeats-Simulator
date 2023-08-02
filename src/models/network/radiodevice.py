'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 06 Jan 2023
@desc
    This module implements the base network radio device.
'''

from abc import ABC, abstractmethod
from src.models.network.channel import Channel
from src.nodes.inode import INode

class RadioDevice(ABC):
    '''
    This class abstract out the base functionalities of a radio device.
    A radio device enables communication between nodes.
    '''
    @abstractmethod
    def get_OwnerNode(self) -> INode:
        '''
        @desc
            Get the the owner node of the radio
        @return
            Owner node object
        '''
        pass

    @abstractmethod
    def get_Address(self):
        '''
        @desc
            Get the unique address of the radio device
        @return
            Address of the radio device
        '''
        pass
    
    @abstractmethod
    def get_Channels(self) -> 'list[Channel]':
        '''
        @desc
            Get the channels that this node part of
        @return
            List of channels 
        '''
        pass
    
    @abstractmethod
    def is_P2P(self) -> bool:
        '''
        @desc
            Get to know whether it is a P2P channel
        @return
            True: If P2P
            False: Otherwise
        '''
        pass

    @abstractmethod
    def is_Broadcast(self) -> bool:
        '''
        @desc
            Get to know whether it is a broadcast channel
        @return
            True: If broadcast
            False: Otherwise
        '''
        pass
    
    @abstractmethod
    def is_Multicast(self) -> bool:
        '''
        @desc
            Get to know whether it is a multicast channel
        @return
            True: If Multicast
            False: Otherwise
        '''
        pass
    
    @abstractmethod
    def is_LinkUp(self):
        '''
        @desc
            Get to know whether any link of the channel is up
        @return
            True: If any link is up
            False: Otherwise
        '''
        pass
    
    @abstractmethod
    def get_MTU(self) -> int:
        '''
        @desc
            Get maximum transmission unit (MTU) length in bytes.
        @return
            MTU in bytes
        '''
        pass
    
    @abstractmethod
    def get_PhySetup(self) -> 'dict':
        '''
        @desc
            Get the phy layer setup of the radio device, e.g., antenna configuration, transmission power, frequency, bandwidth, and so on.
        @return
            A dictionary where key is the name of phy layer parameter.
            For example, 
            {
                "txpower": 20.0,
                "frequency": 470.0
            }
        '''
        pass

    @abstractmethod
    def is_TxBusy(self) -> bool:
        '''
        @desc
            Check whether the radio is already busy in transmitting packet
        @return
            True: If the radio is busy
            False: Otherwise
        '''
        pass
    
    @abstractmethod
    def is_RxBusy(self) -> bool:
        '''
        @desc
            Check whether the radio is already busy in receiving packet
        @return
            True: If the radio is busy
            False: Otherwise
        '''
        pass
    
    @abstractmethod
    def send(
            self, 
            _payloadSize: int,
            _payload: str, 
            _channelIndex: int) -> bool:
        '''
        @desc
            This method is used to transfer a frame from this radio device on a given channel
        @param[in]  _payloadSize
            Size of the paylod in bytes
        @param[in]  _payload
            The payload to be sent in the frame. If it's a object, serialize to string before passing it
        @param[in]  _channelIndex
            The index of the channel
        @return
            True: If the package transmission was successful 
            False: Otherwise
        '''
        pass

    @abstractmethod
    def receive(self, _frame) -> bool:
        '''
        @desc
            This is used to receive any frame from other radios
        @param[in]  _frame
             The frame to receive
        @return
            True: If the reception is successful
            False: Otherwise
        '''
        pass
    
    @abstractmethod
    def set_ReceiveCallBack(self, _cbMethod):
        '''
        @desc
            This methods sets a receive callback for the packet reception event
        @param[in]  _cbMethod
            Method to be call backed
        '''
        pass