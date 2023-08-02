# Model
A node encompasses one or more models, where each model essentially replicates a specific functionality or behavior of the node. For instance, a model can simulate the orbital movement of a satellite, while another model can represent solar panel power generation. In our code implementation, we utilize a class to encapsulate the properties and functionalities of each model. 
## Model interface
A model class must inherit the `IModel` interface that abstracts the core properties and functionalities of any model. For more details about `IModel`, please refer to the [imodel module](/src/models/imodel.py).We discuss some important properties and methods related to models below.  
### `iName`
The implementation name (`iName`) is the model class name.
### `modelTag`
It represents the category or type of a model, such as power, memory, orbit, radio, and others. It plays a crucial role in querying a specific type of model within a node. For example, we can inquire whether a node includes a "POWER" model. The various model tags are enumerated in `EModelTag`.
### `owneNode`
Each model instance must belong to a node instance. `ownerNode` provides the owner node instance of a model instance.
### `supportedNodeClasses`
A model may not support all the node implementation. For example, the orbit model does not support the ground station node. `supportedNodeClasses` gives the list of names of the node implementation classes that it supports. For example, if a model supports only the SatBasic and SatAdvanced node implementations, the list should be `['SatBasic', 'SatAdvanced']`. If the model supports all the node implementations out there, just keep the list `EMPTY`. For example, a data storage model can be used in any node implementation.
### `dependencyModelClasses`
dependencyModelClasses gives the nested list of name of the model implementations that this model has dependency on. For example, if a model has dependency on the ModelPower and ModelOrbitalBasic, the list should be `[['ModelPower'], ['ModelOrbitalBasic']]`. Now, if the model can work with EITHER of the ModelOrbitalBasic OR ModelOrbitalAdvanced, the these two should come under one sublist looking like `[['ModelPower'], ['ModelOrbitalBasic', 'ModelOrbitalAdvanced']]`. So each exclusively dependent model should be in a separate sublist and all the models that can work with either of the dependent models should be in the same sublist. If your model does not have any dependency, just keep the list `EMPTY`. 

### `call_APIs()`
The `call_APIs()` method serves as the API interface of a model. It is utilized to access the APIs provided by the model. The method takes two arguments: the API name and arbitrary keyworded arguments passed as input to the corresponding API. Typically, this method is invoked to interact with the model in real-time. For instance, the power model provides an API to retrieve the available battery power. The computation model within the same parent node can access this API, offered by the power model, by using the `call_APIs()` method of the power model.

### `Execute()`
The simulator operates in a discrete time manner. During each epoch, a model executes its operations. To facilitate this, each model within the simulator should possess an `Execute()` method, responsible for executing the model's specific operations. The `Execute()` method is called by the node when it needs to execute the model. 

In cases where we are implementing a helper model designed to assist other models, the `Execute()` method may remain empty. For instance, a field of view (FoV) helper model, responsible for generating the FoV for a node upon request by other models (e.g., communication), can have its `Execute()` method empty.


## Creating a model class
In the [models directory](/src/models/), we have already developed several model classes catering to orbital dynamics, power, communication functionalities, and more. However, users retain the flexibility to introduce additional model classes to expand the system's capabilities.

As previously mentioned, to create a new model class, it must inherit the `IModel` interface. Alternatively, users can inherit from an existing model class, especially when substantial portions of the new model class have already been implemented within the existing one. If there is no suitable base class, the factory method can be adopted to create a new model class inheriting the `IModel` interface.

In addition to implementing a new model class, users need to create an instance initialization method for the class. This step allows users to receive custom configuration inputs for their model instances. For reference, the `init_ModelOrbit(...)` method within the [modelorbit](/src/models/modelorbit.py) module provides an example. Utilizing the `_modelArgs` parameter allows direct retrieval of configuration inputs from the simulation config file, and the method returns an instance of the newly implemented model class.

To enable users to use the new model implementation in the simulation, it is necessary to add a reference to the initialization method in [modelinits](/src/sim/modelinits.py). By including the model class name as a key and the corresponding initialization method as the value in the `modelInitDictionary` dictionary, users can easily utilize the new model by simply adding its name in the config file. With this, the process is complete!

