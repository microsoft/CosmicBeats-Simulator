"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 26 June 2023

This model is a superclass for all the MAC unit
"""

from dataclasses import dataclass, field
from src.utils import Time
import threading

@dataclass
class GenericMAC:
    # Time when the data unit was created
    creationTime: Time
    
    # ID of the node which created the data unit
    sourceRadioID: int 
    
    # Size of the data unit in bytes
    size: int 
    
    # ID of the node intended to receive the data unit. -1 if broadcast
    intendedRadioID: int
    
    # Sequence number of the data unit
    sequenceNumber: int
    
    # Incremented every time a new data unit is created
    globalMACIDCounter: int = field(init=False, default=0)
    
    # Unique ID of the MAC unit
    id : int = field(init=False)
    
    @property
    def maxsize(self):
        # Override this property in the subclass
        return 0
    
    def __post_init__(self) -> None:
        with threading.Lock():
            self.id = GenericMAC.globalMACIDCounter
            GenericMAC.globalMACIDCounter += 1
            
        if self.size > self.maxsize:
            raise Exception("Size of the MAC unit cannot be greater than the max size")
     