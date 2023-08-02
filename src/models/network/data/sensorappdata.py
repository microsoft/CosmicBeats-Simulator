"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 26 June 2023

This model represents a sensor app data from say a sensor node
"""

from dataclasses import dataclass
from src.models.network.data.genericdata import GenericData

@dataclass
class SensorAppData(GenericData):
    pass
    #Same as GenericData. 
    #TODO: Add more fields if required