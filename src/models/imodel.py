"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 27 Sep 2022

This module includes the interface definition of the model. 
"""
from abc import ABC, abstractmethod
from enum import Enum

class EModelTag(Enum):
    """
    An enum listing the tags of model implementation.
    Each model has a model tag. To know more, please refer to the documentation.
    """
    POWER = 0
    ORBITAL = 1
    VIEWOFNODE = 2
    BASICLORARADIO = 3
    DATAGENERATOR = 4
    DATASTORE = 5
    ISL = 6
    MAC = 7
    ADACS = 8
    IMAGING = 9
    IMAGINGRADIO = 10
    COMPUTE = 11
    SCHEDULER = 12
    
class IModel(ABC):
    '''
    This is an interface implementation for the models. 
    For the details on the definition and functionalities please refer to the documentation guide.  
    '''
    
    @property
    @abstractmethod
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the model class. For example, ModelPower 
            Note that the name should exactly match to your class name. 
        """
        pass

    @property
    @abstractmethod
    def modelTag(self) -> EModelTag:
        """
        @type
            EModelTag
        @desc
            The model tag for the implemented model
        """
        pass

    @property
    @abstractmethod
    def ownerNode(self):
        """
        @type
            INode
        @desc
            Instance of the owner node that incorporates this model instance.
            The subclass (implementing a model) should keep a private variable holding the owner node instance. 
            This method can return that variable.
        """
        pass
    @property
    @abstractmethod
    def supportedNodeClasses(self) -> 'list[str]':
        '''
        @type
            List of string
        @desc
            A model may not support all the node implementation. 
            supportedNodeClasses gives the list of names of the node implementation classes that it supports.
            For example, if a model supports only the SatBasic and SatAdvanced, the list should be ['SatBasic', 'SatAdvanced']
            If the model supports all the node implementations, just keep the list EMPTY.
        '''
        pass
    
    @property
    @abstractmethod
    def dependencyModelClasses(self) -> 'list[list[str]]':
        '''
        @type
            Nested list of string
        @desc
            dependencyModelClasses gives the nested list of name of the model implementations that this model has dependency on.
            For example, if a model has dependency on the ModelPower and ModelOrbitalBasic, the list should be [['ModelPower'], ['ModelOrbitalBasic']].
            Now, if the model can work with EITHER of the ModelOrbitalBasic OR ModelOrbitalAdvanced, the these two should come under one sublist looking like [['ModelPower'], ['ModelOrbitalBasic', 'ModelOrbitalAdvanced']]. 
            So each exclusively dependent model should be in a separate sublist and all the models that can work with either of the dependent models should be in the same sublist.
            If your model does not have any dependency, just keep the list EMPTY. 
        '''
        pass

    @abstractmethod
    def call_APIs(
            self, 
            _apiName: str, 
            **_kwargs):
        '''
        This method acts as an API interface of the model. 
        An API offered by the model can be invoked through this method.
        @param[in] _apiName
            Name of the API. Each model should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        pass

    @abstractmethod
    def Execute(self):
        """
        This method executes the tasks that needed to be performed by the model.
        """
        pass