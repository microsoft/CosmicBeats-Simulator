"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on June 23, 2023
@desc
    This model simulates an ADACS system's power draw. 
    It will draw power if it is in the sun and if the power regulator has power to give.
"""

from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.imodel import IModel, EModelTag

class ModelADACS(IModel):

    __modeltag = EModelTag.ADACS
    __ownernode: INode
    __supportednodeclasses = []
    __dependencies = [['ModelOrbit']]
    __logger: ILogger
    
    @property
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the model class. For example, ModelPower 
            Note that the name should exactly match to your class name. 
        """
        return self.__class__.__name__
        
    @property
    def modelTag(self) -> EModelTag:
        """
        @type
            EModelTag
        @desc
            The model tag for the implemented model
        """
        return self.__modeltag

    @property
    def ownerNode(self):
        """
        @type
            INode
        @desc
            Instance of the owner node that incorporates this model instance.
            The subclass (implementing a model) should keep a private variable holding the owner node instance. 
            This method can return that variable.
        """
        return self.__ownernode
    
    @property
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
        return self.__supportednodeclasses
    
    @property
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
        return self.__dependencies
    
    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self.__modeltag.__str__()])

    def __is_On(self, **_kwargs):
        """
        @desc
            This method returns wether the ADACS is on or not
        @param[in] _kwargs
            Keyworded arguments
            None for this API
        @return
            True if the ADACS is on, False otherwise
        """
        return self.__isOn
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "is_On": __is_On
    }
    
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
        _ret = None

        try:
            _ret = self.__apiHandlerDictionary[_apiName](self, **_kwargs)
        except Exception as e:     
            print(f"[ModelADACS]: An unhandled API request has been received by {self.__ownernode.nodeID}", e)
        
        return _ret
                
    def Execute(self):
        """
        @desc
            The ADACS model consumes energy from the power model if it has energy and in sunlight
        """
        #let's get the power model. We need to consume energy from it
        if self.__powerModel is None:
            self.__orbitalModel = self.__ownernode.has_ModelWithTag(EModelTag.ORBITAL)
            self.__powerModel = self.__ownernode.has_ModelWithTag(EModelTag.POWER)
            
        
        _inSunlight = self.__orbitalModel.call_APIs("in_Sunlight")
        if _inSunlight:
            #Then check if the power model has energy to give
            _hasEnergy = self.__powerModel.call_APIs("has_Energy", _tag="ADACS")
            if _hasEnergy:
                self.__powerModel.call_APIs("consume_Energy", _tag="ADACS", _duration=self.__ownernode.deltaTime)
                self.__isOn = True
            else:
                self.__isOn = False
        else:
            self.__isOn = False
                    
    def __init__(self, 
                _ownernode: INode, 
                _loggerins: ILogger):
        """
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        """
        self.__ownernode = _ownernode
        self.__logger = _loggerins
        self.__isOn = False
        
        self.__powerModel = None
        self.__orbitalModel = None
    
def init_ModelADACS(
                _ownernode: INode,
                _loggerins: ILogger,
                _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelADACS class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        None required for this model
    @return
        Instance of the model class
    '''
    
    return ModelADACS(_ownernode, _loggerins)