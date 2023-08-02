#Usage python3 hungarianscheduler.py config_file granularity output_folder
'''
Created by: Om Chabra
Created on: 27 Jul 2023
@desc
    This implements the global scheduler which will be used to schedule the nodes in the simulation
    It runs a hungarian algorithm to find the optimal schedule for every minute. 
    
    This is based (but not wholly) on the paper: https://dl.acm.org/doi/pdf/10.1145/3452296.3472932
    
    It will store the schedule in a folder (passed as an argument to the init method)
    Each node will have a file in this folder of the form: schedule_nodeID.pkl
'''
import threading
import numpy as np
import os
import sys
import json
import pickle

#Let's make the python interpreter look for the modules in the main directory
sys.path.append(os.getcwd())

from scipy.optimize import linear_sum_assignment
from src.global_schedulers.iglobalscheduler import IGlobalScheduler
from src.sim.simulator import Simulator
from src.nodes.inode import ENodeType

from src.models.network.imaging.imaginglink import ImagingLink
class HungarianScheduler(IGlobalScheduler):  
    def call_APIs(
            self, 
            _apiName: str, 
            **_kwargs):
        '''
        This method acts as an API interface of the SMA. 
        An API offered by the SMA can be invoked through this method.
        @param[in] _apiName
            Name of the API. Each SMA should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        pass
    
    def schedule_NextPause(self, timestep):
        """
        @desc
            This method schedules the next pause for the simulator.
            See the ManagerParallel pause API for more details.
        @param[in] timestep
            The timestep at which the simulation should be paused
        @return
            a threading.Condition() object which will be notified when the simulation is paused
        """
        print(f"[HungarianScheduler]: Scheduling the next pause at timestep {timestep}")
        return self.__sim.call_RuntimeAPIs( "pause_AtTime",
                                _timestep = timestep)
    
    def get_satFOVs(self):
        """
        @desc
            This method gets the SAT FOV's from the simulation.
        @return
            A dictionary of SAT ID: List of visible GS ID's
        """
        _topologyList = self.__sim.call_RuntimeAPIs("get_Topologies")
        assert len(_topologyList) == 1, "This scheduler only works with one topology"
        
        _satToFOV = {} #Dict of Satellite ID: List of visible GS ID's
        for _topologyIdx in range(len(_topologyList)):     
            _sats = _topologyList[_topologyIdx].get_NodesOfAType(ENodeType.SAT)
            for _sat in _sats:
                _fov = self.__sim.call_RuntimeAPIs("call_ModelAPIsByModelName",
                                                            _topologyID = _topologyIdx,
                                                            _nodeID = _sat.nodeID,
                                                            _modelName = "ModelFovTimeBased",
                                                            _apiName = "get_View",
                                                            _apiArgs = {
                                                                "_targetNodeTypes": [ENodeType.GS]
                                                            })
                _satToFOV[_sat.nodeID] = _fov
        return _satToFOV
    
    def get_GlobalGraph(self):
        """
        @desc
            This method creates the global graph for the bipartite scheduler.
        @return
            A numpy array of the SNR between each SAT and GS
        """
        if self.__sats is None:
            self.__sats = self.__sim.call_RuntimeAPIs("get_Topologies")[0].get_NodesOfAType(ENodeType.SAT)
            self.__gs = self.__sim.call_RuntimeAPIs("get_Topologies")[0].get_NodesOfAType(ENodeType.GS)
            
            for _sat in self.__sats:
                self.__satsToSchedule[_sat.nodeID] = [] 
        
            self.__nSat = len(self.__sats)
            self._nGS = len(self.__gs)
            
            self.__satIDsToIdx = {_sat.nodeID: _idx for _idx, _sat in enumerate(self.__sats)}
            self.__gsIDsToIdx = {_gs.nodeID: _idx for _idx, _gs in enumerate(self.__gs)}

        #Sats are rows, GS are columns
        verySmallNumber = -1000000
        _snrGraph = np.full((self.__nSat, self._nGS), verySmallNumber)
        
        #Let's get the SNR between each GS and SAT
        _satFOVs = self.get_satFOVs() #Dict of SAT ID: List of visible GS ID's
        for _satID, _satFOV in _satFOVs.items():
            #Let's get the SNR between the SAT and each GS
            if len(_satFOV) == 0:
                continue
            
            #Let's now setup a hypothetical link between the SAT and each GS
            #To do so, we need the: sat radio device, gs radio device, and distance between them
            _satRadioDevice = self.__sim.call_RuntimeAPIs("call_ModelAPIsByModelName",
                                                            _topologyID = 0,
                                                            _nodeID = _satID,
                                                            _modelName = "ModelImagingRadio",
                                                            _apiName = "get_RadioDevice",
                                                            _apiArgs = {})
            
            #Let's get the SAT position to get the distance
            _satPosition = self.__sim.call_RuntimeAPIs("get_NodeInfo", 
                                                       _topologyID = 0, 
                                                       _nodeID = _satID, 
                                                       _infoType = "position")
            
            for _gsID in _satFOV:
                _gsRadioDevice = self.__sim.call_RuntimeAPIs("call_ModelAPIsByModelName",
                                                             _topologyID = 0,
                                                             _nodeID = _gsID,
                                                             _modelName = "ModelImagingRadio",
                                                             _apiName = "get_RadioDevice", 
                                                             _apiArgs = {})
                
                #Get GS position
                _gsPosition = self.__sim.call_RuntimeAPIs("get_NodeInfo", 
                                                          _topologyID = 0, 
                                                          _nodeID = _gsID, 
                                                          _infoType = "position")
                _distance = _satPosition.get_distance(_gsPosition)
                
                _link = ImagingLink(_satRadioDevice, _gsRadioDevice, _distance)
                _snrGraph[self.__satIDsToIdx[_satID], self.__gsIDsToIdx[_gsID]] = _link.get_SNR()
                
        return _snrGraph

    def __run_Algorithm(self, _snrGraph):
        """
        @desc
            This method runs the algorithm to assign SATs to GSs.
        """
        _time = self.__sim.call_RuntimeAPIs("get_NodeInfo", 
                                                          _topologyID = 0, 
                                                          _nodeID = 1, 
                                                          _infoType = "time")
        _rowInds, _colInds = linear_sum_assignment(_snrGraph, maximize=True) 
        #Let's now assign the SATs to the GSs
        for _rowInd, _colInd in zip(_rowInds, _colInds):
            _satID = self.__sats[_rowInd].nodeID
            _gsID = self.__gs[_colInd].nodeID
            
            if _snrGraph[_rowInd, _colInd] == -1000000:
                _gsID = None
        
            self.__satsToSchedule[_satID].append((_gsID, _time.copy(), _time.add_seconds(self.__timeGranularity)))
            print("[HungarianScheduler]: Assigning SAT {} to GS {} at time {}".format(_satID, _gsID, _time))
        
    def Execute(self):
        """
        This method executes the tasks that needed to be performed by the SMA.
        """
        #The simulation is already setup.
        #Set a pause for t = 0
        _waitingCondition = self.schedule_NextPause(0) #Threading.Event()
        self.start_Simulation()
                
        #While the sim's thread is alive, we will run the algorithm
        i = 1
        while self.__threadSim.is_alive():
            if _waitingCondition is not None and not _waitingCondition.is_set():
                _waitingCondition.wait()
                                
            #Let's get the global graph
            _globalGraph = self.get_GlobalGraph()
            
            #Let's assign the right gs
            self.__run_Algorithm(_globalGraph)
            
            #Set the next pause. 
            _waitingCondition = self.schedule_NextPause(self.__timestepGranularity * i)
            self.__sim.call_RuntimeAPIs("resume")

            i += 1                        
             
        self.save_Schedule()
        
        #Let's wait for the simulation to finish
        self.__threadSim.join()

    def save_Schedule(self):
        """
        This method saves the schedule to a file. 
        """
        #Let's create the schedule folder if it doesn't exist
        if not os.path.exists(self.__scheduleFolder):
            os.makedirs(self.__scheduleFolder)
        
        #Let's now save the schedule
        for _satID in self.__satsToSchedule.keys():
            _schedule = self.__satsToSchedule[_satID]
            _scheduleFile = os.path.join(self.__scheduleFolder, "schedule_" + str(_satID) + ".pkl")
            _scheduleFile = open(_scheduleFile, "wb")
            pickle.dump(_schedule, _scheduleFile)
            _scheduleFile.close()
        
            
    def setup_Simulation(self):
        """
        This method starts the simulation.
        """
        self.__sim = Simulator(self.__configPath)
        #We need to run the simulation in a separate thread
        self.__threadSim = threading.Thread(target=self.__sim.execute)

    def start_Simulation(self):
        """
        This method starts the simulation.
        """
        self.__threadSim.start()
    
    def __init__(self,
                 _configPath,
                 _granularity,
                 _scheduleFolder):
        '''
        @desc
            Constructor
        @param[in] _configPath
            Path to the config file of the simulation
        @param[in] _granularity
            Granularity of the schedule in seconds
        @param[in] _scheduleFolder
            Folder where the schedule will be stored
        '''
        self.__configPath = _configPath
        
        #Load the config file. We need to get "delta"
        _config = json.load(open(_configPath))
        _delta = _config["simtime"]["delta"]
        self.__timeGranularity = _granularity
        self.__timestepGranularity = _granularity / _delta
        
        self.__sim = None
        self.__threadSim = None
        
        self.__sats = None
        self.__satsToSchedule = {}
        
        self.__scheduleFolder = _scheduleFolder

if __name__ == "__main__":
    #Let's create the scheduler
    _scheduler = HungarianScheduler(
        _configPath=sys.argv[1],
        _granularity=int(sys.argv[2]),
        _scheduleFolder=sys.argv[3])
    _scheduler.setup_Simulation()
    _scheduler.Execute()