# Existing models
Find a list of implemented models below along with brief description.

## ModelOrbit

### About

    This module implements the orbital propagation model for the satellite.     

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key always_calculate
            Wether to automatically update the location of the node at every timestep. Default is False
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.ORBITAL

### APIs
#### in_Sunlight

        This method checks if the satellite is in sunlight. Sunlight operations are very very expensive when not done in bulk.
        So we will calculate all the sunlight times at once and store them in a list.
        
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this method
        @return
            True if the satellite is in sunlight, false otherwise
        

#### get_RelativeMotion

        This method calculates the relative motion between the satellite and a ground device such as ground station, IoT device.
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _gs
                The ground device (Assumed that the ground device is stationary)
        @return
            Tuple (distance, relative velocity) in m and m/s respectively
        

#### get_Passes

        This method tells you the start and end time of the passes for a ground station
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _gs
                The ground device (Assumed that the ground device is stationary)
            @key _start
                The start time of the passes (utils.Time)
            @key _end
                The end time of the passes (utils.Time)
            @key _minElevation
                The minimum elevation angle for the passes (float)
        @return
            List of tuples of start and end time of the passes. If the start or end time is during a pass, the start or end time is returned respectively.
        

#### get_Position

        This method calculates the position of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _time
                The time at which the position is to be calculated (utils.Time)
        @return
            utils.Location object containing the position of the satellite
        

#### get_Velocity

        This method calculates the velocity of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _time
                The time at which the velocity is to be calculated (utils.Time)
        @return
            The velocity of the satellite at the given time (x, y, z) in m/s (tuple of floats)
        

#### setup_Skyfield

        @desc
            Set's up the skyfield package for the model. 
            This is important because the skyfield package cannot be pickled.
            See https://github.com/brandon-rhodes/python-sgp4/issues/80
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        

#### remove_Skyfield

        @desc
            Removes the skyfield package for the model. 
            This is important because the skyfield package cannot be pickled.
            See https://github.com/brandon-rhodes/python-sgp4/issues/80
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        

## ModelOrbitOneFullUpdate

### About

    This module implements the orbital propagation model for the satellite.  
    It updates the positions of a satellite for the whole simulation period all at once at in the first execution. 
    

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        The JSON object does NOT require ANY arguments specifically for this model.
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.ORBITAL

## ModelFixedOrbit

### About

    This is an orbital model class used for testing purposes. You can pass in a location, and the satellite will be CONSTANTLY at that location.
    
    

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelFixedOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key lat
            Latitude of the satellite in degrees
        @key lon
            Longitude of the satellite in degrees
        @key alt
            Altitude of the satellite in meters
        @key sunlit
            True if the satellite is in sunlight, false otherwise
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.ORBITAL

### APIs
#### in_Sunlight

        This method checks if the satellite is in sunlight
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this method
        @return
            True if the satellite is in sunlight, false otherwise
        

#### get_RelativeMotion

        This method calculates the relative motion between the satellite and a ground device such as ground station, IoT device.
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
                @key _gs
                    The ground device (Assumed that the ground device is stationary)
        @return
            Tuple (distance, relative velocity) in m and m/s respectively
        

#### get_Position

        This method calculates the position of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
                @key _time
                    The time at which the position is to be calculated (utils.Time)
        @return
            utils.Location object containing the position of the satellite
        

#### get_Velocity

        This method calculates the velocity of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
                @key _time
                    The time at which the velocity is to be calculated (utils.Time)
        @return
            The velocity of the satellite at the given time (x, y, z) in m/s (tuple of floats)
        

## ModelEdgeCompute

### About

    This model represents a scheduler for a satellite performing edge computing.
    
    In this model, the satellite has to decide wether it should perform the computation locally
    or send it to the ground station.
    
    For now, let's assume that a satellite should always have something to transmit and compute.
    

### ModelDependencies
    [['ModelPower'], ['ModelCompute'], ['ModelImagingRadio']]

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelEdgeCompute class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        There are no arguments for this model.
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.SCHEDULER

