"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 26 June 2023

This model represents a beacon data unit which a satellite node broadcasts to all the nodes in its range.
"""

from dataclasses import dataclass, field
from src.models.network.macdata.genericmac import GenericMAC

@dataclass
class MACBeacon(GenericMAC):
    # TODO: match the beacon data unit with the data from tinygs
    numDevicesInView: int = 0
    
    maxsize: int = field(init=False, default=255-4) # 255 bytes - 4 bytes for header
