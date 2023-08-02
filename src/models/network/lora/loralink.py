'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 06 Jan 2023
@desc
    This module implements the base wireless link between two radio devices.
'''

import math
import numpy as np

from src.models.network.link import Link

class LoraLink(Link):
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
    
    # Table representing the SF and SNR to BER
    # https://ieeexplore.ieee.org/document/8581011
    # Source: Elshabrawy, T., & Robert, J. 
    # Analysis of BER and Coverage Performance of LoRa Modulation under Same Spreading Factor Interference. 
    # 2018 IEEE 29th Annual International Symposium on Personal, Indoor and Mobile Radio Communications (PIMRC), 1-6.
    sf_and_snr_to_ber = {
        7: {
            -6.5: .1e-4,
            -7: .8e-4,
            -8: .8e-3,
            -10: 1.1e-2,
            -12: .1,
            -14: .2,
            -16: .3,
            -18: .4,
            -24: .5,
        },
        8: {
            -8: .8e-5,
            -9: .2e-4,
            -10: 1.1e-4,
            -12: .8e-2,
            -14: .7e-1,
            -16: .1,
            -18: .3,
            -24: .5,
        },
        9: {
            -12: 1e-5,
            -13: 1.1e-4,
            -14: 1.1e-3,
            -15: 1e-2,
            -16: .3e-1,
            -18: .1,
            -20: .3,
            -22: .4,
            -24: .5,
        },
        10: {
            -15: 1e-4,
            -16: 1.1e-4,
            -17: 1.3e-3,
            -18: .1e-1,
            -20: .1,
            -22: .2,
            -24: .3,
        }, 
        11: {
            -18: 1.2e-5,
            -19: 1.4e-4,
            -20: 1.4e-3,
            -21: 1.1e-2,
            -22: .8e-1,
            -24: .1,
        },
        12: {
            -21: 1.4e-5,
            -22: .9e-3,
            -24: 1.2e-2,
        }
    }
     
    def get_BER(self):
        '''
        @desc
            Uses the table above to calculate the BER based on the SNR and SF
        @return
            BER from 0 to 1
        '''
        _sf = self.__src.get_PhySetup()['_sf']
        
        if _sf not in self.sf_and_snr_to_ber:
            raise Exception("SF not supported")
        for _snr, _ber in self.sf_and_snr_to_ber[_sf].items():
            if self.get_SNR() > _snr:
                return _ber
        return 1
        
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
            Received signal strength in dBW
        '''

        _txPhySetup = self.__src.get_PhySetup()
        _rxPhySetup = self.__dstn.get_PhySetup()
        
        ATMOSANDOTHERLOSS = 6 # includes pointing loss, polarization loss, atomspheric loss, cloud and fog loss 
        _freeSpaceLoss = self.get_PropagationLoss() 
        
        
        _rxPower = _txPhySetup['_tx_power'] + \
                    _txPhySetup['_tx_antenna_gain'] - \
                    _txPhySetup['_tx_line_loss'] - \
                    _freeSpaceLoss - \
                    ATMOSANDOTHERLOSS + \
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
            signal to noise ratio in dB
        '''
        #Take a look at the following link for more information
        #https://www.kymetacorp.com/wp-content/uploads/2020/09/Link-Budget-Calculations-2.pdf
        
        if self.__SNR is not None: # so that we don't have to calculate it again and again
            return self.__SNR
        
        _txPhySetup = self.__src.get_PhySetup()
        _rxPhySetup = self.__dstn.get_PhySetup()
        
        _eirp = _txPhySetup['_tx_power'] + _txPhySetup['_tx_antenna_gain'] - _txPhySetup['_tx_line_loss']

        _fspl = self.get_PropagationLoss()        
        _atmosLoss =  _txPhySetup.get("_atmosphere_loss", 1.8) # this is in dB. Default is 6 dB
        
        BOTZMANCONST = -228.6 # in dB
        _snr = _eirp - _fspl - _atmosLoss + \
                _rxPhySetup['_gain_to_temperature'] - BOTZMANCONST - 10 * math.log10(_rxPhySetup['_bandwidth'])
        
        self.__SNR = _snr
        return _snr
    

    def get_PLR(self) -> float:
        '''
        @desc
            This method caculates the packet loss rate of the LoRa link.
        @return
            The normalized packet loss rate 
        '''
        _plr = 1.0

        _txPhySetup = self.__src.get_PhySetup()
        # first get the signal strength at the reciver
        _rssi = self.get_ReceivedSignalStrength() # this is in dB
        # check whether RSSI meets the minimum detectable signal strength 
        # Data Source: https://www.mdpi.com/1424-8220/18/3/772
        # "Performance evaluation of LoRa considering scenario conditions." Sensors 18, no. 3 (2018): 772.
        _mdiTable = {
            7: -123.0,
            8: -126.0,
            9: -129.0,
            10: -132.0,
            11: -133.0,
            12: -136.0
        } #Key is spreading factor and value is minimum detectable signal strength in dBm 
        if (_rssi + 30) > _mdiTable[_txPhySetup['_sf']]:
            # The packet may get in
            # Now, we need to get the probability of lossing the packet
            # Fisrt, we get the packet delivery ratio by SNR data for different spreading factors
            # Data source: https://dl.acm.org/doi/abs/10.1145/3447993.3483250
            # Tong, Shuai, Zilin Shen, Yunhao Liu, and Jiliang Wang. "Combating link dynamics for reliable lora connection in urban settings." 
            # In Proceedings of the 27th Annual International Conference on Mobile Computing and Networking, pp. 642-655. 2021.

            # Data structure description
            # Key: spreding factor
            # Value: List
            # Index 0: Lower SNR value threshold. Below this, the PDR is 0.0
            # Index 1: Upper SNR value threshold. Abobe this, the PDR is 1.0
            # Index 2: A list holding the coffeient of 6 degree polynomial curve for PDR (Y) by SNR (X)
            _snrPdrTable = {
                12: [-25, -21, [-5e-10, 9e-8, -6e-6, 0.0001, 0.0003, -0.0094, 0.02]],
                11: [-23.2, -20.45, [-6e-10, 1e-7, -1e-5, 0.0004, -0.0054, 0.0259, -0.0271]],
                10: [-21.98, -19.32, [-5e-11, 4e-8, -5e-6, 0.0002, 0.004, 0.0233 -0.0337]],
                9: [-19.8, -16.75, [-1e-10, 5e-8, -6e-6, 0.0003, 0.0047, 0.0286, -0.0428]],
                8: [-18.02, -15.32, [3e-10, -6e-8, 3e-6, -5e-5, 0.0002, 0.0063, -0.0156]],
                7: [-16.96, -13.4, [-2e-11, 4e-9, -7e-7, 6e-5, 0.0015, 0.0119, -0.0216]]
            }

            # get the SNR value:
            _snr  = self.get_SNR()
            

            _snrPdrTableEntry = _snrPdrTable[_txPhySetup['_sf']]
            if _snr < _snrPdrTableEntry[0]:
                # SNR is below the lower bound. So we are gonna loss the packet
                _plr = 1.0 
            elif _snr > _snrPdrTableEntry[1]:
                # SNR is above the upper bound.
                _plr = 0.0
            else:
                # SNR value is in between the curve fitting area. 
                # Let's use the polynomial function to get the pdr value
                _pdr = 0.0
                _pwr =  len(_snrPdrTableEntry[2]) - 1 # degree of the polynomial 
                for _coeff in _snrPdrTableEntry[2]:
                    _pdr = _pdr + _coeff * math.pow(_snr, _pwr)
                    _pwr = _pwr - 1

                _pdr = np.clip(_pdr, 0.0, 1.0) # in case, value goes slightly beyond the limit due to curve fitting
                _plr = 1 - _pdr 
        else:
            # Need to discard the packet as the signal strength is below the detection level
            _plr = 1.0

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
        _bw = _radioPhySetup['_bandwidth']
        _sf = _radioPhySetup['_sf']
        _cdrate = _radioPhySetup['_coding_rate']
        _preamble = _radioPhySetup['_preamble']

        # calculate the symbol time
        _symbolTime = (2 ** _sf) / _bw

        # Calculate the preamble time
        _preambleTime = (_preamble + 4.25 + (2 if _sf <= 6 else 0)) * _symbolTime

        # calculate the data length
        _dataLength = math.ceil( (8 * _frameLength + 16 + 20 - 4*_sf + 8 - 8*(1 if _sf <= 6 else 0))/(4*_sf))* (_cdrate)

        # caclucate the payload time
        _payloadTime = _dataLength * _symbolTime
        
        _headerTime = 8 * _symbolTime

        _totalToA = _preambleTime + _headerTime + _payloadTime
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

        # get the bit error rate for this link
        _ber = self.get_BER()

        if not 0 <= _ber <= 1:
            raise ValueError("BER must be between 0 and 1")
        if _allowedBitsWrong < 0 or _allowedBitsWrong > _size:
            raise ValueError("Number of allowed bits wrong must be non-negative and less than or equal to the frame size")

        #now we have to use the binomial distribution to calculate the PER
        #P(X >= allowed_bits_wrong) = 1 - P(X < allowed_bits_wrong)
        prob = 1
        p = _ber
        q = 1 - p
        for _idx in range(_allowedBitsWrong+1):
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