## ModelCompute

### About

    This model simulates a satellite's compute.

    It has a queue of tasks that it needs to complete. It can only complete one task at a time.
    

### ModelDependencies
    [['ModelPower']]

### Initialization method and config properties


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
    

### ModelTag
    EModelTag.COMPUTE

### APIs
#### add_Data

        @desc
            This API is used to add data to the compute model.
        @param[in] _kwargs
            Arguments passed to the API handler
            @key _data
                The data to be added to the compute queue
        @return
            True if the data was added successfully, False otherwise
        

#### get_QueueSize

        @desc
            This API is used to get the size of the compute queue.
        @param[in] _kwargs
            Arguments passed to the API handler
        @return
            The size of the compute queue
        

## ModelLoraRadio

### About

    This is a lora communication model which manages the communication between two nodes that support LoRa communication.
    This model is an implementation of the IModel interface. It controls a LoRa Radio device and schedules when to transmit and receive frames.
    This model has two frame queues - reception and transmission which can be accessed extenerally through the appropriate APIs

### ModelDependencies
    [['ModelHelperFoV', 'ModelFovTimeBased']]

### Initialization method and config properties


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
            If true, the model will automatically send the data in the queue. 
            Default is true. If false, use send_Data API to send the data
        @key radio_physetup
            The radio phy setup to pass to the radio device. If not provided, None will be used
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.BASICLORARADIO

## ModelImagingRadio

### About

    This implements a radio model to model an imaging satellite's radio. See the link model (src/models/network/imaging/imaginglink.py) for more details.
    
    This is based off of the generic radio model (src/models/models_radio/modelgenericradio.py) and inherits from it. 
    

### ModelDependencies
    [['ModelHelperFoV', 'ModelFovTimeBased']]

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelImagingRadio class
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
            If true, the model will automatically send the data in the queue. 
            Default is true. If false, use send_Data API to send the data
        @key radio_physetup
            The radio phy setup to pass to the radio device. If not provided, None will be used
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.IMAGINGRADIO

## ModelGenericRadio

### About

    This is a generic communication model which manages the communication between two nodes.
    This model is an implementation of the IModel interface. It controls a Radio device and schedules when to transmit and receive frames.
    This model has two frame queues - reception and transmission which can be accessed externally through the appropriate APIs
    

### Initialization method and config properties


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
    

### APIs

#### add_ReceivedPacket
    @desc
            This method is invoked to add a received packet to the reception (Rx) queue of the model
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key _packet
                The packet to be added to the Rx queue
        @return
            True: If the packet was successfully added to the queue. False: Otherwise

#### get_RxQueue
    @desc
        This method returns the Rx queue of the model
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this API
    @return
        Rx queue

#### get_TxQueue
    @desc
        This method returns the Tx queue of the model
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this API
    @return
        Tx queue

#### add_PacketToTransmit
    @desc
        This method adds a packet to the transmit queue
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        @key _packet
            Packet to be transmitted 
    @return
        True: If it was successfully added to the queue. False: Otherwise

#### get_RadioDevice
    @desc
        This method returns the radio device that the model is using
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this API
    @return
        Radio device instance

#### get_ReceivedPacket
    @desc
        This method returns the packet at the head of the Rx queue
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this API
    @return
        Object at the head of the Rx queue. None otherwise

#### send_Packet
    @desc
        This method sends a packet from the radio device at this timestep. This will only work if _selfCntrl is False.
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        @key _packet
            Packet to be sent. If this is not provided, the method will try to send the one at the head of the Tx queue
    @return 
        True: If the frame was successfully sent. False: Otherwise
 
 #### set_PhyParam
    @desc
        This method sets the parameters of the radio device
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        @key _paramater
            The parameter to be set
        @key _value
            The value to be set

#### get_PhyParam 
    @desc
        This method returns the value of intended parameter of the radio device
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        @key _parameter
            The parameter to get
    @return
        The value of the parameter. Raises exception if the parameter is not valid

