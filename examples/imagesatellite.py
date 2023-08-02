'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
'''

import sys
import os
import time
import threading
import random

#Let's add the path to the src folder so that we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

from src.sim.simulator import Simulator


if __name__ == "__main__":
    random.seed(0)
    _filepath = ''

    #look for the config file path in the command line arguments

    if(len(sys.argv) > 1):
        _filepath = sys.argv[1]
    else:
        _filepath = "configs/examples/config_imagesat.json"

    _sim = Simulator(_filepath)

    _startTime = time.perf_counter()

    #run execute method in a separate thread
    _thread_sim = threading.Thread(target=_sim.execute)
    
    # Let's compute all the FOVs before starting the simulation. This will make the simulation faster.
    # WARNING: Remove this part if you are getting error on a Windows machine. It may slow down the simulation.
    print("[Simulator Info] Computing FOVs...")
    _ret = _sim.call_RuntimeAPIs("compute_FOVs")
    print("[Simulator Info] FOVs computed.")
    
    # Now, let's start the simulation
    _thread_sim.start()
    _thread_sim.join()

    _endTime = time.perf_counter()

    print(f"[Simulator Info] Time required to run the simulation: {_endTime-_startTime} seconds.")