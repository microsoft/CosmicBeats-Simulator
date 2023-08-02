"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 17 March 2023

This is a generic data model that can be used to represent any type of data unit generated at the application layer.
"""

from dataclasses import dataclass, field
from src.utils import Time
import threading

@dataclass()
class GenericData:
    #  Time when the data is created
    creationTime: Time
    
    # Node ID of the source where data was generated
    sourceNodeID: int

    # size of the data payload in bytes
    size: int
    
    # This works like a counter to generate a new ID for each frame in incremental manner
    gloablDataIDCounter: int = field(init=False, default=0)
    
    # Unique ID of this data unit
    id: int = field(init=False) 
    
    def __post_init__(self) -> None:
        
        with threading.Lock():
            self.id = GenericData.gloablDataIDCounter
            GenericData.gloablDataIDCounter += 1