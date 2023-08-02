'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 1 Feb 2023
@desc
    This is a radio device which is managed by a communication model. 
    This device mantains two packet queues - transmission & reception.
    This assumes that a device can transmit and receive frames at the same time.
    However, it can only transmit one frame at a time. 
    It can receive one frame at a time and if there are multiple frames at the same time, it will receive none of them.
''' 
import random
import copy
from queue import Queue

from src.utils import Time
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger

from src.models.imodel import EModelTag
from src.models.network.radiodevice import RadioDevice
from src.models.network.address import Address
from src.models.network.channel import Channel

from src.models.network.lora.loralink import LoraLink
from src.models.network.lora.loraframe import LoraFrame


class LoraRadioDevice(RadioDevice):

    def __init__(
                self, 
                _address: Address, 
                _transmittable: bool, 
                _receivable: bool,
                _ownernode: 'INode', 
                _loggerins: ILogger,
                _radioPhySetup) -> None:
        """
        @desc
            Constructor of the class
        @param[in]  _address
            Unique address of the radio device
        @param[in]  _transmittable
            Whether the radio device can transmit
        @param[in]  _receivable
            Whether the radio device can receive
        @param[in]  _ownernode
            The node that owns this radio device
        @param[in]  _loggerins
            The logger instance
        @param[in]  _radioPhySetup
            The phy setup of the radio device. It should contain the following keys:
            @key _frequency
                Frequency of the radio device (in hertz)
            @key _bandwidth
                Bandwidth of the radio device (in hertz)
            @key _sf
                Spreading factor of the radio device
            @key _coding_rate
                Coding rate of the radio device
            @key _preamble
                Length of the preamble (in symbols)
            @key _tx_antenna_gain
                Gain of the antenna in transmission (in dBi)
            @key _tx_power
                Transmission power of the radio device (in dBW)
            @key _tx_line_loss
                Line loss of the radio device (in dB)
            @key _rx_antenna_gain
                Line loss of the radio device (in dB)
            @key _rx_line_loss
                Line loss of the radio device (in dB)
            @key _gain_to_temperature
                Gain to temperature of the radio device (in dB/K)
            @key _bits_allowed
                Number of bits allowed to be transmitted in a frame
        """
        
        self.__address = _address # unique address of the radio device
        self.__ownernode = _ownernode
        self.__transmittable = _transmittable # whether the radio device can transmit
        self.__receivable = _receivable # whether the radio device can receive
        self.__channels = []
        self.__transmittingTimes = []
        self.__temporaryReceivedFrames = []

        self.__rxQueue = Queue()

        self.__receiveCallBack = None
        
        self.__logger = _loggerins

        self.__radioPhySetup = _radioPhySetup.__dict__
        
        #Let's check if the phy setup is valid
        _neededKeys = ["_frequency", "_bandwidth", "_sf", "_coding_rate", 
                       "_preamble", "_tx_antenna_gain", "_tx_power",
                       "_tx_line_loss", "_rx_antenna_gain", "_rx_line_loss",
                       "_gain_to_temperature", "_bits_allowed"]
        
        for _key in _neededKeys:
            if _key not in self.__radioPhySetup:
                raise Exception("The radio phy setup for {} is missing the key: {}".format(self.__address, _key))
        
    def stop_Receiving(self) -> None:
        self.__receivable = False
    
    def start_Receiving(self) -> None:
        self.__receivable = True

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
        return True
    
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
        return 255
    
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
        return False #This radio device is always ready to receive a packet 
    
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
        _frame = LoraFrame(
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
            #We only should have one channel
            assert len(self.__channels) == 1
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
                    _link = LoraLink(self, _destinationDevice, _distance)
                    
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
                    _per = _link.get_PERFromBER(self.get_PhySetup()["_bits_allowed"], _transmitFrame.size)
                    _transmitFrame.set_PLR(_plr)
                    _transmitFrame.set_PER(_per)
                    
                    _transmitFrame.set_CR(self.get_PhySetup()["_coding_rate"])
                    _transmitFrame.set_BW(self.get_PhySetup()["_bandwidth"])
                    
                    #Only for LoRa:
                    _transmitFrame.set_SF(self.get_PhySetup()["_sf"])
                    
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
        
        #If we are transmitting, we need to burn the energy. 
        #We need to do here in the radio because here is the only one that knows how long it takes to transmit
        if _ret:
            _powerModel = self.__ownernode.has_ModelWithTag(EModelTag.POWER)
            if _powerModel is not None:
                _powerModel.call_APIs("consume_Energy", _tag="TXRADIO", _duration=max(_loggerInfo['secondsToTransmits']))
                
        #Let's log the frame
        _loggerString = "Transmitting. " + "".join([f"{_key}: {_value}. " for _key, _value in _loggerInfo.items()])
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
        
        #The frame can only be received if the radio is the same CR, BW
        #The frequency check should be done when the channel is created
        #These won't cause a collision with other frames of the correct CR and BW
        if _frame.get_BW() != self.get_PhySetup()["_bandwidth"] or _frame.get_SF() != self.get_PhySetup()["_sf"]:
            self.__log_Rx(_frame, _crbwDrop = True)
            return False
        
        #Before we add the frame to the temporary received frames, let's check if it drops due to PLR
        _plrDrop = random.random() < _frame.get_PLR()
        if _plrDrop:
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
        """
        #let's process all the timesteps
        _currentTime = self.__ownernode.timestamp
        
        #let's loop through the temporary received frames and check if there is any collision
        _framesIndex = 0
        while _framesIndex < len(self.__temporaryReceivedFrames): #while loop since list size may change
            _currFrame: LoraFrame = self.__temporaryReceivedFrames[_framesIndex]
            
            #if the packet has fully transmitted, we can now process it
            if _currFrame.get_endReceptionTime() <= _currentTime:
                #let's remove the frame from the list & compare it with others
                self.__temporaryReceivedFrames.remove(_currFrame)
                _framesIndex -= 1
                
                #Let's check if there is a collision. Let's loop through the temporary received frames and check if there is any overlapping times
                #For our logic, see: https://wiki.surfnet.nl/download/attachments/11211020/TUD-LoRaWAN-RoN-2017.pdf
                for _otherFrame in self.__temporaryReceivedFrames:
                    #first check if there is any overlap between (start, end) and (start, end)
                    _currStart = _currFrame.get_startReceptionTime()
                    _currEnd = _currFrame.get_endReceptionTime()
                    
                    _otherStart = _otherFrame.get_startReceptionTime()
                    _otherEnd = _otherFrame.get_endReceptionTime()
                    #This packet should either be fully after or fully before the other packet
                    _timeOverlap = not (_currStart >= _otherEnd or _currEnd <= _otherStart)
                    if _timeOverlap:                     
                        #Let's first check if there is more than 6dB stronger signal.
                        _rssiDiff = abs(_currFrame.get_RSSI() - _otherFrame.get_RSSI())
                        if _rssiDiff < 6:
                            #Here both frames are within 6dB of each other. So, both frames will be dropped    
                            _otherFrame.add_collidedID(_currFrame.id)
                            _currFrame.add_collidedID(_otherFrame.id)
                        else:
                            #Let's find the stronger/weaker frame
                            _strongerFrame = _currFrame if _currFrame.get_RSSI() > _otherFrame.get_RSSI() else _otherFrame
                            _weakerFrame = _currFrame if _currFrame.get_RSSI() < _otherFrame.get_RSSI() else _otherFrame

                            #Now, we need to check if the receiver has already locked on to a frame
                            #let's first check if the stronger frame was transmitted first. If so, the weaker frame will 100% be dropped
                            _strongerFrameFirst = _strongerFrame.get_startReceptionTime() < _weakerFrame.get_startReceptionTime()
                            if _strongerFrameFirst:
                                #The stronger frame was received first. So, the weaker frame will be dropped
                                _weakerFrame.add_collidedID(_strongerFrame.id)
                            else:
                                #The weaker frame was received first. If the receiver has locked on to the weaker frame, both frames will be dropped
                                #If the receiver has not locked on to the weaker frame, the weaker frame will be dropped and the receiver will lock on to the stronger frame
                                
                                #Let's find out low long it takes for the receiver to lock on to the frame
                                _symbolTime = (2**_currFrame.get_SF()) / _currFrame.get_BW()
                                _timeToLockInSeconds = _symbolTime * 4 
                                
                                _timeDiff = Time.difference_in_seconds(_weakerFrame.get_startReceptionTime(), _strongerFrame.get_startReceptionTime())
                                if _timeDiff > _timeToLockInSeconds:
                                    #The weaker frame was locked on. So both frames will be dropped
                                    _weakerFrame.add_collidedID(_strongerFrame.id)
                                    _strongerFrame.add_collidedID(_weakerFrame.id)
                                else:
                                    #The weaker frame was not locked. The weaker frame will be dropped
                                    _weakerFrame.add_collidedID(_strongerFrame.id) 
                            
                #Let's check if there was a collision
                if _currFrame.get_collidedIDs() != []:
                    self.__log_Rx(_currFrame, _collisions = _currFrame.get_collidedIDs())
                    _framesIndex += 1
                    continue #We don't need to process this frame any further
                
                #Now, let's check if there was a frame drop as the device is half duplex
                _frameDrop = False
                #let's check if the frame is being received as it is being transmitted
                for _transmitSet in self.__transmittingTimes:
                    _currStart = _currFrame.get_startReceptionTime()
                    _currEnd = _currFrame.get_endReceptionTime()
                    _otherStart = _transmitSet[0]
                    _otherEnd = _transmitSet[1]
                    
                    _timeOverlap = (_currStart <= _otherStart and _otherStart < _currEnd) or (_currStart < _otherEnd and _otherEnd <= _currEnd)
                    if _timeOverlap:
                        _frameDrop = True
                        self.__log_Rx(_currFrame, _txBusyDrop = True)
                        break
                
                #Let's also check if the coding rate matches
                _crMatches = _currFrame.get_CR() == self.get_PhySetup()["_coding_rate"]
                if not _crMatches:
                    self.__log_Rx(_currFrame, _crbwDrop = True)
                elif not _frameDrop:
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
    
    def __log_Rx(self, _frame: LoraFrame, **_kwargs):
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
                If the frame is dropped due to the coding rate or bw not matching (True/False)
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
    