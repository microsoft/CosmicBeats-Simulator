"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on June 23, 2023
@desc
    This model simulates a satellite's compute.

    It has a queue of tasks that it needs to complete. It can only complete one task at a time.
"""
from math import ceil
from queue import Queue

from src.utils import Time
from src.nodes.inode import INode, ENodeType
from src.simlogging.ilogger import ELogType, ILogger
from src.models.imodel import IModel, EModelTag

class ModelCompute(IModel):

    __modeltag = EModelTag.COMPUTE
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic']
    __dependencies = [['ModelPower']]
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
        return "Model name: " + self.iName + "; " + "Model tag: " + self.__modeltag.__str__() 
    
    def __add_Data(self, **_kwargs):
        """
        @desc
            This API is used to add data to the compute model.
        @param[in] _kwargs
            Arguments passed to the API handler
            @key _data
                The data to be added to the compute queue
        @return
            True if the data was added successfully, False otherwise
        """
        _data = _kwargs['_data']
        if not self.__queueCounter == self.__fullQueueSize  and _data is not None:
            self.__computeQueue.put(_data)
            self.__queueCounter += 1
            return True
        else:
            return False
    
    def __get_QueueSize(self, **_kwargs):
        """
        @desc
            This API is used to get the size of the compute queue.
        @param[in] _kwargs
            Arguments passed to the API handler
        @return
            The size of the compute queue
        """
        return self.__queueCounter
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "add_Data": __add_Data,
        "get_QueueSize": __get_QueueSize
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
            print(f"[ModelCompute]: An unhandled API request has been received by {self.__ownernode.nodeID}", e)
        return _ret
        
    def Execute(self):
        #In this model we will take a process a proportional amount of images based on the timestep
        #Let's walk through a scenario:
        #Let's say the timestep is 1 minute and an image takes 11 seconds to process
        #In one timestep, we can process roughly 5.45 images (if power is available)
        #So in the first timestep, we will process 5 images
        #In the second timestep, we will take the rest of the image along with the new images
        
        for _image in self.__previousStepImages:
            self.__logger.write_Log("Image processed " + str(_image.id), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
        self.__previousStepImages.clear()
        
        _timeAvailable = float(self.__ownernode.deltaTime) #time available in this time step
        _timeCarryOver = 0.0 #Time that was carried over from the previous time step
        if self.__takingImageTill >= self.__ownernode.timestamp and self.__currentImage is not None:
            #we are currently processing an image
            _timeCarryOver = Time.difference_in_seconds(self.__takingImageTill, self.__ownernode.timestamp)
            #if the image completes in this timestep, let's add it to the list of images
            if _timeCarryOver < _timeAvailable:
                self.__previousStepImages.append(self.__currentImage)
                _timeAvailable -= _timeCarryOver

        #If there is still time in this timestep, let's process more images
        if _timeAvailable > 0:
            #If we have energy, let's process images
            _powerModel = self.__ownernode.has_ModelWithTag(EModelTag.POWER)
            if _powerModel.call_APIs("has_Energy", _tag="COMPUTE"):                
                #let's take how many images we can take in terms of time
                _numImages = _timeAvailable/self.__computeTime #This is a float. 5.45 in the example above
                
                #let's check that we have enough images in the queue
                _numImages = min(ceil(_numImages), self.__queueCounter) #This is an integer. 5 in the example above
                
                #Assuming we have enough images, let's take only the integer part. We will carry over the rest. 5 in the example above      
                _numInThisTimeStep = int(_numImages) 
                
                #Add the images which can wholly fit in this time step 
                for _ in range(_numInThisTimeStep):
                    _image = self.__computeQueue.get_nowait()
                    self.__queueCounter -= 1
                    self.__previousStepImages.append(_image)
                
                #Let's add the partial image to the next time step
                _percentOfImageRemaining = 1 - (_numImages - _numInThisTimeStep) #1 - 0.45 = .55 in the example above
                if _percentOfImageRemaining > 0 and self.__queueCounter > 0:
                    _timeRemainingOnNextStep = _percentOfImageRemaining * self.__computeTime #0.55 * 11 = 6.05 in the example above
                    self.__takingImageTill = self.__ownernode.timestamp.copy().add_seconds(self.__ownernode.deltaTime + _timeRemainingOnNextStep) 
                    self.__currentImage = self.__computeQueue.get_nowait()
                    self.__queueCounter -= 1
        
    def __init__(self, 
                _ownernode: INode, 
                _loggerins: ILogger,
                _computeTime: float,
                _queueSize: int
                ):
        """
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _computeTime
            How long in seconds it takes to process an image
        @param[in]  _queueSize
            Size of the compute queue
        """
        self.__ownernode = _ownernode
        self.__logger = _loggerins
        
        self.__computeTime = _computeTime 
        self.__computeQueue = Queue(_queueSize)
        self.__queueCounter = 0
        self.__fullQueueSize = _queueSize

        self.__previousStepImages = [] #list of images taken in the last time step        
        self.__takingImageTill = self.__ownernode.simStartTime.copy() #time till which the current image is being taken
        self.__currentImage = None #current image being taken
        
def init_ModelCompute(
                _ownernode: INode,
                _loggerins: ILogger,
                _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelCompute class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key compute_time
            How long in seconds it takes to process an image
        @key queue_size
            Size of the compute queue
    @return
        Instance of the model class
    '''
    
    return ModelCompute(_ownernode, _loggerins, _modelArgs.compute_time, _modelArgs.queue_size)