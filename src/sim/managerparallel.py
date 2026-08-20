# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

'''
Created by: Tusher Chakraborty
Created on: 13 Dec 2022
@desc
    This module implements the ManagerParallel class of the simulator.
    It leverages the parallel computing capabilities offered by Python

    [MODIFIED]: Integrated GeminiBrain & MECOrchestrator directly into the simulation loop.
'''
import concurrent.futures
import pickle
import queue
import threading
import multiprocessing as mp
import time
import numpy as np

# --- MEC INTEGRATION ---
from src.ai_logic import MECOrchestrator
# -----------------------

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
        return self.__topologies
    
    __reqHandlerDictionary = {
        EManagerReqType.GET_TOPOLOGIES : __get_Topologies
    }
    
    def req_Manager(self, _reqType: EManagerReqType, **_kwargs):
        _ret = None
        try:
            _ret = self.__reqHandlerDictionary[_reqType](self, **_kwargs)
        except:
            print("[Simulator Warning]: An unhandled request has been received in the req_Manager() method.")
        return _ret
    
    # The definition of API handlers (Mantidos originais para compatibilidade)
    def __call_ModelAPIsByModelName(self, **_kwargs):
        if ("_topologyID" not in _kwargs) or ("_nodeID" not in _kwargs) or \
            ("_modelName" not in _kwargs) or ("_apiName" not in _kwargs):
            raise Exception("[API: call_ModelAPIsByModelName]: The keyworded arguments are not complete for the API")
        
        _topologyID = _kwargs["_topologyID"]
        _nodeID = _kwargs["_nodeID"]
        _modelName = _kwargs["_modelName"]
        _apiName = _kwargs["_apiName"]
        _apiArgs = _kwargs["_apiArgs"]

        try:
            _node = self.__topologies[_topologyID].get_Node(_nodeID)
        except:
            raise Exception("[API: call_ModelAPIsByModelName]: The node instance could not be found in the topology")
        
        try:
            _model = _node.has_ModelWithName(_modelName)
        except Exception as e:
            raise Exception(f"[API: call_ModelAPIsByModelName]: The model instance could not be found in the node due to {e}")
        
        try:
            _ret = _model.call_APIs(_apiName, **_apiArgs)
        except Exception as e:
            raise Exception(f"[API: call_ModelAPIsByModelName]: The {_apiName} could not be called from the model {_modelName} due to {e}")

        return _ret     

    def __get_NodeInfo(self, **_kwargs):
        if ("_topologyID" not in _kwargs) or ("_nodeID" not in _kwargs) or ("_infoType" not in _kwargs):
            raise Exception("[API: get_NodeInfo]: The keyworded arguments are not complete for the API")
        
        _topologyID = _kwargs["_topologyID"]
        _nodeID = _kwargs["_nodeID"]
        _infoType = _kwargs["_infoType"]

        try:
            _node = self.__topologies[_topologyID].get_Node(_nodeID)
        except:
            raise Exception("[API: get_NodeInfo]: The node instance could not be found in the topology")
        
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
        if ("_timestep" not in _kwargs):
            raise Exception("[API: __pause_AtTime]: The keyworded arguments are not complete for the API")
        
        _pauseTimeStep = _kwargs["_timestep"]
        _currentTimeStep = self.__currentStep

        if _pauseTimeStep < _currentTimeStep:
            return None
        else:
            self.__timeStepToStop = _pauseTimeStep
            return self.__stoppingCondition
        
    def __resume(self, **_kwargs):
        self.__stoppingCondition.clear()
        self.__resumingCondition.set()
        
    def __compute_FOVs(self, **_kwargs):
        _numProcesses = mp.cpu_count()
        if ("_numProcesses" in _kwargs):
            _numProcesses = _kwargs["_numProcesses"]
        
        _nodeQueue = mp.Queue()
        _fovQueue = mp.Queue()

        def __processMethod():     
            try:
                _lastNodeID = -1
                while True:
                    try:
                        _satID = _nodeQueue.get(timeout=1)
                        self.__call_ModelAPIsByModelName(_topologyID = 0, _nodeID = _satID, _modelName = "ModelOrbit", _apiName = "setup_Skyfield", _apiArgs = {})
                        self.__call_ModelAPIsByModelName(_topologyID = 0, _nodeID = _satID, _modelName = "ModelFovTimeBased", _apiName = "find_Passes", _apiArgs = {"_targetNodeTypes" : [ENodeType.GS, ENodeType.IOTDEVICE]})
                        _lastNodeID = _satID
                    except queue.Empty: break
                    except Exception as _e:
                        print(f"[API: compute_FOVs]: An exception occurred: {_e}")
                        exit(1)
                
                if _lastNodeID != -1:
                    _dict = self.__call_ModelAPIsByModelName(_topologyID = 0, _nodeID = _satID, _modelName = "ModelFovTimeBased", _apiName = "get_GlobalDictionary", _apiArgs = {})
                    _fovQueue.put(_dict)
            except Exception as _e:
                print(f"[API: compute_FOVs]: An exception occurred: {_e}")
                exit(1)
            return
        
        assert len(self.__topologies) == 1, "[API: compute_FOVs]: Only supported for single topology"
        _sats = self.__topologies[0].get_NodesOfAType(ENodeType.SAT)
        for _sat in _sats:
            self.__call_ModelAPIsByModelName(_topologyID = 0, _nodeID = _sat.nodeID, _modelName = "ModelOrbit", _apiName = "remove_Skyfield", _apiArgs = {})
            _nodeQueue.put(_sat.nodeID)
            
        _processes = []
        for _ in range(_numProcesses):
            _process = mp.Process(target=__processMethod)
            _processes.append(_process)
            _process.start()
        
        _processDicts = []
        while True:
            _allDone = True
            for _process in _processes:
                if _process.is_alive():
                    _allDone = False
                    break
            if _allDone: break
            else:
                time.sleep(1)
                while not _fovQueue.empty(): _processDicts.append(_fovQueue.get())
        
        for _process in _processes: _process.join()
                
        _outputFOV = {}
        for _fovDict in _processDicts:
            for _nodeID, _fovArray in _fovDict.items():
                if _fovArray is None or _fovArray.shape[0] == 0: continue
                _thisList = _outputFOV.get(_nodeID, None)
                if _thisList is None: _thisList = _fovArray
                else: _thisList = np.concatenate((_thisList, _fovArray), axis=0)
                _outputFOV[_nodeID] = _thisList

        self.__call_ModelAPIsByModelName(_topologyID = 0, _nodeID = _sats[0].nodeID, _modelName = "ModelFovTimeBased", _apiName = "set_GlobalDictionary", _apiArgs = {"_globalDictionary" : _outputFOV})
        
        for _sat in _sats:
            self.__call_ModelAPIsByModelName(_topologyID = 0, _nodeID = _sat.nodeID, _modelName = "ModelOrbit", _apiName = "setup_Skyfield", _apiArgs = {})

        if ("_outputPath" in _kwargs):
            with open(_kwargs["_outputPath"], "wb") as _f: pickle.dump(_outputFOV, _f)
            
    def __load_FOVs(self, **_kwargs):
        _inputPath = _kwargs["_inputPath"]
        with open(_inputPath, "rb") as _f:
            _fovDict = pickle.load(_f)
            self.__call_ModelAPIsByModelName(_topologyID = 0, _nodeID = 0, _modelName = "ModelFovTimeBased", _apiName = "set_GlobalDictionary", _apiArgs = {"_globalDictionary" : _fovDict})
    
    def __run_OneStep(self, **_kwargs):
        for _topology in self.__topologies:
            for _node in _topology.nodes:
                _node.Execute()

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

    def call_APIs(self, _api: str, **_kwargs):
        _ret = None
        try:
            _ret = self.__apiHandlerDictionary[_api](self, **_kwargs)
        except Exception as e:     
            print(f"[Runtime API Manager]: An exeption has been raised while executing the API: {e}")
        return _ret

    def __init__(self, **_simEnv):
        self.__topologies = _simEnv["topologies"]
        self.__numOfSteps = int(_simEnv["numOfSimSteps"])
        self.__numOfThreads = int(_simEnv["numOfWorkers"])
        
        self.__currentStep = 0
        self.__timeStepToStop = None
        
        self.__stoppingCondition = threading.Event()
        self.__resumingCondition = threading.Event()
        
        for _topology in self.__topologies:
            for _node in _topology.nodes:
                _node.add_ManagerInstance(self) 

        # --- MEC INJECTION START ---
        print(">>> [MEC] ManagerParallel Initialized. Setting up AI...")
        # Como o MECOrchestrator agora cria o seu próprio motor, só precisas disto:
        self.mec_orchestrator = MECOrchestrator()
        
        # Extrai nós das topologias para configurar
        all_nodes = []
        if isinstance(self.__topologies, dict):
             for t in self.__topologies.values(): 
                 if hasattr(t, 'nodes'): all_nodes.extend(t.nodes)
        elif isinstance(self.__topologies, list):
             for t in self.__topologies: 
                 if hasattr(t, 'nodes'): all_nodes.extend(t.nodes)
        
        self.mec_orchestrator.setup_nodes(all_nodes)
        # --- MEC INJECTION END ---
                
                                
    def run_Sim(self):
        '''
        @desc
            This method is called to run the simulation.
        '''
        # To keep the nodes in sync, we ensure that the threads join at the end of each step.
        while self.__currentStep < self.__numOfSteps:
            
            # Pause logic
            if self.__timeStepToStop is not None and self.__timeStepToStop == self.__currentStep:
                self.__stoppingCondition.set()
                self.__resumingCondition.wait()
                self.__resumingCondition.clear()
                    
            if self.__currentStep % 60 == 0:
                print(f"[Running Sim]: Current step: {self.__currentStep}")
            
            # --- COSMIC BEATS PHYSICS (Original) ---
            if self.__numOfThreads > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.__numOfThreads) as executor:
                    _results = []
                    for _topology in self.__topologies:
                        for _node in _topology.nodes:
                            _result = executor.submit(_node.Execute)
                            _results.append(_result)
                    for _result in _results:
                        _result.result() 
            else:
                for _topology in self.__topologies:
                    for _node in _topology.nodes:
                        _node.Execute()
            # ---------------------------------------

            # --- MEC ORCHESTRATION (Injected) ---
            # Assume delta=5.0s (padrão no config.json)
            # Precisamos do tempo absoluto em segundos para o escalonador
            simulation_time = self.__currentStep * 5.0 
            self.mec_orchestrator.step(simulation_time)
            # ------------------------------------

            self.__currentStep += 1 
        
        # --- MEC REPORT ---
        if hasattr(self, 'mec_orchestrator'):
            self.mec_orchestrator.print_stats()
            self.mec_orchestrator.save_metrics()
        # ------------------

        self.__stoppingCondition.set()