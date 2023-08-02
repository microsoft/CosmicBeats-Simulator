'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 13 Dec 2022
@desc
    This module implements the ManagerParallel class of the simulator.
    It leverages the parallel computing capabilities offered by Python
'''
import concurrent.futures
import pickle
import queue
import threading
import multiprocessing as mp
import time
import numpy as np

from src.nodes.itopology import ITopology
from src.sim.imanager import IManager, EManagerReqType
from src.nodes.inode import ENodeType

class ManagerParallel(IManager):
    '''
    @desc
    This class implements the functionalities of the simulation manager leveraging the the parallel computing capabilities offered by Python.
    '''
    __topologies: 'list[ITopology]'
    __numOfSteps : int

    def __get_Topologies(self, **_kwargs) -> 'list[ITopology]':
        '''
        @desc
            List of topologies that the manager instance is handling
        @return
            List of ITopology
        '''
        return self.__topologies
    
    __reqHandlerDictionary = {
        EManagerReqType.GET_TOPOLOGIES : __get_Topologies
    }
    
    def req_Manager(self, 
                    _reqType: EManagerReqType, 
                    **_kwargs):
        '''
        @desc
           Send a request to the manager through this method
        @param[in]  _reqType
            Type of the request
        @param[in]  _kwargs
            Keyworded arguments that are passed to the handler function
        @return
            Returns the results (if any)
        '''
        _ret = None

        try:
            _ret = self.__reqHandlerDictionary[_reqType](self, **_kwargs)
        except:
            print("[Simulator Warning]: An unhandled request has been received in the req_Manager() method.")
        
        return _ret
    
    # The definition of API handlers

    def __call_ModelAPIsByModelName(self, **_kwargs):
        '''
        @desc
            This method calls the APIs of a model of a particular node
        @param[in]  _kwargs
            Keyworded arguments
            @key    _topologyID
                ID of the topology from which the data will be downloaded
            @key    _nodeID
                ID of the node
            @key    _modelName
                Name of the model
            @key    _apiName
                Name of the API
            @key    _apiArgs
                Arguments of the API
        @return
            The API return
        '''
        #check whether we have the keys
        if ("_topologyID" not in _kwargs) or \
            ("_nodeID" not in _kwargs) or \
            ("_modelName" not in _kwargs) or \
            ("_apiName" not in _kwargs):
            raise Exception("[API: call_ModelAPIsByModelName]: The keyworded arguments are not complete for the API")
        
        #get the topology ID
        _topologyID = _kwargs["_topologyID"]
        #get the node ID
        _nodeID = _kwargs["_nodeID"]
        #get the model name
        _modelName = _kwargs["_modelName"]
        #get the API name
        _apiName = _kwargs["_apiName"]
        #get the API arguments
        _apiArgs = _kwargs["_apiArgs"]

        #get the node instance from the topology
        try:
            _node = self.__topologies[_topologyID].get_Node(_nodeID)
        except:
            raise Exception("[API: call_ModelAPIsByModelName]: The node instance could not be found in the topology")
        
        #get the model instance from the node
        try:
            _model = _node.has_ModelWithName(_modelName)
        except Exception as e:
            raise Exception(f"[API: call_ModelAPIsByModelName]: The model instance could not be found in the node due to {e}")
        
        #call the API from the model
        try:
            _ret = _model.call_APIs(_apiName, **_apiArgs)
        except Exception as e:
            raise Exception(f"[API: call_ModelAPIsByModelName]: The {_apiName} could not be called from the model {_modelName} due to {e}")

        return _ret     

    def __get_NodeInfo(self, **_kwargs):
        '''
        @desc
            This method returns the information of a node
        @param[in]  _kwargs
            Keyworded arguments
            @key    topologyID
                ID of the topology from which the data will be downloaded
            @key    nodeID
                ID of the node
            @key    infoType
                Type of the information
        '''
        #check whether we have the keys
        if ("_topologyID" not in _kwargs) or \
            ("_nodeID" not in _kwargs) or \
            ("_infoType" not in _kwargs):
            raise Exception("[API: get_NodeInfo]: The keyworded arguments are not complete for the API")
        
        #get the topology ID
        _topologyID = _kwargs["_topologyID"]
        #get the node ID
        _nodeID = _kwargs["_nodeID"]
        #get the information type
        _infoType = _kwargs["_infoType"]

        #get the node instance from the topology
        try:
            _node = self.__topologies[_topologyID].get_Node(_nodeID)
        except:
            raise Exception("[API: get_NodeInfo]: The node instance could not be found in the topology")
        
        # Check the node information type using the infoType argument with switch case
        _nodeInfo = None
        match _infoType:
            case "time":
                _nodeInfo = _node.timestamp.copy()
            case "position":
                _nodeInfo = _node.get_Position()
            case _:
                raise Exception(f"[API: get_NodeInfo]: The information type {_infoType} is not supported")

        return _nodeInfo

    def __pause_AtTime(self, **_kwargs):
        '''
        @desc
            This method pauses the simulation at a particular time step. 
            It will return a threading.Event object which will be used to pause the simulation. 
            If you'd like to pause the simulation multiple times, it is recommended to do it while the simulation is paused.
            This will overwrite the previous pause
        @param[in]  _kwargs
            Keyworded arguments
            @key _timestep
                Time step at which the simulation will be paused (an integer)
        @return
            A threading.Event object which will be set when the simulation is paused.
            Returns None if the pause timestep has already passed. 
        '''
        if ("_timestep" not in _kwargs):
            raise Exception("[API: __pause_AtTime]: The keyworded arguments are not complete for the API")
        
        #Let's get the pause timestep
        _pauseTimeStep = _kwargs["_timestep"]
        
        #get the current time step
        _currentTimeStep = self.__currentStep

        if _pauseTimeStep < _currentTimeStep:
            return None
        else:
            self.__timeStepToStop = _pauseTimeStep
            return self.__stoppingCondition
        
    def __resume(self, **_kwargs):
        """
        @desc
            This method resumes the simulation. 
            Call this method after you have paused the simulation.        
        """
        self.__stoppingCondition.clear()
        self.__resumingCondition.set()
        
    def __compute_FOVs(self, **_kwargs):
        """
        @desc
            Call this method to compute all the FOVs of all the nodes in the topology.
            This method should be called before the simulation starts.
            The idea here is to pre-compute all the FOVs then load them during the simulation.
            This will save a lot of time, especially if you are running the same simulation multiple times or have a lot of cores.
        @param[in]  _kwargs
            Keyworded arguments:
            @key _outputPath
                Optional path to the output file where the FOVs will be stored. 
                If you store the FOVs, you can use the load_FOVs method to load them during a simulation.
                If you decide not to store them, the FOVs will be updated in the node instances. 
            @key _numProcesses
                Optional number of processes to use for the computation. Default is number of existing CPUs.
        """
        _numProcesses = mp.cpu_count()
        if ("_numProcesses" in _kwargs):
            _numProcesses = _kwargs["_numProcesses"]
        
        _nodeQueue = mp.Queue() #queue to store the node IDs to be processed
        _fovQueue = mp.Queue() #the output queue to store the FOVs

        def __processMethod():
            #This is the method that will be run by each process            
            try:
                #let's calculate how many ever FOVs we can 
                #If you look through the model, you will see that each one internally stores their FOVs. So, we just need to calculate then retrieve them
                _lastNodeID = -1 #this is to keep track of the last node ID that was processed
                while True:
                    try:
                        _satID = _nodeQueue.get(timeout=1)
                        #Let's add in the skyfield model again. Look below for the reason
                        self.__call_ModelAPIsByModelName(
                            _topologyID = 0,
                            _nodeID = _satID,
                            _modelName = "ModelOrbit",
                            _apiName = "setup_Skyfield",
                            _apiArgs = {}
                        )
                        
                        #Let's actually compute the FOVs
                        self.__call_ModelAPIsByModelName(
                            _topologyID = 0,
                            _nodeID = _satID, 
                            _modelName = "ModelFovTimeBased",
                            _apiName = "find_Passes",
                            _apiArgs = {
                                "_targetNodeTypes" : [ENodeType.GS, ENodeType.IOTDEVICE]
                            })
                        
                        _lastNodeID = _satID
                    
                    except queue.Empty:
                        #We have processed all the nodes
                        break
                    
                    except Exception as _e:
                        #We have an exception. Let's print it and exit
                        print(f"[API: compute_FOVs]: An exception occurred while computing FOVs: {_e}")
                        exit(1)
                
                if _lastNodeID != -1:
                    #Let's get the FOVs and store them in the queue
                    _dict = self.__call_ModelAPIsByModelName(
                        _topologyID = 0,
                        _nodeID = _satID,
                        _modelName = "ModelFovTimeBased",
                        _apiName = "get_GlobalDictionary",
                        _apiArgs = {}
                    )
                    _fovQueue.put(_dict)
                    
                #let's exit the process
            except Exception as _e:
                print(f"[API: compute_FOVs]: An exception occurred while computing FOVs: {_e}")
                exit(1)
            
            #let's exit the process
            return
        
        #Now back to the main process
        assert len(self.__topologies) == 1, "[API: compute_FOVs]: This method is only supported for a single topology"
        
        #We're going to loop through all the satellites, which will then find the passes for all the ground stations/IoT devices
        _sats = self.__topologies[0].get_NodesOfAType(ENodeType.SAT)
        for _sat in _sats:
            #We need to remove the pickle skyfield object from the node instance. 
            #See the API documentation for more details
            #TODO: This is a hack. We need to find a better way to do this
            self.__call_ModelAPIsByModelName(
                _topologyID = 0,
                _nodeID = _sat.nodeID,
                _modelName = "ModelOrbit",
                _apiName = "remove_Skyfield",
                _apiArgs = {}
            )
            
            _nodeQueue.put(_sat.nodeID)
            
        #let's create the processes
        _processes = []
        for _ in range(_numProcesses):
            _process = mp.Process(target=__processMethod)
            _processes.append(_process)
            _process.start()
        
        #In this main process, we need to keep checking if the processes are done and emptying the fovQueue
        #We can't use the join() yet because the queue's buffer might get full and the processes might get stuck
        #So, we need to keep checking if the processes are done and emptying the queue
        _processDicts = []
        while True:
            _allDone = True
            for _process in _processes:
                if _process.is_alive():
                    _allDone = False
                    break
            if _allDone:
                break
            else:
                #Let's wait for 1 second
                time.sleep(1)
                #Let's check if the queue is empty
                while not _fovQueue.empty():
                    _processDicts.append(_fovQueue.get())
        
        #Let's reap the processes
        for _process in _processes:
            _process.join()
                
        #Let's combine all the dictionaries. Non-sat devices will have their FOVs spread across multiple dictionaries
        _outputFOV = {}
        for _fovDict in _processDicts:
            for _nodeID, _fovArray in _fovDict.items():
                if _fovArray is None or _fovArray.shape[0] == 0:
                    continue
                _thisList = _outputFOV.get(_nodeID, None)
                
                if _thisList is None:
                    _thisList = _fovArray
                else:
                    _thisList = np.concatenate((_thisList, _fovArray), axis=0)
                
                _outputFOV[_nodeID] = _thisList

        #Load the FOVs into the nodes  
        #Since we're using a single topology, we can just use the first node
        self.__call_ModelAPIsByModelName(
            _topologyID = 0,
            _nodeID = _sats[0].nodeID,
            _modelName = "ModelFovTimeBased",
            _apiName = "set_GlobalDictionary",
            _apiArgs = {
                "_globalDictionary" : _outputFOV
            }
        )
        
        #Let's add the skyfield model again. Look above for the reason
        for _sat in _sats:
            self.__call_ModelAPIsByModelName(
                            _topologyID = 0,
                            _nodeID = _sat.nodeID,
                            _modelName = "ModelOrbit",
                            _apiName = "setup_Skyfield",
                            _apiArgs = {}
                        )

        #Now, let's save it to a file if needed
        if ("_outputPath" in _kwargs):
            _outputPath = _kwargs["_outputPath"]
            with open(_outputPath, "wb") as _f:
                pickle.dump(_outputFOV, _f)
            
    def __load_FOVs(self, **_kwargs):
        """
        @desc
            This method loads the FOVs from a file and sets it to the nodes
            Look in the compute_FOVs() method for details on generating the FOVs
        @param[in] _kwargs
            _inputPath: Path to the file containing the FOVs
        """
        _inputPath = _kwargs["_inputPath"]
        with open(_inputPath, "rb") as _f:
            _fovDict = pickle.load(_f)
            self.__call_ModelAPIsByModelName(
                _topologyID = 0,
                _nodeID = 0,
                _modelName = "ModelFovTimeBased",
                _apiName = "set_GlobalDictionary",
                _apiArgs = {
                    "_globalDictionary" : _fovDict
                }
            )
    
    def __run_OneStep(self, **_kwargs):
        '''
        @desc
            This method is called to run one step of the simulation.
        '''
        for _topology in self.__topologies:
            for _node in _topology.nodes:
                _node.Execute()

    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "call_ModelAPIsByModelName" : __call_ModelAPIsByModelName,
        "get_NodeInfo" : __get_NodeInfo,
        "pause_AtTime" : __pause_AtTime,
        "resume" : __resume,
        "get_Topologies": __get_Topologies,
        "compute_FOVs" : __compute_FOVs,
        "load_FOVs" : __load_FOVs,
        "run_OneStep" : __run_OneStep
    }

    def call_APIs(self, 
                _api: str, 
                **_kwargs):
        '''
        This method acts as a runtime API interface of the manager. 
        An API offered by the manager can be invoked through this method in runtime.
        @param[in] _api
            Name of the API. Each model should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        _ret = None
 
        try:
            _ret = self.__apiHandlerDictionary[_api](self,
                                                          **_kwargs)
        except Exception as e:     
            print(f"[Runtime API Manager]: An exeption has been raised while executing the API: {e}")
        
        return _ret

    def __init__(
            self, 
            **_simEnv):
        '''
        @desc
            Constructor of the class.
        @param[in]  __simEnv
            Simulation environment embedded in a keyworded arbitrary arguments as follows
                @key    topologies
                    List of the topologies
                @key    numOfSimSteps
                    Number of setps (epochs) we want to run the simulator
                @key    deltaTime
                    Time delta between each simulation epoch
                @key   numOfWorkers
                    Number of threads to be used for the simulation
        '''
        self.__topologies = _simEnv["topologies"]
        self.__numOfSteps = int(_simEnv["numOfSimSteps"])
        self.__numOfThreads = int(_simEnv["numOfWorkers"])
        
        self.__currentStep = 0

        self.__timeStepToStop = None
        
        # This is the threading.Condition() object that is used to pause the simulation
        self.__stoppingCondition = threading.Event()
        self.__resumingCondition = threading.Event()
        
        # update the manager instance of all the node objects
        for _topology in self.__topologies:
            for _node in _topology.nodes:
                _node.add_ManagerInstance(self) 
                
                                
    def run_Sim(self):
        '''
        @desc
            This method is called to run the simulation.
        '''
        # To keep the nodes in sync, we ensure that the threads join at the end of each step.
        while self.__currentStep < self.__numOfSteps:
            
            # Check if the simulation is to be paused. If it is, then we wait until the user resumes it
            if self.__timeStepToStop is not None and self.__timeStepToStop == self.__currentStep:
                #Let's set the stopping condition to true
                self.__stoppingCondition.set()
                #Let's wait until the user resumes the simulation
                self.__resumingCondition.wait()
                #Let's reset the stopping and resuming conditions
                self.__resumingCondition.clear()
                    
            if self.__currentStep % 60 == 0:
                print(f"[Running Sim]: Current step: {self.__currentStep}")
            
            if self.__numOfThreads > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.__numOfThreads) as executor:
                    _results = []
                    #Let's execute all the nodes in parallel
                    for _topology in self.__topologies:
                        for _node in _topology.nodes:
                            _result = executor.submit(_node.Execute)
                            _results.append(_result)
                    
                    #Once all the threads are done, we can check if there are any exceptions that were raised, then we can raise them
                    #If we don't do this, then the exceptions will be ignored and the nodes will be out of sync
                    for _result in _results:
                        _result.result() 
            else:
                for _topology in self.__topologies:
                    for _node in _topology.nodes:
                        _node.Execute()        
            self.__currentStep += 1 
            
        #Just to be sure, let's raise the stopping condition - some nodes might be waiting for it
        self.__stoppingCondition.set()
        
