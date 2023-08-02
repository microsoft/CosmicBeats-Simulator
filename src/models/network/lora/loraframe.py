'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 26 July 2023
@desc
    This module implements a Lora Frame 
'''
from src.models.network.frame import Frame

class LoraFrame(Frame):
    def set_SF(self, sf: int) -> None:
        self.__SF = sf
    def get_SF(self) -> int:
        return self.__SF
    