'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 1 Feb 2023
@desc
    This is a generic communication model which manages the communication between two nodes.
    This model is an implementation of the IModel interface. It controls a Radio device and schedules when to transmit and receive frames.
    This model has two frame queues - reception and transmission which can be accessed externally through the appropriate APIs
'''
from queue import Queue
import pickle
from abc import ABC, abstractmethod

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.network.address import Address
from src.models.imodel import EModelTag

class ModelGenericRadio(IModel, ABC):
    '''
    This model class implements the radio functionalities of node having a radio device. 
    This radio class enables communication, i.e., transmission and reception of frames between two nodes. 
    '''
    ##THESE ARE THE VARIABLES TO UPDATE IN SUBCLASSES:
    _modeltag = None 
    _supportednodeclasses: 'list[str]' = [] #list of node classes that this model supports
    _dependencies: 'list[list[str]]' = [] #list of models that this model depends on
    
    @property
    @abstractmethod
    def modelTag(self) -> EModelTag:
        """
        @type
            EModelTag
        @desc
            The model tag for the implemented model
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def _radioDeviceClass(self):
        """
        @type
            a RadioDevice class            
        """
        raise NotImplementedError
    
    @abstractmethod
    def _update_Channel(self):
        """
        @desc
            This method updates the channels of the radio device based on what is stored in the node
            This should only be called when the node is transmitting
        """
        raise NotImplementedError
    
    @abstractmethod
    def iName(self):
        raise NotImplementedError
    
    
    _logger: ILogger
    _ownernode: INode
    
    #Rest should be same for all subclasses (feel free to change if you need to)
    
    # model operation specific variables
    _radioID: int
    _rxQueue: Queue                # received packet queue
    _txQueue: Queue                # packets to be transmitted
    _selfCtrl: bool                # decides whether the frame queues are handled in the Execute() method by itself or externally

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
        return self._ownernode
    
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
        return self._supportednodeclasses
    
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
        return self._dependencies
    
    @property
    def radioID(self) -> int:
        '''
        @type
            int
        @desc
            ID of the radio device in the node
        '''
        return self._radioID
    
    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self._modeltag.__str__()])
    
    def _add_ReceivedPacket(self, **_kwargs) -> bool:
        """
        @desc
            This method is invoked to add a received packet to the reception (Rx) queue of the model
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key _packet
                The packet to be added to the Rx queue
        @return
            True: If the packet was successfully added to the queue. False: Otherwise
        """
        # check if the queue is full
        if self._rxCounter != self._maxQueueSize:    
            _pickledPacket = _kwargs['_packet']
            _packet = pickle.loads(_pickledPacket)
            
            self._rxQueue.put(_packet)
            self._rxCounter += 1
            self._log_Action("received", _packet)
            return True
        else:
            return False
    
    def _get_RxQueue(self, **_kwargs):
        '''
        @desc
            This method returns the Rx queue of the model
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this API
        @return
            Rx queue
        '''
        return self._rxQueue
    
    def _get_TxQueue(self, **_kwargs):
        '''
        @desc
            This method returns the Tx queue of the model
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this API
        @return
            Tx queue
        '''
        return self._txQueue
    
    def _add_PacketToTransmit(self, **_kwargs):
        """
        @desc
            This method adds a packet to the transmit queue
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key _packet
                Packet to be transmitted 
        @return
            True: If it was successfully added to the queue. False: Otherwise
        """
        if self._txCounter == self._maxQueueSize:
            return False
        else:
            self._txQueue.put(_kwargs["_packet"])
            self._txCounter += 1
            self._log_Action("addedToTxQueue", _kwargs["_packet"])
            return True
        
    def _get_RadioDevice(self, **_kwargs):
        '''
        @desc
            This method returns the radio device that the model is using
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this API
        @return
            Radio device instance
        '''
        return self._radioDevice
    
    def _get_ReceivedPacket(self, **_kwargs):
        '''
        @desc
            This method returns the packet at the head of the Rx queue
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this API
        @return
            Object at the head of the Rx queue. None otherwise
        '''
        if self._rxCounter == 0:
            return None
        else:
            _ret = self._rxQueue.get()
            self._log_Action("dequeued", _ret)
            self._rxCounter -= 1
            
            return _ret    
        
    def _send_Packet(self, **_kwargs):
        """
        @desc
            This method sends a packet from the radio device at this timestep. This will only work if _selfCntrl is False.
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key _packet
                Packet to be sent. If this is not provided, the method will try to send the one at the head of the Tx queue
            @key _destinationID
                ID of the destination node. If this is not provided, the method will send to channel 0
        @return 
            True: If the frame was successfully sent. False: Otherwise
        """      
        #Let's also check if there is enough power to send the frame        
        #If we have a power model, and we don't enough power to send the frame -> return
        if self.__powerModel is not None and not self.__powerModel.call_APIs("has_Energy", _tag="TXRADIO"):
            self._log_Action("noPower", _kwargs.get("_packet", None))
            return False
        
        #Let's check what to send
        _packetToSend = _kwargs.get("_packet", None)
        if _packetToSend == None:
            if self._txCounter > 0:
                _packetToSend = self._txQueue.get()
                self._txCounter -= 1
            else:
                return False
        
        #Let's update the transmission channels
        self._update_Channel()
        
        #Let's check if we can send it to anywhere
        if len(self._radioDevice.get_Channels()) == 0:
            self._log_Action("noChannel", _packetToSend)
            return False  
        
        #Let's check if we can send it to a specific channel
        _destinationChannel = 0
        _destinationID = _kwargs.get("_destinationID", None)
        if _destinationID is not None:
            #Let's find the channel to send to
            _channels = self._radioDevice.get_Channels()
            _found = False
            for _channelIdx in range(len(_channels)):
                _channel = _channels[_channelIdx]
                for _radioDevice in _channel.get_Devices():
                    if _radioDevice.get_OwnerNode().nodeID == _destinationID:
                        _destinationChannel = _channelIdx 
                        #We've found the channel to send to. Break out of all loops
                        _found = True
                        break
                if _found:
                    break
            if not _found:
                #We couldn't find the channel to send to
                self._log_Action("noChannel", _packetToSend)
                return False
        
        _success = self._radioDevice.send(_packetToSend.size, pickle.dumps(_packetToSend), _destinationChannel)
        if _success:        
            self._log_Action("sent", _packetToSend)
        else:
            #This is either because the radio device is busy or an error occurred. See the radio device's log for more info
            self._log_Action("attemptedToSend", _packetToSend)
        return _success
    
    def _set_PhyParam(self, **_kwargs):
        """
        @desc
            This method sets the parameters of the radio device
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key _paramater
                The parameter to be set
            @key _value
                The value to be set
        """
        _parameter = _kwargs["_parameter"]
        _value = _kwargs["_value"]
        
        _phySetup = self._radioDevice.get_PhySetup()
        
        if _parameter in _phySetup:
            _phySetup[_parameter] = _value
        else:
            raise Exception("The passed in parameter is not a valid parameter for the radio device")
    
    def _get_PhyParam(self, **_kwargs):
        """
        @desc
            This method returns the value of intended parameter of the radio device
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key _parameter
                The parameter to get
        @return
            The value of the parameter. Raises exception if the parameter is not valid
        """
        _parameter = _kwargs["_parameter"]
        
        _phySetup = self._radioDevice.get_PhySetup()
        
        if _parameter in _phySetup:
            return _phySetup[_parameter]
        else:
            raise Exception("The passed in parameter is not a valid parameter for the radio device")
    
    def _set_Frequency(self, **_kwargs):
        """
        @desc
            This method switches the radio device to the given frequency
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key _frequency
                Switch to this frequency (Hz)
        """
        self._set_PhyParam(_parameter="_frequency", _value=_kwargs["_frequency"])
    
    def _get_Frequency(self, **_kwargs):
        """
        @desc
            This method returns the frequency that the radio device is currently using
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this method
        @return
            Frequency (Hz)
        """
        return self._get_PhyParam(_parameter="_frequency")
    
    def _turn_RXOn(self, **_kwargs):
        """
        @desc
            This method turns the radio device's RX on
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this method
        """
        self._isRXOn = True
    
    def _turn_RXOff(self, **_kwargs):
        """
        @desc
            This method turns the radio device's RX off
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this method
        """
        self._isRXOn = False 
        
    def get_RxQueueSize(self, **_kwargs):
        """
        @desc
            This method returns the size of the Rx queue
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this method
        @return
            Size of the Rx queue
        """
        return self._rxCounter
    
    def get_TxQueueSize(self, **_kwargs):
        """
        @desc
            This method returns the size of the Tx queue
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            None for this method
        @return
            Size of the Tx queue
        """
        return self._txCounter
    
    # API dictionary where API name is the key and handler function is the value
    _apiHandlerDictionary = {
        "add_PacketToTransmit": _add_PacketToTransmit,
        "send_Packet": _send_Packet,
        
        "get_RxQueue": _get_RxQueue,
        "get_TxQueue": _get_TxQueue,
        "get_RxQueueSize": get_RxQueueSize,
        "get_TxQueueSize": get_TxQueueSize,
        "get_ReceivedPacket": _get_ReceivedPacket,
        
        "turn_RXOn": _turn_RXOn,
        "turn_RXOff": _turn_RXOff,
        
        "get_RadioDevice": _get_RadioDevice,
        "get_PhyParam": _get_PhyParam,
        "set_PhyParam": _set_PhyParam,
        "get_Frequency": _get_Frequency,
        "set_Frequency": _set_Frequency,
    }
    
    def _log_Action(self, _action: str, _object: str):
        '''
        @desc
            This method logs the action taken here in this model
        @param[in]  _action
            The action taken by the model
        @param[in]  _object
            The object on which the action was taken
        '''
        #Let's get the type of the object, i.e. if it's a mac unit, data unit, etc.
        _objectType = type(_object).__name__
        
        #Let's get the ID of the object. Just in case, we don't have an ID attribute, let's set it to None
        _objectID = getattr(_object, "id", None)
        
        #Let's see what nodes we can potentially talk to
        _currChannels = self._radioDevice.get_Channels()
        _currDevices = [i.get_Devices() for i in _currChannels] #List of lists of devices
        _currDevices = [item for sublist in _currDevices for item in sublist] #flatten the list
        _nodes = list(set(device.get_OwnerNode().nodeID for device in _currDevices)) #get the unique node IDs
        
        #Let's also get the queue sizes
        _rxQueueSize = self._rxCounter
        _txQueueSize = self._txCounter
        
        #Let's log the action.
        self._logger.write_Log(f"Action: {_action}. ObjectType: {_objectType}. ObjectID: {_objectID}. NodesInChannels: {_nodes}. RxQueueSize: {_rxQueueSize}. TxQueueSize: {_txQueueSize}", \
            ELogType.LOGINFO, self._ownernode.timestamp, self.iName)
        
    def call_APIs(
            self, 
            _apiName: str, 
            **_kwargs):
        '''
        @desc
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
            _ret = self._apiHandlerDictionary[_apiName](self, **_kwargs)
        except Exception as e:
            print(f"[ModelGenericRadio]: An unhandled API request has been received by {self._ownernode.nodeID}: ", e)
        return _ret    

    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _radioID: int, 
            _radioPhySetup,
            _queueSize: int = 0,
            _selfCtrl: bool = True) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _radioID
            ID of the radio device in a node
        @param[in]  _radioPhySetup
            Dictionary that contains the radio device physical setup
        @param[in]  _queueSize
            Size of the queue. By default, it is infinite
        @param[in]  _selfCtrl
            True: The transmission of the frames would be done automatically in the execution method
            False: The transmission of the frames or handling received frame would be externally controlled 
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self._ownernode = _ownernodeins
        self._logger = _loggerins

        self._radioID = _radioID

        self._rxQueue = Queue(maxsize= _queueSize)
        self._txQueue = Queue(maxsize= _queueSize)

        self._selfCtrl = _selfCtrl
        
        _radioDeviceClass = self._radioDeviceClass()
        
        self._radioDevice = _radioDeviceClass(Address(self._radioID), True, True, _ownernodeins, _loggerins, _radioPhySetup)
        self._radioDevice.set_ReceiveCallBack(self._add_ReceivedPacket)
        
        self._rxCounter = 0 #counter for received packets. Less overhead than calling qsize()
        self._txCounter = 0 #same but for transmitted packets
        self._maxQueueSize = _queueSize
        
        self.__powerModel = None

        self._isRXOn = True
   
    def Execute(self):
        if self.__powerModel is None:
            self.__powerModel = self._ownernode.has_ModelWithTag(EModelTag.POWER)

        #let's first update the radio device's packets
        self._radioDevice.update_Timestep()
        
        #Check if we should keep the radio on
        if self.__powerModel is not None and not self.__powerModel.call_APIs("has_Energy", _tag="RXRADIO"):
            self._isRXOn = False
        #Let's burn RX power if the radio is on    
        if self._isRXOn and self.__powerModel is not None:
            self.__powerModel.call_APIs("consume_Energy", _tag="RXRADIO", _duration=self._ownernode.deltaTime)
        
        #if there's no packet to transmit, let's return
        if self._txCounter == 0 or self._radioDevice.is_TxBusy():
            return
        
        # When the self control is enabled, the model will automatically send whatever is in the queue
        if self._selfCtrl:
            #If we aren't transmitting, let's transmit
            if not self._radioDevice.is_TxBusy():
                self._send_Packet()
                
