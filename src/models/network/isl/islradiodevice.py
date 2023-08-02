'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 22 May 2023
@desc
    This is a radio device which is managed by a communication model. 
    This device mantains two packet queues - transmission & reception.
    This assumes that a device can transmit and receive frames at the same time.
    However, it can only transmit one frame at a time. 
    It can receive one frame at a time and if there are multiple frames at the same time, it will receive none of them.
''' 

from src.models.network.radiodevice import RadioDevice
from src.models.network.address import Address
from src.models.network.channel import Channel
from src.models.network.frame import Frame
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from queue import Queue
import random

from src.models.network.isl.isllink import ISLLink

class ISLRadioDevice(RadioDevice):
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
        self.__temporaryReceivedFrames = []

        self.__rxQueue = Queue()

        self.__receiveCallBack = None
        
        self.__logger = _loggerins

        self.__radioPhySetup = _radioPhySetup
        
        #let's check that the radioPhySetup is valid. Should contain MTU, datarate, and BER
        if not self.__radioPhySetup and not self.__radioPhySetup.get('MTU') and not self.__radioPhySetup.get('datarate') and not self.__radioPhySetup.get('BER'):
            self.__logger.log(ELogType.ERROR, "RadioPhySetup is not valid")
            raise Exception("RadioPhySetup is not valid")
        

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
        return self.__radioPhySetup.MTU
    
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

        return self.__radioPhySetup.__dict__

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

        if _payloadSize > self.get_MTU():
            # bigger fame size than the MTU. Drop it. 
            self.__logger.write_Log("ISLRadioDevice dropping the frame as packet is bigger than MTU", ELogType.LOGINFO, self.__ownernode.timestamp)
            return False
        
        if self.is_TxBusy():
            #drop the frame. Because the radio is already transmitting a frame
            self.__logger.write_Log("ISLRadioDevice dropping the frame as the radio is busy in transmission", ELogType.LOGINFO, self.__ownernode.timestamp)
        else:
            #let's first try to find the channel that has the destination address
            _destinationChannel = self.__channels[_channelIndex]
            _destinationDevice: ISLRadioDevice = None

            if _destinationChannel is None:
                _ret = False
            else:
                # Transmit frame to all the devices in the channel
                for _destinationDevice in _destinationChannel.get_Devices():
                    # make sure that the radio is not transmitting to itself
                    if _destinationDevice.get_Address() != self.get_Address():
                        self.__logger.write_Log("ISLRadioDevice sending to " + str(_destinationDevice.get_OwnerNode().iName) + " from " + str(self.get_OwnerNode().iName), ELogType.LOGINFO, self.__ownernode.timestamp)
                        
                        _currentTime = self.__ownernode.timestamp
                        # let's get the distance
                        _pos1 = self.get_OwnerNode().get_Position(self.get_OwnerNode().timestamp)
                        _pos2 = _destinationDevice.get_OwnerNode().get_Position(_currentTime)
                        _distance = _pos1.get_distance(_pos2)
                        
                        #Get the link between the two devices
                        _link = ISLLink(self, _destinationDevice, _distance)
                        
                        # create frame 
                        _frame = Frame(
                                    source=self.__address, 
                                    size= _payloadSize,
                                    payloadString= _payload)

                        #let's find out how long it takes to transmit the frame                        
                        _secondsToTrasmit = _link.get_TimeOnAir(_frame.size)/1e3
                        
                        #now let's add the transmission time to the frame
                        _time = self.__ownernode.timestamp
                        _frame.set_startTransmissionTime(_time.copy())
                        _frame.set_endTransmissionTime(_time.copy().add_seconds(_secondsToTrasmit))

                        self.__logger.write_Log("Sending frame from {} to {} in {} seconds". \
                                                format(self.get_Address(), _destinationDevice.get_Address(), _secondsToTrasmit), \
                                                    ELogType.LOGINFO, self.__ownernode.timestamp)

                        _propagationDelay = _link.get_PropagationDelay()

                        _frame.set_startReceptionTime(_time.copy().add_seconds(_propagationDelay))
                        _frame.set_endReceptionTime(_time.copy().add_seconds(_propagationDelay + _secondsToTrasmit))
                        _frame.set_PLR(_link.get_PLR()) 
                        _frame.set_PER(_link.get_PERFromBER(self.get_PhySetup()["_bits_allowed"], _frame.size))
                        
                        # Now, add this to the destination radio device
                        _destinationDevice.receive(_frame)

                        #now let's add the transmission time to the transmitting times
                        self.__transmittingTimes.append([_time.copy(), _time.copy().add_seconds(_secondsToTrasmit)])

                        _ret = True
                
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
            return False
        self.__temporaryReceivedFrames.append(_frame)
        return True

    def update_Timestep(self):
        #let's process all the timesteps
        _currentTime = self.__ownernode.timestamp
        
        #let's loop through the temporary received frames and see if any of them has fully transmitted
        #no collsion detection is done here
        _idx = 0
        while _idx < len(self.__temporaryReceivedFrames): #while loop since list size may change
            _currFrame:Frame = self.__temporaryReceivedFrames[_idx]

            #if the packet has fully transmitted, we can now process it
            if _currFrame.get_endReceptionTime() <= _currentTime:
                #remove the frame from the temporary received frames
                self.__temporaryReceivedFrames.pop(_idx)
                
                #we have a successful reception 
                #let's add the frame to the received queue and call the callback
                self.__rxQueue.put(_currFrame)
                if self.__receiveCallBack is not None:
                    #check if the packet should be dropped
                    self.__logger.write_Log(f"Frame ID: {_currFrame.id}, PLR: {_currFrame.get_PLR()}, PER: {_currFrame.get_PER()} ", ELogType.LOGINFO, self.__ownernode.timestamp, self.__class__.__name__)
                    _plrDrop = random.random() < _currFrame.get_PLR() 
                    _perDrop = random.random() < _currFrame.get_PER()
                    _drop = _plrDrop or _perDrop
                    
                    if not _drop:
                        self.__logger.write_Log(f"Frame ID: {_currFrame.id} received successfully", ELogType.LOGINFO, \
                            self.__ownernode.timestamp, self.__class__.__name__)
                        self.__receiveCallBack(_packet = _currFrame.payloadString)
                    else:
                        self.__logger.write_Log("Frame ID: {_currFrame.id} dropped due to {} and {}".format("PLR" if _plrDrop else "", "PER" if _perDrop else ""), \
                            ELogType.LOGINFO, self.__ownernode.timestamp, self.__class__.__name__)
            _idx += 1

    def set_ReceiveCallBack(self, _cbMethod):
        '''
        @desc
            This methods sets a receive callback for the packet reception event
        @param[in]  _cbMethod
            Method to be call backed
        '''
        self.__receiveCallBack = _cbMethod
    