#### set_Frequency
    @desc
        This method switches the radio device to the given frequency
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        @key _frequency
            Switch to this frequency (Hz)

#### get_Frequency
    @desc
        This method returns the frequency that the radio device is currently using
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this method
    @return
        Frequency (Hz)

#### turn_RXOn
    @desc
        This method turns the radio device's RX on
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this method

#### turn_RXOff
    @desc
        This method turns the radio device's RX off
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this method

#### get_RxQueueSize
    @desc
        This method returns the size of the Rx queue
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this method
    @return
        Size of the Rx queue

#### get_TxQueueSize
    @desc
        This method returns the size of the Tx queue
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        None for this method
    @return
        Size of the Tx queue


## ModelISL

### About

    This is a ISL communication model which manages the communication between two satellites specified in the config file. 
    This model is an implementation of the IModel interface. It controls a ISL Radio device and schedules when to transmit and receive frames.
    This model only has one queue - rx. The tx queue will be managed by another model, e.g., a network model.
    To send a frame, use the send_Data() API. 
    

### Initialization method and config properties


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
            If true, the model will automatically send the data in the queue. 
            Default is true. If false, use send_Data API to send the data
        @key radio_physetup
            The radio phy setup to pass to the radio device. If not provided, None will be used
        @key connected_nodeIDs
            A list of node IDs that are connected to this node via ISL
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.ISL

## ModelDownlinkRadio

### About

    This is an extension of the original LoraRadioModel so that we can distinguish between multiple radio models
    This one is for the sat communicating with ground stations and sending beacon messages

    
    

### Initialization method and config properties



### ModelTag
    EModelTag.BASICLORARADIO

## ModelAggregatorRadio

### About

    This module is an extension of the original LoraRadioModel so that we can distinguish between the two lora radios.
    This is used for the aggregator node in the network, i.e., satellite in case of direct-to-satellite communication.
    

### Initialization method and config properties



### ModelTag
    EModelTag.BASICLORARADIO

## ModelFovTimeBased

### About

    This module implements the field of view (FoV) operation for a node. 
    It offers improved performance compared to the normal "modelhelperfov" model, especially when the timestep is small (refer to the fov test case for performance comparisons). 
    The FoV operation is based on finding the time of intersection with a satellite, and it does not involve calculating the elevation angles. 
    One unique aspect of this model is the presence of a static variable that holds all the pass times. 
    This design choice aims to avoid redundant computations. 
    Once the pass times for a satellite are calculated, they are reused in the ground station to prevent unnecessary recalculation.. 
    

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelFovTimeBased class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key min_elevation
            Minimum elevation angle of view in degrees
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.VIEWOFNODE

### APIs
#### get_View

        @desc
            This method generates the view for the parent node at the given time and location.
            If the _time and location are not provided it picks the latest location of the node based on the current node time. 
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _targetNodeTypes
                List of the node types that we are interested in 
            @key:  _myTime
                Time of the FoV search. Optional. If not provided, it uses the current node time
        @return
            A list of node IDs that can be seen of the target node types
        

#### find_Passes

        @desc
            This method finds the passes of the target nodes in the whole simulation time.
            This will update the __nodeToTimes dictionary with the passes of the target nodes. 
            This won't return anything.
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _targetTypes
                List of the node types that we are interested in
        

#### log_Pass

        @desc
            This method logs the pass of the target node in the current node. 
        @param[in]  _otherNode
            The other node
        @param[in]  _startTime
            The start time of the pass
        @param[in]  _endTime
            The end time of the pass
        

#### get_GlobalDictionary

        @desc
            This method returns the global dictionary of the model. 
            Technically, this is not an API of an individual node's model but global. But it's here
        @return
            A dictionary where the key is the node ID and the value is a list of the passes of the node. See __find_Passes for the format of the pass
        

#### set_GlobalDictionary

        @desc
            This method sets the global dictionary of the model. 
            Technically, this is not an API of an individual node's model but global. But it's here
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _globalDictionary
                A dictionary where the key is the node ID and the value is a list of the passes of the node. See __find_Passes for the format of the pass
        

