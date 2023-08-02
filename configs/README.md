# Configure
The configuration for the simulation setup is supplied in JSON format. Several sample config files can be found in the [configs](/configs/) folder. In this section, we will explain the process of creating and customizing a config file.

## Simulation time ("simtime")
As stated in our primary [README](/README.md), this simulator operates on a discrete-time basis. Hence, while setting up the simulation, it is necessary to specify the start time, end time, and epoch interval. These details can be entered within the `"simtime"` JSON object. For proper formatting, please use the `"yyyy-mm-dd hh:mm:ss"` format for both the `"starttime"` and `"endtime"`. The `"delta"` field represents the epoch interval, measured in seconds.

## Logging setup
The `"simlogsetup"` object contains the logging setup for the simulator. Within this setup, we offer various log handlers, including command prompt-based, file-based, and others (find all the log handlers [here](/src/simlogging/)). You can select the desired log handler by setting the `"loghandler"` value to the class name of the corresponding log handler. Some log handlers may require additional configuration arguments from the user, such as the path to the log dumping directory. To provide these arguments, include them in the `"simlogsetup"` section. To understand the required arguments for a specific log handler, please refer to the corresponding log handler implementation module.
    
## Topologies (`"topologies"`)
To include one or more topologies in your simulation setup, use the `"topologies"` array. Each topology should have a distinct name and unique ID. Within each topology, you can define an array of nodes. For additional information about working with topologies, please refer to [this](/src/nodes/README.md) resource.

### Nodes (`"nodes"`)
In the simulator, a node represents a physical entity, such as a satellite, ground station, user terminal, IoT device, and more. Node configurations are presented as an array inside `"topologies"`.

Each node object consists of four mandatory properties:
1. Unique ID of the node, `"nodeid"`.
2. Type of node (`"type"`), denoted by abbreviations like SAT for satellite and GS for ground station. This aids in understanding generated logs for each node.
3. Logging level (`"loglevel"`), which supports different types of log messages, including "error", "warn", "debug", "info", "logic", and "all". You can set any of these values for `"loglevel"`.
4. Implementation name (`"iname"`) that corresponds to the desired node class. Multiple [implementations of node classes](/src/nodes/) are available. Simply use the name of your desired node class as the value of `"iname"`. 

Note that the chosen node class may require additional configuration properties, which can be provided in the same JSON object. To learn about the required config properties, please refer to the corresponding node implementation module or [here](/src/nodes/README.md).

As previously mentioned, a node may encompass one or multiple models. The configuration of models for a node is provided within the corresponding node object as an array.

### Models (`"models"`)
Each JSON object for model configuration must include the `"iname"` property, which determines the desired implementation of the model class that the user wants to use in the node. Multiple [implementations of model classes](/src/models/) are at your disposal.

Additionally, certain model classes may necessitate additional configuration inputs, which we include as properties in the same JSON object. To learn about the specific configuration inputs required for a particular model class, please refer to the corresponding model implementation module or [here](/src/models/README.md).

A skeleton config file looks as following.

```JSON
{
    "topologies":
    [
        // here goes the list of topology config objects
        {
            // config for the topology: 1
            
            "nodes":
            [
                // here goes the list of config objects for nodes in topology: 1
                {
                    // config for the node: 1

                    "models":
                    [
                        // here goes the list of config objects for models in node: 1
                        {
                            // config for model 1
                        },
                        {
                            // config for model 2
                        }
                    ]
                },
                {
                    // config for the node:2
                }
            ]
            
        },
        {
            // config for the topology: 2
        }
    ]
}
```

# Config file generator
Creating a config file for a topology that includes hundreds of nodes can be a cumbersome task. To simplify this process, we offer config file generator scripts [here](/config_generators/). Utilizing these scripts, you can easily generate a config file for any desired number of nodes.

To use the scripts, you only need to provide two files:
1. A file containing the TLEs (Two-Line Elements) of the satellites.
2. A file containing the locations of ground stations or IoT devices (if applicable).

In the script, you are required to provide the standard config for a satellite node, ground station, and IoT device (if present). The script will then generate the config for all your satellites, ground stations, and IoT devices, following the provided standard config.
