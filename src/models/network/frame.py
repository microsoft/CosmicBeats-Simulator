'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 03 Apr 2023
@desc
    This module implements frame class that is used to exchange data between two radio devices
'''

from dataclasses import dataclass,field
from src.utils import Time
from src.models.network.address import Address
import threading

@dataclass
class Frame:
    # Unique ID of the frame
    id: int = field(init=False, default=0)

    # it works as an incrementing counter to generate unique ID for each frame instance
    globalFrameIDCounter: int = field(init=False, default=0)
    
    # Source adress of the frame
    source: Address

    # size of the frame in bytes
    size: int
    
    # payload of the frame in string
    payloadString: str = ""
    
    # When the frame is being transmitted, each device will get it's own instance of the frame. 
    # This instance ID will be used to identify the frame instance
    instanceID: int = 0
    
    def __post_init__(self) -> None:
        
        with threading.Lock():
            self.id = Frame.globalFrameIDCounter
            Frame.globalFrameIDCounter += 1

        self.__startTransmissionTime: 'Time | None' = None
        self.__endTransmissionTime: 'Time | None' = None
        self.__PLR = 0.0
        self.__PER = 0.0
        self.__collidedIDs: 'list[int]' = []
        self.__RSSI = 0.0
    
    def set_startTransmissionTime(self, time: 'Time') -> None:
        self.__startTransmissionTime = time
    
    def set_endTransmissionTime(self, time: 'Time') -> None:
        self.__endTransmissionTime = time
    
    def get_startTransmissionTime(self) -> 'Time | None':
        return self.__startTransmissionTime
    
    def get_endTransmissionTime(self) -> 'Time | None':
        return self.__endTransmissionTime
    
    def set_startReceptionTime(self, time: 'Time') -> None:
        self.__startReceptionTime = time
        
    def set_endReceptionTime(self, time: 'Time') -> None:
        self.__endReceptionTime = time
    
    def get_startReceptionTime(self) -> 'Time | None':
        return self.__startReceptionTime
    
    def get_endReceptionTime(self) -> 'Time | None':
        return self.__endReceptionTime
    
    def set_PLR(self, PLR: float) -> None:
        self.__PLR = PLR
    
    def get_PLR(self) -> float:
        return self.__PLR

    def set_PER(self, PER: float) -> None:
        self.__PER = PER

    def get_PER(self) -> float:
        return self.__PER
    
    def set_CR(self, CR: float) -> None:
        self.__CR = CR
        
    def get_CR(self) -> float:
        return self.__CR
    
    def set_BW(self, BW: int) -> None:
        self.__BW = BW
        
    def get_BW(self) -> int:
        return self.__BW
    
    def set_RSSI(self, RSSI: float) -> None:
        self.__RSSI = RSSI
    
    def get_RSSI(self) -> float:
        return self.__RSSI
    
    def set_SNR(self, SNR: float) -> None:
        self.__SNR = SNR
    
    def get_SNR(self) -> float:
        return self.__SNR
    
    def add_collidedID(self, collidedID: int) -> None:
        self.__collidedIDs.append(collidedID)
        
    def get_collidedIDs(self) -> list:
        return self.__collidedIDs
    
    def __str__(self) -> str:
        return f"Frame({self.size}, {self.payloadString}, {self.__startTransmissionTime}, {self.__endTransmissionTime})"
    
    def __repr__(self) -> str:
        return self.__str__()