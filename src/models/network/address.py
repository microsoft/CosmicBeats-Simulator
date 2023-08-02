'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
'''
class Address():
    def __init__(self, _address):
        self.__address = _address
    
    def get_Address(self):
        return self.__address
    
    def __str__(self) -> str:
        return str(self.__address)
    
    def __eq__(self, _other):
        return self.__address == _other.get_Address()