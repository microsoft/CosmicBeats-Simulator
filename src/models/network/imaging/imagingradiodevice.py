'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 25 July 2023
@desc
    This is a radio device that models an imaging satellite's and ground station's radio.
    Both the satellite and the ground station have multiple physical channels.
''' 

from src.models.network.radiodevice import RadioDevice
from src.models.network.address import Address
from src.models.network.channel import Channel
from src.models.network.frame import Frame
from src.utils import Time
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from queue import Queue
import random

import copy
from src.models.network.imaging.imagingchannel import ImagingChannel
from src.models.network.imaging.imaginglink import ImagingLink

class ImagingRadioDevice(RadioDevice):
    def __init__(
                self, 
                _address: Address, 
                _transmittable: bool, 
                _receivable: bool,
                _ownernode: 'INode', 
                _loggerins: ILogger,
                _radioPhySetup) -> None:
        
        self.__address = _address # unique address of the radio device
        self.__ownernode = _ownernode
        self.__transmittable = _transmittable # whether the radio device can transmit
        self.__receivable = _receivable # whether the radio device can receive
        self.__channels = []
        self.__transmittingTimes = []
        self.__temporaryReceivedFrames = [] #List of frames that are received but not yet processed

        self.__rxQueue = Queue()

        self.__receiveCallBack = None
        
        self.__logger = _loggerins

        self.__radioPhySetup = _radioPhySetup.__dict__
        
    def get_OwnerNode(self) -> INode:
        '''
        @desc
            Get the the owner node of the radio
        @return
            Owner node object
        '''
        return self.__ownernode

    def get_Address(self):
        '''
        @desc
            Get the unique address of the radio device
        @return
            Address of the radio device
        '''
        return self.__address
    
    def set_Channels(self, _channels: 'list[Channel]') -> None:
        '''
        @desc
            Set the channels that this node part of
        @param[in]  _channels
            List of channels 
        '''
        self.__channels = _channels
    
    def get_Channels(self) -> 'list[Channel]':
        '''
        @desc
            Get the channels that this node part of
        @return
            List of channels 
        '''
        return self.__channels
    
    def is_P2P(self) -> bool:
        '''
        @desc
            Get to know whether it is a P2P channel
        @return
            True: If P2P
            False: Otherwise
        '''
        return False

    def is_Broadcast(self) -> bool:
        '''
        @desc
            Get to know whether it is a broadcast channel
        @return
            True: If broadcast
            False: Otherwise
        '''
        return False
    
    def is_Multicast(self) -> bool:
        '''
        @desc
            Get to know whether it is a multicast channel
        @return
            True: If Multicast
            False: Otherwise
        '''
        return False
    
    def is_LinkUp(self):
        '''
        @desc
            Get to know whether any link of the channel is up
        @return
            True: If any link is up
            False: Otherwise
        '''
        return self.__transmittable 

    def get_MTU(self) -> int:
        '''
        @desc
            Get maximum transmission unit (MTU) length in bytes.
        @return
            MTU in bytes
        '''
        return float('inf') #Let's make it infinity so that we can transmit larger packets. This drastically reduces the simulation time
        #return 64000 / 8
    
    def get_PhySetup(self) -> dict():
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

        return self.__radioPhySetup

    def is_TxBusy(self) -> bool:
        '''
        @desc
            Check whether the radio is already busy in transmitting packet
        @return
            True: If the radio is busy
            False: Otherwise
        '''
        _ret = False

        _currentTime = self.__ownernode.timestamp
        _index = 0
        while _index < len(self.__transmittingTimes):
            _transmitSet = self.__transmittingTimes[_index]
            if _transmitSet[0] <= _currentTime and _currentTime < _transmitSet[1]:
                _ret = True
            if _currentTime > _transmitSet[1]:
                # remove the old transmission records
                self.__transmittingTimes.pop(_index)
                continue
            _index = _index + 1
                
        return _ret
    
    def is_RxBusy(self) -> bool:
        '''
        @desc
            Check whether the radio is already busy in receiving packet
        @return
            True: If the radio is busy
            False: Otherwise
        '''
        #TODO: check this
        return False 
    
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
        _ret = False
        
        #Let's create a frame from the payload
        _frame = Frame(
                    source=self.__address, 
                    size= _payloadSize,
                    payloadString= _payload)
        _frame.instanceID = 0
        _instanceId = 1 #This is used to identify the instance of the frame
        
        #Let's create a dictionary to log the frame. We'll process this at the end of this method
        _loggerInfo = {
            'frameID': _frame.id, #This is the global frame ID
            'sourceAddress': str(self.get_Address()),  #This is the source address
            'frameSize': _frame.size,
            'payloadSize': _payloadSize,
            'mtuDrop': False, #If the frame is dropped due to MTU
            'busyDrop': False, #If the frame is dropped due to the radio being busy
            'noValidChannelDrop': False, #If the frame is dropped due to no valid channel
            'instanceIDs': [], #This is the instance ID of each copy of the frame that is transmitted
            'destinationNodeIDs': [], #This is the destination node ID of each copy of the frame that is transmitted
            'destinationRadioIDs': [], #This is the destination radio ID of each copy of the frame that is transmitted
            'snrs': [], #This is the SNR of each copy of the frame that is transmitted
            'secondsToTransmits': [], #This is the time it takes to transmit each copy of the frame
            'plrs': [], #This is the PLR of each copy of the frame
            'pers': [], #This is the PER of each copy of the frame
        }
        
        if _payloadSize > self.get_MTU():
            # bigger fame size than the MTU. Drop it. 
            _loggerInfo['mtuDrop'] = True
        elif self.is_TxBusy():
            #drop the frame. Because the radio is already transmitting a frame
            _loggerInfo['busyDrop'] = True    
        elif len(self.__channels) == 0:
            #drop the frame. Because there is no valid channel
            _loggerInfo['noValidChannelDrop'] = True
            _ret = False
        else:
            #We only should have two devices in the channel (this device and the other)
            assert len(self.__channels[_channelIndex].get_Devices()) == 2
            #Let's get the channel
            _destinationChannel = self.__channels[_channelIndex]
            # Transmit frame to all the devices in the channel
            for _destinationDevice in _destinationChannel.get_Devices():
                # make sure that the radio is not transmitting to itself
                if _destinationDevice.get_Address() != self.get_Address():
                    _currentTime = self.__ownernode.timestamp
                    # let's get the distance
                    _ourPosition = self.get_OwnerNode().get_Position(self.get_OwnerNode().timestamp)
                    _destinationNode = _destinationDevice.get_OwnerNode()
                    _destinationPosition = _destinationNode.get_Position(_currentTime)
                    _distance = _ourPosition.get_distance(_destinationPosition)
                    
                    #Get the link between the two devices
                    _link = ImagingLink(self, _destinationDevice, _distance)
                    
                    #Now, send the frame to the link. Send a copy of the frame as it might be modified
                    _transmitFrame = copy.deepcopy(_frame)
                    _transmitFrame.instanceID = _instanceId
                    _instanceId += 1

                    #let's find out how long it takes to transmit the frame                        
                    _secondsToTrasmit = _link.get_TimeOnAir(_transmitFrame.size)/1e3
                    
                    #now let's add the transmission time to the frame
                    _transmitFrame.set_startTransmissionTime(_currentTime.copy())
                    _transmitFrame.set_endTransmissionTime(_currentTime.copy().add_seconds(_secondsToTrasmit))

                    _propagationDelay = _link.get_PropagationDelay()

                    _transmitFrame.set_startReceptionTime(_currentTime.copy().add_seconds(_propagationDelay))
                    _transmitFrame.set_endReceptionTime(_currentTime.copy().add_seconds(_propagationDelay + _secondsToTrasmit))
                    
                    _plr = _link.get_PLR()
                    _per = _link.get_PERFromBER(0, _transmitFrame.size)
                    _transmitFrame.set_PLR(_plr)
                    _transmitFrame.set_PER(_per)
                    
                    _transmitFrame.set_BW(self.get_PhySetup()["_bandwidth"])
                    _transmitFrame.set_RSSI(_link.get_ReceivedSignalStrength())
                    
                    # Now, add this to the destination radio device
                    _destinationDevice.receive(_transmitFrame)

                    #now let's add the transmission time to the transmitting times
                    self.__transmittingTimes.append([_currentTime.copy(), _currentTime.copy().add_seconds(_secondsToTrasmit)])
                    
                    #Let's add the info to the logger
                    _loggerInfo['instanceIDs'].append(_transmitFrame.instanceID)
                    _loggerInfo['destinationNodeIDs'].append(_destinationNode.nodeID)
                    _loggerInfo['destinationRadioIDs'].append(int(str(_destinationDevice.get_Address())))
                    _loggerInfo['snrs'].append(_link.get_SNR())
                    _loggerInfo['secondsToTransmits'].append(_secondsToTrasmit)
                    _loggerInfo['plrs'].append(_plr)
                    _loggerInfo['pers'].append(_per)

                    _ret = True
        
        #Let's log the frame
        _loggerString = "Transmitting. " + ", ".join([f"{_key}: {_value}. " for _key, _value in _loggerInfo.items()])
        self.__logger.write_Log(_loggerString, ELogType.LOGINFO, self.__ownernode.timestamp, self.__class__.__name__)
            
        return _ret
    
    def receive(self, _frame, **kwargs) -> bool:
        '''
        @desc
            This is used to receive any frame from other radios
        @param[in]  _frame
             The frame to receive
        @return
            True: If the reception is successful
            False: Otherwise
        '''
        if not self.__receivable:
            self.__logger.write_Log("Frame {} not receiving due to radio not being receivable".format(_frame.id), \
                ELogType.LOGINFO, self.__ownernode.timestamp, self.__class__.__name__)
            return False
        
        #Let's also make sure that BW is the same
        #CR is adaptive, so we don't need to check that
        if _frame.get_BW() != self.get_PhySetup()["_bandwidth"]:
            self.__log_Rx(_frame, _crbwDrop = True)
            return False
        
        #Let's also evaluate the PLR
        if random.random() < _frame.get_PLR():
            self.__log_Rx(_frame, _plrDrop = True)
            return False
        
        self.__temporaryReceivedFrames.append(_frame)
        return True
    
    
    def update_Timestep(self):
        """
        @desc
            This method is called at the start of each timestep. 
            It processes all the frames that are received, checks if the transmission is complete and checks for collisions/drops
            If there is a successful reception, it will call the callback method
            This is based on the loraradiodevice method. See that method for more details
        """
        #let's process all the timesteps
        _currentTime = self.__ownernode.timestamp
        
        #let's loop through the temporary received frames and check if there is any collision
        _framesIndex = 0
        while _framesIndex < len(self.__temporaryReceivedFrames): #while loop since list size may change
            _currFrame: Frame = self.__temporaryReceivedFrames[_framesIndex]
            
            #if the packet has fully transmitted, we can now process it
            if _currFrame.get_endReceptionTime() <= _currentTime:
                #let's remove the frame from the list & compare it with others
                self.__temporaryReceivedFrames.remove(_currFrame)
                _framesIndex -= 1
                
                for _otherFrame in self.__temporaryReceivedFrames:
                    #first check if there is any overlap between (start, end) and (start, end)
                    _currStart = _currFrame.get_startReceptionTime()
                    _currEnd = _currFrame.get_endReceptionTime()
                    
                    _otherStart = _otherFrame.get_startReceptionTime()
                    _otherEnd = _otherFrame.get_endReceptionTime()

                    #This packet should either be fully after or fully before the other packet
                    _timeOverlap = not (_currStart >= _otherEnd or _currEnd <= _otherStart or (_currStart == _otherStart and _currEnd == _otherEnd))
                    if _timeOverlap:
                        #In this case, regardless of the RSSI, both packets will be marked as collided
                        _otherFrame.add_collidedID(_currFrame.id)
                        _currFrame.add_collidedID(_otherFrame.id)
                            
                #Let's check if there was a collision
                if len(_currFrame.get_collidedIDs()) >= 1:
                    self.__log_Rx(_currFrame, _collisions = _currFrame.get_collidedIDs())
                else:
                    #we have a successful reception 
                    #check if the packet should be dropped due to PER
                    #We already checked the PLR in the receive method. 
                    _perDrop = random.random() < _currFrame.get_PER()
                    _drop = _perDrop
                    if not _drop:
                        self.__log_Rx(_currFrame, _success = True)
                        if self.__receiveCallBack is not None:
                            self.__receiveCallBack(_packet = _currFrame.payloadString)
                        else:
                            self.__rxQueue.put(_currFrame.payloadString)
                    else:
                        self.__log_Rx(_currFrame, _perDrop = _perDrop)
            _framesIndex += 1
 
         #If we don't have any receiving frames that start before the last transmission ends, we can remove the transmission 
        _idx = 0
        if len(self.__temporaryReceivedFrames) > 0:        
            _earliestReception = min(self.__temporaryReceivedFrames[i].get_startReceptionTime() for i in range(len(self.__temporaryReceivedFrames)))
            _earliestReception = max(_earliestReception, _currentTime) #We don't want to remove the transmission if it's still going on
        else:
            _earliestReception = _currentTime
        while _idx < len(self.__transmittingTimes):
            _transmitSet = self.__transmittingTimes[_idx]
            if _transmitSet[1] <= _earliestReception:
                self.__transmittingTimes.remove(_transmitSet)
                _idx -= 1
            _idx += 1   

    def __log_Rx(self, _frame: Frame, **_kwargs):
        """
        @desc
            This method logs the received frames and if they are successfully received or not
        @param[in]  _frame
            The frame to be logged
        @param[in]  _kwargs
            The keyword arguments. It can contain any of the following keys. 
            @key _success
                If the frame is successfully received (True/False)
            @key _collisions
                List of frame IDs that collided with this frame
            @key _plrDrop
                If the frame is dropped due to PLR (True/False)
            @key _perDrop
                If the frame is dropped due to PER (True/False)
            @key _txBusyDrop
                If the frame is dropped due to the radio being busy (half duplex) (True/False)
            @key _crbwDrop
                If the frame is dropped due to the coding rate not matching (True/False)
        """
        #Let's get the keyword arguments
        _success = _kwargs["_success"] if "_success" in _kwargs else False
        _collisions = _kwargs["_collisions"] if "_collisions" in _kwargs else []
        _plrDrop = _kwargs["_plrDrop"] if "_plrDrop" in _kwargs else False
        _perDrop = _kwargs["_perDrop"] if "_perDrop" in _kwargs else False
        _txBusyDrop = _kwargs["_txBusyDrop"] if "_txBusyDrop" in _kwargs else False
        _crbwDrop = _kwargs["_crbwDrop"] if "_crbwDrop" in _kwargs else False
        
        #Setup another dictionary. See the send method for the other keys
        _loggerInfo = {
            'frameID': _frame.id, #This is the global frame ID
            'success': _success, #If the frame is successfully received
            'collision': True if len(_collisions) > 0 else False, #If the frame collided with any other frame
            'collisionFrameIDs': _collisions, #This is the list of frame IDs that collided with this frame
            'plrDrop': _plrDrop, #If the frame is dropped due to PLR
            'perDrop': _perDrop, #If the frame is dropped due to PER
            'txBusyDrop': _txBusyDrop, #If the frame is dropped due to the radio being busy (half duplex)
            'crbwDrop': _crbwDrop #If the frame is dropped due to the coding rate not matching
        }
        
        _loggerString = "Receiving. " + "".join([f"{_key}: {_value}. " for _key, _value in _loggerInfo.items()])
        self.__logger.write_Log(_loggerString, ELogType.LOGINFO, self.__ownernode.timestamp, self.__class__.__name__)

    def set_ReceiveCallBack(self, _cbMethod):
        '''
        @desc
            This methods sets a receive callback for the packet reception event
        @param[in]  _cbMethod
            Method to be call backed
        '''
        self.__receiveCallBack = _cbMethod
    