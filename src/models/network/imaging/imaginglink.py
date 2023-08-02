'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: July 4 2023
@desc
    This module models matches the paper:
        Devaraj, Kiruthika, et al. "Planet high speed radio: Crossing Gbps from a 3U cubesat." (2019).
        
    This model uses an Adaptive Coding Mechanism so the time on the air is changed based on the SNR
    
    The DVBS2 modulation details can be found here:
        Structure, Second Generation Framing. "Channel Coding and Modulation Systems for Broadcasting." 
        Interactive Services, News Gathering and Other Broadband Satellite Applications (2009): 307-1.
        https://www.etsi.org/deliver/etsi_en/302300_302399/302307/01.02.01_40/en_302307v010201o.pdf
        
    This is all made for Frame Size 64000 bits. Maybe we can change this later.
'''
from src.models.network.link import Link

import math
import numpy as np

class ImagingLink(Link):
    def __init__(self, _src, _dstn, _distance):
        '''
        @desc
            Constructor
        @param
            _src: Source radio device
            _dstn: Destination radio device
            _distance: Distance between source and destination
        '''
        self.__src: 'ImagingRadioDevice' = _src
        self.__dstn: 'ImagingRadioDevice' = _dstn
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
        #The BER is very low. The PER on 64000 bits is 10^-7. Let's just say 0 for now
        #TODO: Implement this https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=7434305
        return 0
        
    def get_PropagationLoss(self) -> float:
        '''
        @desc
            Get the Propagation Loss of the link in dB
        @return
            Free space Propagation Loss in dB
        '''

        _txPhySetup = self.__src.get_PhySetup()
        _distanceKM = self.__distance / 1000
        _freqGHz = _txPhySetup['_frequency'] / 1e9
        _loss = 20 * math.log10(_distanceKM) + 20 * math.log10(_freqGHz) + 92.45
        return _loss

    def get_ReceivedSignalStrength(self) -> float:
        '''
        @desc
            This method calculates the received signal strength at the receiver based on 
            the Phy layer setups of transmitter and receiver. 
        @return
            Received signal strength in dB
        '''
        _txPhySetup = self.__src.get_PhySetup()
        _rxPhySetup = self.__dstn.get_PhySetup()
        
        _freeSpaceLoss = self.get_PropagationLoss() 
        
        _eirp = _txPhySetup['_tx_power'] + _txPhySetup['_tx_antenna_gain'] - _txPhySetup['_tx_line_loss']
        
        _rxPower = _eirp - \
                    _freeSpaceLoss + \
                    _rxPhySetup['_rx_antenna_gain'] - \
                    _rxPhySetup['_rx_line_loss'] 
                    
        return _rxPower
    
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
        #Take a look at the following link for more information
        #https://www.kymetacorp.com/wp-content/uploads/2020/09/Link-Budget-Calculations-2.pdf
        
        if self.__SNR is not None: # so that we don't have to calculate it again and again
            return self.__SNR
        
        _txPhySetup = self.__src.get_PhySetup()
        _rxPhySetup = self.__dstn.get_PhySetup()
        
        _eirp = _txPhySetup['_tx_power'] + _txPhySetup['_tx_antenna_gain'] - _txPhySetup['_tx_line_loss']

        _fspl = self.get_PropagationLoss()        
        _atmosLoss =  _txPhySetup.get("_atmosphere_loss", 6) # this is in dB. Default is 6 dB
        
        BOTZMANCONST = -228.6 # in dB
        _snr = _eirp - _fspl - _atmosLoss + \
                _rxPhySetup['_gain_to_temperature'] - BOTZMANCONST - 10 * math.log10(_rxPhySetup['_bandwidth'])
        
        self.__SNR = _snr
        return _snr

    def get_PLR(self) -> float:
        '''
        @desc
            This method caculates the packet loss rate of the link.
        @return
            The normalized packet loss rate 
        '''
        #I'm assuming no packet loss in this model. I'm not sure how to calculate it. 
        return 0
    
    #This is table 13 from the DVBS2 standard (citation above)
    #The first element is the spectral efficiency and the second is the SNR
    #I've commented out some lines to make it monotonically increasing
    #Third element is code rate and the fourth is modulation order
    _snrToEfficiency = [
        (-2.35, 0.490243,1/4, 2), #QPSK 1/4 
        (-1.24, 0.56448,1/3, 2), #QPSK 1/3
        (-0.30, 0.789412,2/5, 2), #QPSK 2/5
        (1.00, 0.988858,1/2, 2), #QPSK 1/2
        (2.23, 1.188304,3/5, 2), #QPSK 3/5
        (3.10, 1.322253,2/3, 2), #QPSK 2/3
        (4.03, 1.487473,3/4, 2), #QPSK 3/4
        (4.68, 1.587196,4/5, 2), #QPSK 4/5
        (5.18, 1.654663,5/6, 2), #QPSK 5/6
        (6.20, 1.766451,8/9, 2), #QPSK 8/9
        (6.42, 1.788612,9/10, 2), #QPSK 9/10
#       (5.50, 1.779991,3/5, 3),#8PSK 3/5
        (6.62, 1.980636,2/3, 3), #8PSK 2/3
        (7.91, 2.228124,3/4, 3), #8PSK 3/4
        (9.35, 2.478562,5/6, 3), #8PSK 5/6
#       (10.69, 2.646012,8/9, 3), #8PSK 8/9
#       (10.98, 2.679207,9/10, 3), #8PSK 9/10
#       (8.97, 2.637201,2/3, 4), #16APSK 2/3
        (10.21, 2.966728,3/4, 4), #16APSK 3/4
        (11.03, 3.165623,4/5, 4), #16APSK 4/5
        (11.61, 3.300184,5/6, 4), #16APSK 5/6
#       (12.89, 3.523143,8/9, 4), #16APSK 8/9
#       (13.13, 3.567342,9/10, 4), #16APSK 9/10
        (12.73, 3.703295,3/4, 5), #32APSK 3/4
        (13.64, 3.951571,4/5, 5), #32APSK 4/5
        (14.28, 4.119540,5/6, 5), #32APSK 5/6
        (15.69, 4.397854,8/9, 5), #32APSK 8/9
        (16.05, 4.453027,9/10, 5), #32APSK 9/10
    ]
    
    def get_TimeOnAir(
                    self, 
                    _frameLength: int)->float:
        '''
        @desc
            Calculates the time on air for a given frame length
        @param _frameLength
            Length of the frame in bytes
        @return
            Time on the air in msec
        '''
        _frameLengthInBits = _frameLength * 8
        
        _radioPhySetup = self.__src.get_PhySetup()
        
        #Let's find the spectral efficiency
        _snr = self.get_SNR()
        _spectralEfficiency = None
        _cr = None
        
        for _snrThreshold, _efficiency, _codingRate, _ in self._snrToEfficiency:
            if _snr >= _snrThreshold:
                _spectralEfficiency = _efficiency
                _cr = _codingRate
            else:
                break
        if _spectralEfficiency is None:
            raise ValueError("SNR is too low for this link. SNR: {}, Distance: {}".format(_snr, self.__distance))
        
        #Let's find the symbol rate
        _symbolRate = _radioPhySetup['_symbol_rate']
        _uncodedDatarate = _symbolRate * _spectralEfficiency #bps
        _codedDatarate = _uncodedDatarate * _cr #bps
        _codedDatarate *= _radioPhySetup['_num_channels'] 
        
        _totalToA = _frameLengthInBits / _codedDatarate
        
        return _totalToA * 1000 # convert to msec
    
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
                    _allowedBitsWrong: int,
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
        
        if _size != 64800:
            #TODO: support other frame sizes. For now, only 64 kB frames are supported
            return 0

        return 10**-7

    
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
        _velocity = kwargs.get('_velocity', None) # You can use the API's in the satellite orbit model to get the relative velocity
        
        if _frequency is None:
            raise ValueError('Frequency is not provided for calculating the doppler shift')
        if _velocity is None:
            raise ValueError('Velocity is not provided for calculating the doppler shift')

        return (3e8/(3e8 + _velocity)) * _frequency - _frequency