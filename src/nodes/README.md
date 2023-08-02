# Node and Topology
In the simulator, a node symbolizes a tangible endpoint entity that can include satellites, ground stations, user terminals, IoT devices, and more. In our code implementation, we employ a class to encapsulate the properties and functionalities of a node.

Topology is a group of nodes organized as a class in our implementation. For instance, a satellite IoT network can be represented by a topology that includes nodes for satellites, IoT devices, and ground stations.

## Node interface
To qualify as a node class, it is necessary for the class to inherit the `INode` interface, which abstracts the essential properties and methods shared by all nodes. Find the details on `INode` in [inode module](/src/nodes/inode.py). We discuss some crucial properties and methods below.
### `iName`
The implementation name (`iName`) is the node class name.
### `nodeType`
`nodeType` denotes the type of node that the class implements, such as satellite, IoT device, ground station, etc. The node types are listed in `ENodeType`.
### `hasModelWithTag()` and `hasModelWithName()`
`hasModelWithTag()` and `hasModelWithName()` method opens the way to check whether a node has a particular model and if so, it returns the model instance. For example, radio model may want to check whether its parent node has a power model to consider the power level before making any transmission or even update the consumed power after transmission. 
### `managerInstance`
`managerInstance` points to the Manager class instance that the node is part of. To learn about the Manager class refer to [this](/src/sim/README.md).
### `simStartTime`, `simEndTime`, and `deltaTime`
`simStartTime` and `simEndTime` are the start and end simulation time for the node respectively. `deltaTime` is the time gap between two simulation epochs in seconds.
### `Execute()`
The simulator operates in discrete time, where each epoch triggers a node to execute specific operations. The `Execute()` method is responsible for carrying out these node operations. Within this method, the simulator sequentially calls the `Execute()` methods of the models associated with the node to execute corresponding operations. For instance, in the `Execute()` method of a satellite instance, it may begin by invoking orbit model to update its position, followed by the power model to handle power generation. Subsequently, the node could execute the computation model if it includes one.
### `ExecuteCntd()`
The `ExecuteCntd()` method carries out operations of all discrete epochs until the simulation's end time.

## Creating a node class
In the [nodes directory](/src/nodes/), we have already developed several node classes for satellite, ground station, and IoT device functionalities. Nevertheless, users have the flexibility to introduce additional node classes to the system.

As previously mentioned, to create a new node class, it must inherit the `INode` interface. By following the factory method, users can implement a new node class that adheres to the `INode` interface. Alternatively, if an existing node class already contains a substantial portion of the desired functionality for the new node, users can choose to inherit from the existing node class. This allows for greater code reusability and simplifies the process of introducing new node types.  

To introduce a new node class, you must also create an instance initialization method for the class. This step grants you the flexibility to receive custom configuration inputs from the user for your specific node instance. For reference, you can examine the `init_SatelliteBasic(...)` method within the [satellitebasic](/src/nodes/satellitebasic.py) module. Utilizing the `_nodeDetails` parameter allows you to directly retrieve configuration inputs from the simulation config file. The method concludes by returning an instance of your newly implemented node class.

To make your new node implementation accessible in the simulation, you need to include a reference to your initialization method in [nodeinits](/src/sim/nodeinits.py). By adding the node class name as a key and the initialization method as the corresponding value in the `nodeInitDictionary` dictionary, users can seamlessly employ your class by merely specifying its name in the config file. With this, the process is complete!

## Topology interface
To qualify as a topology class, it is necessary for the class to inherit the `ITopology` interface, which abstracts the essential properties and methods. Find the details on `ITopology` in [itopology module](/src/nodes/itopology.py). 

# Existing Nodes
Find a list of implemented nodes below along with brief description.

## SatelliteBasic

### About

    It implements a very basic satellite class inheriting INode
    

### Initialization method and config properties

    @desc
        This method initializes an instance of SatelliteBasic class
    @param[in]  _nodeDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "nodeid": 1,
            "tle_1": "1 50985U 22002B   22290.71715197  .00032099  00000+0  13424-2 0  9994",
            "tle_2": "2 50985  97.4784 357.5505 0011839 353.6613   6.4472 15.23462773 42039",
            "additionalargs": ""
        }
    @param[in]  _timeDetails
        It's a converted JSON object containing the simulation timing related info. 
        The JOSN object must have the literals as follows (values are given as example).
        {
            "starttime": "2022-10-14 12:00:00",
            "endtime": "2022-10-14 13:00:00",
            "delta": 5.0
        }
    @param[in]  _topologyID
        The ID of the topology that the node instance is part of
    @param[in]  _logger
        Logger instance
    @return
        Created instance of the class
    

### NodeType
    ENodeType.SAT
    
## IoTBasic

### About

    This module implements an IoT Object 
    

### Initialization method and config properties

    @desc
        This method initializes an instance of IoT class
    @param[in]  _nodeDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "nodeid": 1,
            "latitude": 49.3,
            "longitude": -122.2,
            "elevation": 0.0,
            "additionalargs": ""
        }
    @param[in]  _timeDetails
        It's a converted JSON object containing the simulation timing related info. 
        The JOSN object must have the literals as follows (values are given as example).
        {
            "starttime": "2022-10-14 12:00:00",
            "endtime": "2022-10-14 13:00:00",
            "delta": 5.0
        }
    @param[in]  _topologyID
        The ID of the topology that the node instance is part of
    @param[in]  _logger
        Logger instance
    @return
        Created instance of the class
    

### NodeType
    ENodeType.IOTDEVICE

## GSBasic

### About

    This module implements the basic ground station (GS) class


### Created By
    
    Created by: Tusher Chakraborty
    Created on: 08 Nov 2022
    
### Initialization method and config properties

    @desc
        This method initializes an instance of SatelliteBasic class
    @param[in]  _nodeDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "nodeid": 1,
            "latitude": 49.3,
            "longitude": -122.2,
            "elevation": 0.0,
            "additionalargs": ""
        }
    @param[in]  _timeDetails
        It's a converted JSON object containing the simulation timing related info. 
        The JOSN object must have the literals as follows (values are given as example).
        {
            "starttime": "2022-10-14 12:00:00",
            "endtime": "2022-10-14 13:00:00",
            "delta": 5.0
        }
    @param[in]  _topologyID
        The ID of the topology that the node instance is part of
    @param[in]  _logger
        Logger instance
    @return
        Created instance of the class
    

### NodeType
    ENodeType.GS
