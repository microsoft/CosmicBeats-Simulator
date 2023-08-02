"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 26 June 2023

This model represents an image which a satellite might take
"""

from dataclasses import dataclass, field
from src.utils import Time
from src.models.network.data.genericdata import GenericData

@dataclass
class Image(GenericData):
    pass 
    #TODO: Add image data (i.e. location of image, etc