## ModelHelperFoV

### About

    This module implements the field of view (FoV) operation for a node. 
    For example, which ground stations a satellite can see from its current position and vice versa.


### Initialization method and config properties


    @desc
        This method initializes an instance of ModelHelperFoV class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key min_elevation
            Minimum elevation angle in degrees
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.VIEWOFNODE

### APIs
#### get_View

        @desc
            This method generates the view for the parent node at the given time and location.
            If the _time and location are not provided it picks the latest location of the node based on the current node time. 
        @param[in]  _kwargs
            keyworded arguments that should contain the following arguments
            @key:  _isDownView
                True: A view of a node in space
                False: A view of a node on ground
            @key:  _targetNodeTypes
                List of the node types that we want to cover in the view.
                Ensure that the consistency has been kept with the view selection.
                For example, DO NOT select the nodes in space if it's a down view
            @key:  _myTime
                Time of the FoV search
            @key:  "_myLocation"
                Location of the node
        @return
            A list containing the visible node IDs of the target node types 
        

## ModelImagingLogicBased

### About

    This model simulates a satellite's imaging system. 
    This model will take an image if there is power available and the satellite is in sun. 
    An image will take a certain amount of time to take and will consume a certain amount of power.
    

### ModelDependencies
    [['ModelFixedOrbit', 'ModelOrbit', 'ModelOrbitOneFullUpdate'], ['ModelPower'], ['ModelDataStore', 'ModelDataAutoTransmit']]

### Initialization method and config properties


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
    

### ModelTag
    EModelTag.IMAGING

### APIs
#### take_Image

        @desc
            Takes an image on demand
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            Returns the image object if the image was taken, else returns None
        

#### check_ImagePossible

        @desc
            Uses the power, orbital, and ADACS model to check if the image is possible
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            Returns True if the image is possible, False otherwise
        

## ModelMACTTnC

### About

    This model represents the MAC layer specifically designed for the satellite network, known as the TTnC model. It operates based on the following steps:

    1. The model checks the RX queue of the ModelDownlinkRadio for a control packet sent from the Ground Station (GS).
    2. Upon receiving the control packet, the model checks the requested number of packets, denoted as 'X,' and searches its local storage to obtain the necessary data.
    3. The model sends up to "X" packets to the Ground Station using the ModelDownlinkRadio. It does not discard the sent packets until receiving a bulk ACK (Acknowledgment) that contains the sent packets. The sent packets are held in this model.
    4. The model then waits for the ACK by monitoring the RX queue of the downlink radiomodel.
    5. Once an ACK is received, the model examines the packet IDs and discards the received packets accordingly. Any packets that were not acknowledged will be resent when the next control packet is received. 

    

