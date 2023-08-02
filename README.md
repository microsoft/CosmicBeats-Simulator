# CosmicBeats Simulator
Our vision is to create a versatile space simulation platform that caters to individuals with diverse research interests, including networking, AI, computing, and more. Unlike traditional simulators tied to specific research applications, our design allows for seamless integration of various space-related research verticals.

The current version of simulator offers the capability to simulate various facets of satellite operation and communication, encompassing orbital dynamics, wireless communication, IoT networks, computation, imaging, and more. We have included numerous example scenarios that can be simulated using these functionalities, such as direct-to-satellite IoT communication networks, distributed ground station setups, imaging satellite operations, and others. However, users are not limited to these predefined scenarios. By making simple modifications in the config file, users can simulate many additional scenarios. Moreover, the platform's codebase allows for easy integration of new capabilities, enabling users to build upon the existing features smoothly. Additionally, the simulator provides runtime APIs that allow seamless interaction with the simulator for real-time control of operations. This feature facilitates easy integration of the simulator with external programs, requiring minimal or no modifications to the simulator's codebase. For instance, by utilizing the runtime APIs, users can effortlessly interface a scheduler for the ground station network.

We are thrilled to have you as a contributor to our project as our goal is to make this project community driven. Your valuable expertise and passion will play a vital role in shaping this space simulation platform for diverse research interests. Whether you are a developer, researcher, or enthusiast, there are plenty of opportunities to make a significant impact. Let's work together to create an exceptional and collaborative space simulation platform. 

## Design of the simulator
![Simplified core architecture](/figs/simulator_architecture.svg)

At the core of our simulator are "nodes" and "models." A node represents a physical endpoint entity, such as satellites, ground stations, user terminals, IoT devices, among others. Each node consists of one or multiple models, each of which replicates the functionality or behavior of the corresponding node component. These models can represent software or hardware elements, such as satellite batteries or even the orbital movements of satellites. Importantly, the user can make zero-code configuration of the models within each node based on their specific simulation requirements. This customization ensures that the simulation setup remains tailored to the intended research purpose. 

Interactions between models are critical for simulating real-world scenarios accurately. For instance, a computation model might need to assess the power availability from the battery model before performing its operations. To facilitate such interactions, a model exposes public APIs accessible by other models.   

Our simulator employs a discrete-time approach, executing simulated operations at regular intervals known as "epochs". This ensures consistent and predictable execution. During each epoch, the simulator invokes the `Execute()` method of each model within the nodes, effectively simulating the desired operations associated with those models.

With our space simulation platform, researchers can explore and contribute to a wide array of space-related research domains, thanks to its adaptable design and the ability to model diverse scenarios. You have the opportunity to contribute in various ways, such as introducing new nodes, models, SMAs, summarizers, APIs, and configs. Additionally, you can participate in fixing issues, enhancing computations, and much more. Your contributions are not limited, and we welcome your innovative ideas and improvements.

## Installation and setup
The simulator is developed using Python. To get started, ensure you have the most recent version of Python installed. Use `pip` to install the required package listed in [requirements.txt](/requirements.txt), and you'll be ready to go.

```bash
pip install -r requirements.txt
```

Anaconda can be used as well to setup the platform. Use [environment.yml](/environment.yml) to create the environment with required packages. 

## Quick start
Running the initial simulation scenario is swift and simple; just execute the [main.py](/main.py)

```bash
python main.py
```
Upon execution, the simulator will output a sequence of logs in your terminal.

If you wish to experiment with an alternative simulation configuration, you can provide the path to any configuration file from the [configs](/configs/) directory as an argument to the main.py script. 

```bash
python main.py configs/config.json
```

## Usage
Most of the simulator's usage involves customizing the nodes and models within the config file. Therefore, it is essential to comprehend the concepts of nodes, models, and configuration to effectively utilize the simulator. 

### Node
To learn about node, please refer to [this](/src/nodes/README.md).

### Model
To learn about model, please refer to [this](/src/models/README.md).

### config
The configuration of the simulation setup is maintained in a JSON file. To know more on how to work with the configuration file, please refer to [this](/configs/README.md).

### Running the simulation
The sole interface to the simulator is the [Simulator class](/src/sim/simulator.py), meaning that users can run the simulator by simply creating an instance of this class. 

```Python
from src.sim.simulator import Simulator

_configFilePath = "configs/config.json"

_sim = Simulator(_configFilePath)
_sim.execute()
```
The runtime APIs can also be accessed through the Simulator class by invoking `call_RuntimeAPIs()` method.

To learn more about the Simulator class and architecture of the simulator, please refer to [this](/src/sim/README.md).

### Analytics
The primary objective of a simulation is to generate insights, achieved by analyzing the logs produced by the simulator. As these insights are tailored to each specific use case, reusing the code written for analytics can be challenging. However, in our design, we prioritize creating an analytics pipeline that is highly adaptable and can be easily repurposed for various scenarios. To learn more about the analytics pipeline, please refer to [this](/src/analytics/README.md).

### Examples
We will attempt to execute a series of end-to-end simulation examples. ** It is essential to note that the data utilized for these simulation examples may not accurately represent real-world values.** We have used public TLE files from [https://celestrak.org/](https://celestrak.org/). 

#### Satellite based IoT network
In this simulation, there are 1000 IoT devices on Earth that engage in direct communication with over 150 LEO (Low Earth Orbit) satellites. The satellites collect data from the IoT devices, store it onboard, and transmit the data to ground stations whenever an opportunity arises. Find the corresponding config file [here](/configs/examples/config_1000iot.json).

```bash
 python examples/iotnetwork.py
```
It might take a while since we are dealing with a large number of nodes.

Once the simulation is complete, we are good to go for analyzing the logs and generating results. We have multiple sample scripts for log analysis available [here](/examples/analytics_sample/) that use our [SMAs and Summarizers](/src/analytics/) to analyze the logs and generate insights. For this example, we will use [analyze_datalayer.py](examples/analytics_sample/analyze_datalayer.py) to find end-to-end delay of our simulated IoT network. This script analyzes the logs stored in the `exampleLogs/` temporary directory and returns the results in several metrics.

```bash
python -Wignore examples/analytics_samples/analyze_datalayer.py exampleLogs/
```

#### Image satellite
In this example, we simulate a constellation of satellites capturing earth image, called Earth Observation satellites. Find the corresponding config file [here](/configs/examples/config_imagesat.json).

```bash
 python examples/imagesatellite.py
```
It dumps the log in the `imagingLogs/` directory. Once the simulation is complete, we run analysis on the logs by running an example analyzer script that returns the power profile of satellites in the constellation.  

```bash
python -Wignore examples/analytics_samples/analyze_power.py imagingLogs/
```

### Test
We have provided several test cases [here](/src/test/). You can use `pytest` package to evaluate the tests.
```bash
pytest -Wignore src/test/
```

## License
Please refer to [LICENSE.txt](/LICENSE.txt)

## Security
Please refer to [SECURITY.md](/SECURITY.md)

## Support
Please refer to [SUPPORT.md](/SUPPORT.md)

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
