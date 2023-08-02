'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
'''
from src.sim.simulator import Simulator
import sys
import time
import random

if __name__ == "__main__":
    random.seed(0)
    _filepath = ''

    #look for the config file path in the command line arguments

    if(len(sys.argv) > 1):
        _filepath = sys.argv[1]
    else:
        _filepath = "configs/config.json"

    _sim = Simulator(_filepath)

    _startTime = time.perf_counter()

    # Now, let's start the simulation

    _sim.execute()

    _endTime = time.perf_counter()

    print(f"[Simulator Info] Time required to run the simulation: {_endTime-_startTime} seconds.")
 
