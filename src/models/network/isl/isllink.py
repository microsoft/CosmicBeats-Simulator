'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 22 May 2023
@desc
    This module implements the laser link between two sats.
'''
import math

from src.models.network.link import Link

class ISLLink(Link):
    def __init__(self, _src, _dstn, _distance):
        '''
        @desc
            Constructor
        @param
            _src: Source radio device
            _dstn: Destination radio device
            _distance: Distance between source and destination
        '''
        self.__src: 'LoraRadioDevice' = _src
        self.__dstn: 'LoraRadioDevice' = _dstn
        self.__distance: float = _distance
        
        self.__SNR = None #SNR - avoids recalculation

    def get_Src(self) -> 'RadioDevice':
        '''
        @desc
            Get the source radio device of the link.
        @return
            Src radio device
        '''
        return self.__src
    
    def get_Dstn(self) -> 'RadioDevice':
        '''
        @desc
            Get the destination radio device of the link.
        @return
            Src radio device
        '''
        return self.__dstn
    
    def get_BER(self):
        '''
        @desc
            Uses the table above to calculate the BER based on the SNR and SF
        @return
            BER from 0 to 1
        '''
        _ber = self.__src.get_PhySetup()['BER']
        return _ber
        
    def get_PropagationLoss(self) -> float:
        '''
        @desc
            Get the Propagation Loss of the link in dB
        @return
            Free space Propagation Loss in dB
        '''
        #We don't have a link model for ISL yet
        #Datarate is passed by the user
        return None

    def get_ReceivedSignalStrength(self) -> float:
        '''
        @desc
            This method calculates the received signal strength at the receiver based on 
            the Phy layer setups of transmitter and receiver. 
        @return
            Received signal strength in dB
        '''
        #Same as above
        return None
    
    def get_SNR(self) -> float:
        '''
        @desc
            This method calculates the signal to noise ratio at the reciver end
        @param  _txPhySetup
            Phy layer setup of the transmitter
        @param  _rxPhySetup
            Phy layer setup of the receiver
        @param _distance
            Distance between the transmitter and receiver
        @return
            signal to noise ratio
        '''
        #Same as above
        return None
    

    def get_PLR(self) -> float:
        '''
        @desc
            This method caculates the packet loss rate of the LoRa link.
        @return
            The normalized packet loss rate 
        '''
        #Same as above
        _plr = 0.0
        return _plr
    
    def get_TimeOnAir(
                    self, 
                    _frameLength: int)->float:
        '''
        @desc
            Calculates the time on air for LoRa frame given the modulation config setup and frame length.
        @param _frameLength
            Length of the frame in bytes
        @return
            Time on the air in msec
        '''
        _radioPhySetup = self.__src.get_PhySetup()
        _datarate = _radioPhySetup['datarate']
        
        return _frameLength / _datarate * 1000 # convert to msec
    
    def get_PropagationDelay(self, **kwargs) -> float:
        '''
        @desc
            Get the Propagation Delay of the link
    
        @return
            Propagation delay in seconds
        '''
        return self.__distance / 3e8
    
    def get_PERFromBER(
                    self, 
                    allowed_bits_wrong: int,
                    _size: int) -> float:
        """
        @desc
            Get the packet error rate (PER) of the frame based on the bit error rate (BER)
        @param[in]  allowed_bits_wrong
            Number of bits that are allowed to be wrong 
        @param[in]  _size
            Size of a frame in bytes
        @return
            PER of the frame from 0 to 1
        """
        # convert the size from bytes to bits
        _size = _size*8

        # get the bit error rate for this link
        _ber = self.get_BER()

        if not 0 <= _ber <= 1:
            raise ValueError("BER must be between 0 and 1")
        if allowed_bits_wrong < 0 or allowed_bits_wrong > _size:
            raise ValueError("Number of allowed bits wrong must be non-negative and less than or equal to the frame size")

        #now we have to use the binomial distribution to calculate the PER
        #P(X >= allowed_bits_wrong) = 1 - P(X < allowed_bits_wrong)
        prob = 1
        p = _ber
        q = 1 - p
        for _idx in range(allowed_bits_wrong+1):
            prob -= math.comb(_size, _idx) * (p ** _idx) * (q ** (_size - _idx))
        
        return prob

    
    def get_DopplerShift(self,
                         **kwargs)-> float:
        '''
        @desc
            Get the doppler shift at the current time for a link between satelliote and ground
        @param
            kwargs: Keyworded arguments
                _frequency: center frequency
                _velocity: relative velocity of the satellite (+ve for approaching, -ve for receding) (m/s)
        @return
            Doppler shift in Hz
        '''
        _frequency = kwargs.get('_frequency', None)
        _velocity = kwargs.get('_velocity', None) # You can use the API's in the satellite orbit helper model to get the relative velocity
        
        if _frequency is None:
            raise ValueError('Frequency is not provided for calculating the doppler shift')
        if _velocity is None:
            raise ValueError('Velocity is not provided for calculating the doppler shift')

        return (3e8/(3e8 + _velocity)) * _frequency - _frequency