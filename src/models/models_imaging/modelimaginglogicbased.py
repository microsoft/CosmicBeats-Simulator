"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on June 23, 2023
@desc
    This model simulates a satellite's imaging system. 
    This model will take an image if there is power available and the satellite is in sun. 
    An image will take a certain amount of time to take and will consume a certain amount of power.
"""
from math import ceil

import numpy as np

from src.utils import Time
from src.nodes.inode import INode, ENodeType
from src.simlogging.ilogger import ELogType, ILogger
from src.models.imodel import IModel, EModelTag
from src.models.network.data.image import Image

class ModelImagingLogicBased(IModel):

    __modeltag = EModelTag.IMAGING
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = [['ModelFixedOrbit', 'ModelOrbit', 'ModelOrbitOneFullUpdate'], 
                      ['ModelPower'], 
                      ['ModelDataStore', 'ModelDataAutoTransmit']]
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

    def __check_ImagePossible(self, **_kwargs) -> bool:       
        """
        @desc
            Uses the power, orbital, and ADACS model to check if the image is possible
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            Returns True if the image is possible, False otherwise
        """
        #We need to add all the images from the last time step to the data store
        #This is because an image shouldn't be available to the node until the time step that is taken finishes
        #Let's check if we are pointing towards the earth. If the ADACS is on, that means we are also in sun
        _adacsOn = self.__adacsModel.call_APIs("is_On")
        if not _adacsOn:
            return False
        
        #Let's check if we have enough energy to take an image
        _hasEnergy = self.__powerModel.call_APIs("has_Energy", _tag="IMAGING")
        if not _hasEnergy:
            return False
        
        return _hasEnergy and _adacsOn
    
    def __take_Image(self, **_kwargs):
        """
        @desc
            Takes an image on demand
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            Returns the image object if the image was taken, else returns None
        """       
        _canTake = self.__check_ImagePossible()
        if not _canTake:
            return None
        
        _hasPower = self.__powerModel.call_APIs("consume_Energy", _tag="IMAGING", _duration=self.__timeToBurn)
                
        if not _hasPower:
            self.__logger.write_Log(f"We don't have enough power to take an image", ELogType.LOGWARN, self.__ownernode.timestamp)
            return None
            
        _image = self.create_Image()
        return _image
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "take_Image": __take_Image,
        "check_ImagePossible": __check_ImagePossible
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
            print(f"[ModelImagingLogicBased]: An unhandled API request has been received by {self.__ownernode.nodeID}", e)
        return _ret
    
    def create_Image(self):
        '''
        @desc   
            Creates an image and returns the image object
        @return
            Image object
        '''
        _time = self.__ownernode.timestamp.copy()
        _id = self.__ownernode.nodeID
        _size = self.__imageSize
        _image = Image(_time, _id, _size)
        return _image
    
    def Execute(self):
        if not self.__selfCtrl:
            return
        
        #In this model we will take a proportional amount of images based on the timestep
        #Let's walk through a scenario:
        #Let's say the timestep is 1 minute and an image takes 11 seconds to take
        #In one timestep, we can take roughly 5.45 images (if in sunlight and power is available)
        #So in the first timestep, we will take 5 images
        #In the second timestep, we will take the rest of the image along with the new images
        #At the start of the second timestep, the 5 images will be inserted into the data store
        
        #Let's first get all the models that we need to interact with
        if self.__powerModel is None:
            self.__powerModel = self.__ownernode.has_ModelWithTag(EModelTag.POWER)
            self.__orbitalModel = self.__ownernode.has_ModelWithTag(EModelTag.ORBITAL)
            self.__adacsModel = self.__ownernode.has_ModelWithTag(EModelTag.ADACS)
            self.__dataStore = self.__ownernode.has_ModelWithTag(EModelTag.DATASTORE)
        
        if len(self.__imagesFromLastTimeStep) > 0:
            for _image in self.__imagesFromLastTimeStep:
                self.__dataStore.call_APIs("add_Data", _data=_image)
            self.__imagesFromLastTimeStep.clear()
        
        _timeAvailable = float(self.__ownernode.deltaTime) #time available in this time step
        _timeCarryOver = 0.0 #Time that was carried over from the previous time step
        if self.__currentImage is not None and self.__takingImageTill >= self.__ownernode.timestamp:
            #we are currently taking an image
            _timeCarryOver = Time.difference_in_seconds(self.__takingImageTill, self.__ownernode.timestamp)
            #if the image completes in this timestep, let's add it to the list of images
            if _timeCarryOver < _timeAvailable:
                #self.__logger.write_Log("Image completed in this time step", ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
                self.__imagesFromLastTimeStep.append(self.__currentImage)
                _timeAvailable -= _timeCarryOver
            else:
                _timeAvailable = 0.0

        #If there is still time in this timestep, let's take more images
        if _timeAvailable > 0:
            #If we have energy and we are in sunlight, let's take images
            if self.__check_ImagePossible():
                #let's take how many ever images we can take
                _numImages = _timeAvailable/self.__imageTime #This is a float. 5.45 in the example above
                _numInThisTimeStep = int(_numImages) #Let's take only the integer part. We will carry over the rest. 5 in the example above      
                
                #Add the images which can wholly fit in this time step 
                for _ in range(_numInThisTimeStep):
                    _image = self.__take_Image()
                    self.__imagesFromLastTimeStep.append(_image)
                
                #Let's add the partial image to the next time step
                _percentOfImageRemaining = 1 - (_numImages - _numInThisTimeStep) #1 - 0.45 = .55 in the example above
                _timeRemainingOnNextStep = _percentOfImageRemaining * self.__imageTime #0.55 * 11 = 6.05 in the example above
                
                self.__currentImage = self.__take_Image()
                self.__takingImageTill = self.__ownernode.timestamp.copy().add_seconds(self.__ownernode.deltaTime + _timeRemainingOnNextStep) 
       
        
    def __init__(self, 
                _ownernode: INode, 
                _loggerins: ILogger,
                _imagingTime: float,
                _imageSize: int,
                _imagingInterval: float,
                _selfCtrl: bool
                ):
        """
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _imagingTime
            How long in seconds it takes to image & readout an image
        @param[in]  _imageSize
            Size of the image in bytes
        @param[in] _imagingInterval 
            Time between successive images
        @param[in] _selfCtrl
            Wether or not to follow the Execute method (True) or use APIs to schedule when to take an image (False)
        """
        self.__ownernode = _ownernode
        self.__logger = _loggerins
        
        self.__imageTime = _imagingTime 
        self.__timeToBurn = _imagingTime #Duration of energy consumption
        
        self.__selfCtrl = _selfCtrl
        
        if _imagingInterval != 0 and not _selfCtrl:
            self.__logger.write_Log("[ModelImagingLogicBased] Since this model is not in selfCtrl mode, we are ignoring the _imagingInterval", ELogType.LOGWARN, self.__ownernode.timestamp)
        else:
            self.__imageTime = _imagingInterval + _imagingTime #Let's just pretend that the image takes the interval time and the imaging time 
        
        self.__imageSize = _imageSize
        
        self.__takingImageTill = self.__ownernode.simStartTime.copy().add_seconds(-1) #time till which the current image is being taken
        self.__currentImage = None
        self.__imagesFromLastTimeStep = [] #list of images taken in the last time step
        
        self.__powerModel = None
        self.__orbitalModel = None
        self.__dataStore = None
        
        
def init_ModelImagingLogicBased(
                _ownernode: INode,
                _loggerins: ILogger,
                _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelImagingLogicBased class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key time_to_image
            How long in seconds it takes to image & readout an image
        @key image_size
            Size of the image in bytes
        @key imaging_interval
            Time between successive images
        @key self_ctrl
            Wether or not to follow the Execute method (True) or use APIs to schedule when to take an image (False). Default is True
    @return
        Instance of the model class
    '''
    
    selfCtrl = True
    if hasattr(_modelArgs, "self_ctrl"):
        selfCtrl = _modelArgs.self_ctrl
    
    return ModelImagingLogicBased(_ownernode, _loggerins, _modelArgs.time_to_image, _modelArgs.image_size, _modelArgs.imaging_interval, selfCtrl)