### ModelDependencies
    [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio'], ['ModelDataStore']]

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelMACTTnC class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key beacon_interval
            How often to send a beacon (in seconds)
        @key beacon_backoff
            Wait for a random amount of time between _beaconInterval and _beaconInterval + _beaconBackoff before sending a beacon
        @key beacon_frequency
            What frequency to send beacons
        @key downlink_frequency
            What frequency to send data on
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.MAC

## ModelMACgs

### About

    This MAC layer model is designed specifically for ground stations. It operates through the following steps:

    1. he ground station listens for satellite beacons by checking the RX queue of the modelradio.
    2. Upon receiving a beacon, the ground station sends a data download request for a specific number of packets, denoted as "X."
    3. The satellite responds by transmitting up to "X" packets to the ground station.
    4. The ground station confirms the number of packets received and stores the received packets in its data store.

    

### ModelDependencies
    [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio'], ['ModelDataStore']]

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelMACgs class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key num_packets
            The number of packets to ask the satellite to send
        @key timeout
            How long to wait to not receive any packets from the satellite before moving on.
        @key beacon_frequency
            What frequency to listen for beacons from the satellite
        @key downlink_frequency
            What frequency to listen for data packets from the satellite
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.MAC

## ModelMACiot

### About

    This model represents the MAC layer for IoT nodes and operates according to the following steps:

    1. The model checks the queue of the data generation model to see if there is any data to transmit.
    2. Upon encountering a beacon, the model verifies whether it is the most recent one and not an old beacon.
    3. If the beacon is the latest, the model attempts data transmission and waits for an acknowledgment (ACK). Both packet transmission and ACK reception occur through the modelradio.
    4. The model persists in retransmitting during subsequent beacon cycles until it successfully receives the ACK.


    

### ModelDependencies
    [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio'], ['ModelDataGenerator']]

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelMACiot class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key num_packets
            The number of packets to ask the satellite to send
        @key timeout
            How long to wait to not receive any packets from the satellite before moving on.
        @key beacon_frequency
            What frequency to listen for beacons from the satellite
        @key uplink_frequency
            What frequency to send data packets to the satellite
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.MAC

## ModelMACgateway

### About

    This MAC Layer model is designed for satellite-to-IoT device communication management. The model operates through the following steps:

        1. At each iteration, it examines the RX queue of the modelradio (uplink) to check for any received packets.
        2. Upon receiving a packet, it transmits an acknowledgment (ACK) back to the device using the same uplink modelradio.
        3. The received packet is then stored in the satellite's local storage.
        Both the acknowledgments and packets are sent and received using the ModelAggregatorRadio's frequency.
    

### ModelDependencies
    [['ModelAggregatorRadio'], ['ModelDataStore']]

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelMACgateway class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.MAC

## ModelADACS

### About

    This model simulates an ADACS system's power draw. 
    It will draw power if it is in the sun and if the power regulator has power to give.

    

### ModelDependencies
    [['ModelOrbit']]

### Initialization method and config properties


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
    

### ModelTag
    EModelTag.ADACS

### APIs
#### is_On

        @desc
            This method returns wether the ADACS is on or not
        @param[in] _kwargs
            Keyworded arguments
            None for this API
        @return
            True if the ADACS is on, False otherwise
        

## ModelPower

### About

    This is a energy model which the satellite generates power and has APIs to use energy. 
    All units are Jules and Watts

    

### ModelDependencies
    [['ModelFixedOrbit', 'ModelOrbit', 'ModelOrbitOneFullUpdate']]

### Initialization method and config properties
    @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _powerConsumptionDict
            Dictionary containing the power consumption of the model in W.
            For example:
            {
                "TXRADIO": .532,
                "HEATER": .532,
                "RXRADIO": .133,
                "CONCENTRATOR": .266,
                "GPS": .190
            }
        @param[in] _powerConfigurations
            Dictionary containing the power configurations of the model in Joules.
            For instance:
            {
                "MAX_CAPACITY": 25308,
                "MIN_CAPACITY": 15185,
                "INITIAL_CAPACITY": 25308 
            }
        @param[in] _powerGenerations
            Dictionary containing the power generation of the model in W. 
            For instance:
            {
                "SOLAR": 1.666667,
            }
        @param[in] _energyEfficiency
            The efficiency of the battery/panel as a float between 0 and 1
        @param[in] _alwaysOn:
            A list of the tasks that are always on
        @param[in] _timestep
            Timestep of the simulation in seconds (float)
        @param[in] _requiredEnergy
            Dictionary containing the required minimum energy for each task in Joules.
            For instance:
            {
                "Heater": 10,
                "GPS": 10,
                "TXRADIO": 20,
            }
            Means that the heater will only run when there is at least 10 J of energy available, the GPS when 10 J, and the TXRADIO when 20 J.
            If the required energy is not provided, the task will always run if more than the minimum energy is available.
            Used for the has_Energy API. 
    

### ModelTag
    EModelTag.POWER

### APIs
#### consume_Energy

        @desc
            This method consumes energy from the battery.
        @param[in]  _kwargs
            keyworded arguments that contain the following arguments:
                Option 1: if the energy in Joules is directly available, just provide the following argument 
                _kwargs["_energy"]: 'float'
                    Energy to be consumed in joules. Other following keyworded arguments are not required to

                Option 2: if the power and consumption numbers are available, just provide the following two arguments   
                _kwargs["_power"]: 'float'
                    Power in Watts
                _kwargs["_duration"]: 'float' 
                    representing the duration for which the power is consumed (in seconds)
                
                Option 3: if the power consumption number for your model tag is provided in the config file just provide the following two arguments
                _kwargs["_duration"]: 'float' 
                    representing the duration for which the power is consumed (in seconds) 
                _kwargs["_tag"]: 'str' 
                    representing the tag of the power consumption in the config file
        @return
            True: If the power was successfully consumed. 
            False: Otherwise
        

#### get_AvailableEnergy

        @desc
            This method returns the available energy in the battery in Joules
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            The available energy in the battery in Joules
        

#### get_MinCharge

        @desc
            This method returns the minimum charge in the battery in Joules
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            The minimum charge in the battery in Joules
        

#### get_MaxCharge

        @desc
            This method returns the maximum charge in the battery in Joules
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            The maximum charge in the battery in Joules
        

#### has_Energy

        @desc
            This method returns True if there is enough energy to run the requested operation
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _tag: 'str'
                Tag of the power consumption in the config file
        @return
            True: If there is enough energy to run the requested operation
            False: Otherwise
        

## ModelDataGenerator

### About

    This module implements the creation of data. 

### Initialization method and config properties


    @desc
        This method initializes an instance of the ModelDataGenerator
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key data_poisson_lambda
            The lambda value of the poisson distribution representing the number of data to be generated per second
        @key data_size
            How large the data created should be
        @key queue_size
            Size of the data queue. Default is -1, which means infinite
        @key self_ctrl
            Wether to automatically push data to the radio model or not. Default is False
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.DATAGENERATOR

### APIs

        @desc
            This method stops the model from generating any more data
        @param[in] _kwargs
            Keyworded arguments
            None 
        @return
            None
        

#### get_Data

        @desc
            This method returns the data generated by the model
        @param[in] _kwargs
            Keyworded arguments
            None 
        @return
            Data if available, None otherwise
        

#### get_Queue

        @desc
            This method returns the data queue of the model
        @param[in] _kwargs
            Keyworded arguments
            None
        @return
            Data queue
        

#### get_QueueSize

        @desc
            This method returns the size of the data queue of the model
        @param[in] _kwargs
            Keyworded arguments
            None
        @return
            Size of the data queue
        

## ModelDataStore

### About

    This model represents data storage with a queue of a set size. 
    It contains APIs to insert and retrieve data.  

    

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelHelperFoV class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key queue_size
            Size of the queue
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.DATASTORE

### APIs
#### get_Data

        @desc
            This method returns the data generated by the model
        @param[in] _kwargs
            Keyworded arguments
            None 
        @return
            Data if available, None otherwise
        

#### get_Queue

        @desc
            This method returns the data queue of the model
        @param[in] _kwargs
            Keyworded arguments
            None
        @return
            Data queue
        

#### get_QueueSize

        @desc
            This method returns the size of the data queue of the model
        @param[in] _kwargs
            Keyworded arguments
            None
        @return
            Size of the data queue
        

#### add_Data

        @desc
            This method adds data to the data queue of the model
        @param[in] _kwargs
            Keyworded arguments
            @key _data
                Data to be added to the queue
        @return
            True if data is added successfully, False otherwise
        

## ModelDataRelay

### About

    This model automatically transmits the data received from the radio model to the radio's model transmit buffer.


### ModelDependencies
    [['ModelGenericRadio', 'ModelLoraRadio', 'ModelDownlinkRadio', 'ModelAggregatorRadio', 'ModelImagingRadio']]

### Initialization method and config properties


    @desc
        This method initializes an instance of ModelDataRelay class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        None required for this model
    @return
        Instance of the model class
    

### ModelTag
    EModelTag.DATASTORE

### APIs
#### add_Data

        @desc
            API handler for adding data to the transmit buffer
        @param[in]  _kwargs
            Keyworded arguments 
            @key _data
                The data to be added
        @return
            True if the data is added to the transmit buffer, False otherwise
        