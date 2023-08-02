"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 26 June 2023

This model represents an ack data unit.
"""

from dataclasses import dataclass, field
from src.models.network.macdata.genericmac import GenericMAC 

@dataclass
class MACControl(GenericMAC):
    numPacketsToSend: int
    
    maxsize: int = field(init=False, default=255-4) # 255 bytes - 4 bytes for header