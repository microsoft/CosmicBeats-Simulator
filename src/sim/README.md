# Working with the simulator

## Creation and execution 
The [`Simulator`](/src/sim/simulator.py) class serves as a comprehensive interface to our simulator, providing a seamless experience from creation to execution, including runtime control. When provided with the [config file](/configs/README.md) as input, the `Simulator` class orchestrates the simulation environment and delegates the environment to the manager for executing the simulation. Users can effortlessly utilize the simulator by creating an instance of this class.

```Python
from src.sim.simulator import Simulator

_configFilePath = "configs/config.json"

_sim = Simulator(_configFilePath)
_sim.execute()
```

Internally, the `Simulator` class relies on two core classes: [`Orchestrator`](/src/sim/orchestrator.py) and [`Manager`](/src/sim/imanager.py).

The `Orchestrator` class is responsible for creating the simulation environment. Its main tasks include reading the config file, creating nodes with the specified models, resolving model dependencies, and allocating resources (e.g., threads, containers, virtual machines) to the nodes. To achieve this, the `Orchestrator` class refers to the [nodeinits](/src/sim/nodeinits.py) and [modelinits](/src/sim/modelinits.py) files to find the appropriate initialization methods for creating node and model instances based on the configuration in the config file.

On the other hand, the `Manager` class takes the simulation environment created by the `Orchestrator` class and executes the operations of the nodes by invoking their `Execute()` method. The `Manager` class handles the runtime operation of the simulator. 

Please take a look at the [class diagram](/figs/Class_diagram.pdf) for better understanding.

## Calling runtime APIs
The simulator offers the option of calling runtime APIs through the `call_RuntimeAPIs()` method of `Simulator` class. To enable this, you need to execute the simulator in a separate thread. Thn, in a different thread, you can invoke `call_RuntimeAPIs()`.
```Python
from src.sim.simulator import Simulator
import threading

_configFilePath = "configs/config.json"

_sim = Simulator(_configFilePath)

#run execute method in a separate thread
_thread_sim = threading.Thread(target=_sim.execute)

#call runtime APIs
_sim.call_RuntimeAPIs(...)

```