def init_ModelGenericRadio(
    _ownernodeins: INode, 
    _loggerins: ILogger, 
    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelLoraRadio class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key radioID
            The ID to set the radio device to. If not provided, the node ID will be used
        @key queue_size
            The size of the queue. If not provided, the queue size will be infinite
        @key self_ctrl
            If true, the model will automatically send whatever is in the queue. 
            Default is true. If false, use send_Packet API to send a packet
        @key radio_physetup
            The radio phy setup to pass to the radio device. If not provided, None will be used
    @return
        Instance of the model class
    '''

    assert _ownernodeins is not None
    assert _loggerins is not None
    assert _modelArgs is not None

    if 'radioID' in _modelArgs:
        _radioId = _modelArgs.radioId
    else:
        _radioId = _ownernodeins.nodeID
    
    _queueSize = -1
    if 'queue_size' in _modelArgs:
        _queueSize = _modelArgs.queue_size
    
    _selfCtrl = True
    if 'self_ctrl' in _modelArgs:
        _selfCtrl = _modelArgs.self_ctrl
    
    _radioPhySetup = None
    if 'phy_setup' in _modelArgs:
        _radioPhySetup = _modelArgs.radio_physetup

    return ModelGenericRadio(_ownernodeins, 
                          _loggerins, 
                          _radioId,
                          _radioPhySetup, 
                          _queueSize, 
                          _selfCtrl)