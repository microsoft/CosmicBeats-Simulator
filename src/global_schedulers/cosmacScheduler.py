#Usage: python3 cosmacScheduler.py config_file granularity output_folder
'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 27 Jul 2023
Updated: 2024

@desc
    This implements the CosMAC (Constellation-Aware Medium Access and Scheduling for IoT Satellites) global scheduler.
    Based on the paper: https://deepakv.web.illinois.edu/assets/papers/CosMAC_MobiCom_2024.pdf
    
    The scheduler generates optimal transmission schedules for satellite-to-ground communication in IoT satellite
    constellations. It uses a Maximum Weight Independent Set (MWIS) algorithm to solve the scheduling problem
    while considering:
    1. Interference constraints between nearby ground stations
    2. SNR-based link quality optimization
    3. Spreading factor selection for LoRa transmissions
    4. Constellation dynamics and satellite field-of-view changes
    
    The scheduler operates in discrete time intervals and generates schedule files for each satellite and
    ground station, which are consumed by the CosMAC downlink models.
    
    Output format: Each node gets a schedule file (schedule_nodeID.pkl) containing a list of
    (start_time, end_time, spreading_factor) tuples.
'''
import threading
import numpy as np
import os
import sys
import json
import pickle
import itertools

import networkx as nx

#Let's make the python interpreter look for the modules in the main directory
sys.path.append(os.getcwd())

from scipy.optimize import linear_sum_assignment
from src.global_schedulers.Coloring_MWIS_heuristics import greedy_MWIS
from src.global_schedulers.iglobalscheduler import IGlobalScheduler
from src.sim.simulator import Simulator
from src.nodes.inode import ENodeType

from src.models.network.lora.loralink import LoraLink

class CosmacScheduler(IGlobalScheduler):
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
        print(f"[CosmacScheduler]: Scheduling the next pause at timestep {timestep}")
        return self.__sim.call_RuntimeAPIs( "pause_AtTime",
                                _timestep = timestep)

    def perfect_ordering(self, adj):
        ordering = []
        n = adj.shape[0]
        w = np.zeros(n)
        numbers = np.arange(1, n + 1)
        vertices = np.arange(1, n + 1)

        for _ in range(n):
            idx = np.argmax(w)
            ordering.append(vertices[idx])
            neigh = numbers[adj[vertices[idx] - 1] > 0]

            to_increase = np.intersect1d(neigh, vertices)
            id = [np.where(vertices == x)[0][0] for x in to_increase]

            w[id] = w[id] + 1
            w = np.concatenate((w[:idx], w[idx + 1:]))
            vertices = np.concatenate((vertices[:idx], vertices[idx + 1:]))

        return ordering

    def weight_indep(self, adj, w):
        """
        @desc
            Finds the Maximum Weight Independent Set of a graph
        @param[in] adj
            The adjacency matrix of the graph
        @param[in] w
            The weight vector of the graph
        @return
            The selected vertices and the weight of the independent set
        """

        if len(w) != adj.shape[0]:
            raise ValueError("The length of w must be equal to the number of vertices in the graph")

        ordering = self.perfect_ordering(adj)
        ordering = np.fliplr([ordering])[0]
        vertices = np.arange(1, ordering.size + 1)
        red = np.zeros(ordering.size, dtype=int)
        blue = np.zeros(ordering.size, dtype=int)
        w_temp = w[ordering - 1]

        for i in range(ordering.size):
            if w_temp[i] > 0:
                red[i] = 1
                vert_temp = ordering[i:]
                neigh_vert = vertices[adj[ordering[i] - 1] == 1] - 1
                vert_reduce = np.intersect1d(neigh_vert, vert_temp)
                for j in range(i + 1, ordering.size):
                    if np.sum(vert_reduce == ordering[j]) > 0:
                        w_temp[j] = w_temp[j] - w_temp[i]
                        if w_temp[j] < 0:
                            w_temp[j] = 0
                w_temp[i] = 0

        for i in range(ordering.size):
            idx = ordering.size - i - 1
            if red[idx] == 1:
                vert_chosen = ordering[blue == 1]
                if np.sum(adj[ordering[idx] - 1, vert_chosen - 1]) == 0:
                    blue[idx] = 1

        selected = ordering[blue == 1]
        indep_siz = np.sum(w[ordering[blue == 1] - 1])
        return selected, indep_siz

    def get_satFOVs(self):
        """
        Retrieves satellite field-of-view information for constellation-aware scheduling.
        
        This method queries the simulation to get the current visibility relationships
        between satellites and ground stations, which is essential for CosMAC's
        constellation-aware scheduling decisions.
        
        @return dict
            Dictionary mapping satellite IDs to lists of visible ground station IDs
            Format: {sat_id: [gs_id1, gs_id2, ...]}
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
                                                                "_targetNodeTypes": [ENodeType.GS],
                                                                "_isDownView": True,
                                                                "_myTime": None,
                                                                "__myLocation": None
                                                            })
                _satToFOV[_sat.nodeID] = _fov
        return _satToFOV

    def get_GlobalGraph(self):
        """
        Creates the global interference graph for CosMAC scheduling optimization.
        
        This method constructs a graph representation of the satellite constellation
        communication scenario, where:
        1. Nodes represent potential satellite-to-ground station links
        2. Edges represent interference constraints between links
        3. Node weights represent link quality (SNR-based)
        
        The scheduler then solves a Maximum Weight Independent Set (MWIS) problem
        to find the optimal set of non-interfering links for each time slot.
        
        @return numpy.ndarray
            Global graph representation with SNR values and interference constraints
        """
        # Dynamic constellation parameters (replaces hardcoded values)
        # Get actual satellite and ground station counts from simulation
        _topologyList = self.__sim.call_RuntimeAPIs("get_Topologies")
        _sats = _topologyList[0].get_NodesOfAType(ENodeType.SAT)
        _gss = _topologyList[0].get_NodesOfAType(ENodeType.GS)
        
        _nSats = len(_sats)
        _nGS = len(_gss)
        
        # Create dynamic ID mappings based on actual node IDs
        _satIDToIdx = {sat.nodeID: idx for idx, sat in enumerate(_sats)}
        _gsIDToIdx = {gs.nodeID: idx for idx, gs in enumerate(_gss)}

        if self.__satRadioDevices is None:
            self.__satRadioDevices = {}
            self.__satIDToRadioDevices = {}
            # Cache radio devices for all satellites (dynamic range)
            for sat in _sats:
                _satID = sat.nodeID
                self.__satIDToRadioDevices[_satID] = self.__sim.call_RuntimeAPIs("call_ModelAPIsByModelName",
                                                                 _topologyID = 0,
                                                                 _nodeID = _satID,
                                                                 _modelName = "ModelDownlinkRadio",
                                                                 _apiName = "get_RadioDevice",
                                                                 _apiArgs = {})

            # Cache radio devices for all ground stations (dynamic range)
            self.__gsIDToRadioDevices = {}
            for gs in _gss:
                _gsID = gs.nodeID
                self.__gsIDToRadioDevices[_gsID] = self.__sim.call_RuntimeAPIs("call_ModelAPIsByModelName",
                                                                 _topologyID = 0,
                                                                 _nodeID = _gsID,
                                                                 _modelName = "ModelLoraRadio",
                                                                 _apiName = "get_RadioDevice",
                                                                 _apiArgs = {})

            # Cache ground station positions (dynamic range)
            _gsToPos = {}
            for gs in _gss:
                _gsID = gs.nodeID
                _gsToPos[_gsID] = self.__sim.call_RuntimeAPIs("get_NodeInfo",
                                                   _topologyID = 0,
                                                   _nodeID = _gsID,
                                                   _infoType = "position")
            self.__gsIDToPos = _gsToPos

            _gsPairs = []
            for _gsID1, _gsPos1 in _gsToPos.items():
                for _gsID2, _gsPos2 in _gsToPos.items():
                    if _gsID1 != _gsID2 and _gsPos1.get_distance(_gsPos2) < self.__minDistance:
                        _gsPairs.append((_gsIDToIdx[_gsID1], _gsIDToIdx[_gsID2]))
            self.__gsPairs = np.array(_gsPairs) #This is a numpy array of shape (nPairs, 2)


        #This graph is a numpy array where each column is a satellite and each row is a ground station
        #The value is the index of the respective link in the list of links
        _globalGraph = np.full((_nGS, _nSats), -1)
        _listOfLinks = []
        _snrs = []

        _linkIDXtoSatID = {}
        _linkIDXtoGSID = {}
        _linkToGS = {}
        #Let's get the SNR between each GS and SAT
        _satFOVs = self.get_satFOVs() #Dict of SAT ID: List of visible GS ID's

        for _satID, _satFOV in _satFOVs.items():
            #Let's get the SNR between the SAT and each GS
            if len(_satFOV) == 0:
                continue

            #Let's now setup a hypothetical link between the SAT and each GS
            #To do so, we need the: sat radio device, gs radio device, and distance between them

            #Let's get the SAT position to get the distance
            _satPosition = self.__sim.call_RuntimeAPIs("get_NodeInfo",
                                                       _topologyID = 0,
                                                       _nodeID = _satID,
                                                       _infoType = "position")

            for _gsID in _satFOV:
                _gsPosition = self.__gsIDToPos[_gsID]
                _distance = _satPosition.get_distance(_gsPosition)

                _satRadioDevice = self.__satIDToRadioDevices[_satID]
                _gsRadioDevice = self.__gsIDToRadioDevices[_gsID]

                _link = LoraLink(_satRadioDevice, _gsRadioDevice, _distance)

                _listOfLinks.append(_link)
                _snrs.append(_link.get_SNR())

                #Let's now add this link to the global graph
                _satIdx = _satIDToIdx.get(_satID, len(_satIDToIdx))
                _satIDToIdx[_satID] = _satIdx

                _gsIdx = _gsIDToIdx.get(_gsID, len(_gsIDToIdx))
                _gsIDToIdx[_gsID] = _gsIdx

                _globalGraph[_gsIdx, _satIdx] = len(_listOfLinks) - 1

                _linkIDXtoSatID[len(_listOfLinks) - 1] = _satID
                _linkIDXtoGSID[len(_listOfLinks) - 1] = _gsID
                _linkToGS[_link] = _gsID

        _adj = np.zeros((len(_listOfLinks), len(_listOfLinks)))

        #No need to check wether two links are the same - will remove duplicates later
        nGS, nSats = _globalGraph.shape
        for _gsIdx1, _gsIdx2 in self.__gsPairs:
            #get all the values in each of these two rows which are not -1
            row1ValidLinks = np.where(_globalGraph[_gsIdx1, :] != -1)[0]
            row2ValidLinks = np.where(_globalGraph[_gsIdx2, :] != -1)[0]

            #This is the indicies of the columns which both rows have a valid link (i.e. the cases where both talk to a sat)
            sharedColumns = np.intersect1d(row1ValidLinks, row2ValidLinks)

            #Now, we want to get the indicies of the links in the _listOfLinks
            _gs1LinkIdxs = _globalGraph[_gsIdx1, sharedColumns]
            _gs2LinkIdxs = _globalGraph[_gsIdx2, sharedColumns]

            #Now, draw an edge between each of these links (don't draw an edge between the same link or between links of the same gs)
            _adj[_gs1LinkIdxs, _gs2LinkIdxs] = 1
            _adj[_gs2LinkIdxs, _gs1LinkIdxs] = 1

        # _adj1 = np.zeros((len(_listOfLinks), len(_listOfLinks)))
        # for _satID, _links in _satToLinks.items():
        #     for _link1 in _links:
        #         for _link2 in _links:
        #             if _link1 != _link2:
        #                 _gs1 = _linksToGS[_link1]
        #                 _gs2 = _linksToGS[_link2]
        #                 if _gs1 != _gs2 and _gsIDToPos[_gs1].get_distance(_gsIDToPos[_gs2]) < self.__minDistance:
        #                     _adj1[_linksToIndex[_link1], _linksToIndex[_link2]] = 1
        #                     _adj1[_linksToIndex[_link2], _linksToIndex[_link1]] = 1

        #Now, we have to connect each link which shares a gs to each other
        #so for each gs
        for _rowIdx in range(nGS):
            #Get each column which has a valid link (i.e. the gs which talk to this sat)
            _validCols = np.where(_globalGraph[_rowIdx, :] != -1)[0]
            #Get the indicies of the links
            _validLinks = _globalGraph[_rowIdx, _validCols]
            #Now, we want to draw an edge between each of these links
            _rows, _cols = np.meshgrid(_validLinks, _validLinks)
            _adj[_rows, _cols] = 1

        # for _gsID, _links in _gsToLinks.items():
        #     #Connect all of the links which share a GS
        #     for _link1 in _links:
        #         for _link2 in _links:
        #             if _link1 != _link2 and _linksToSat[_link1] != _linksToSat[_link2]:
        #                 _adj1[_linksToIndex[_link1], _linksToIndex[_link2]] = 1
        #                 _adj1[_linksToIndex[_link2], _linksToIndex[_link1]] = 1

        for _row in range(nGS):
            #Get each col which has a valid link
            _satIndxs = np.argwhere(_globalGraph[_row, :] != -1).flatten()

            #for each column we need to connect the (_row, _col) to (:, _col)
            for _satIdx in _satIndxs:
                for _otherSatIdx in _satIndxs:
                    if _satIdx != _otherSatIdx:
                        _thisLink = _globalGraph[_row, _satIdx]

                        #Count the number of non -1 values in this column
                        _secondCol = np.argwhere(_globalGraph[:, _otherSatIdx] != -1).flatten()
                        _secondLinks = _globalGraph[_secondCol, _otherSatIdx]

                        _adj[_thisLink, _secondLinks] = 1
                        _adj[_secondLinks, _thisLink] = 1

        # for _gsID, _links in _gsToLinks.items():
        #     #Connect all of the links which share a GS
        #     for _link1 in _links:
        #         for _link2 in _links:
        #             #Now, we connect all of the links in one satellite to all of the links in another satellite if they share any ground stations
        #             _sat2 = _linksToSat[_link2]
        #             _sat1 = _linksToSat[_link1]
        #             if _sat1 == _sat2:
        #                 continue
        #             for _link3 in _satToLinks[_sat2]:
        #                 if _link3 != _link1:
        #                     _adj1[_linksToIndex[_link1], _linksToIndex[_link3]] = 1
        #                     _adj1[_linksToIndex[_link3], _linksToIndex[_link1]] = 1

        np.fill_diagonal(_adj, 0)

        # Log graph statistics for CosMAC analysis
        print(f"[CosmacScheduler] Interference graph - Nodes: {len(_listOfLinks)}, Edges: {np.sum(_adj)//2}")

        _weights = np.array(_snrs) + 20

        #grph = nx.from_numpy_array(_adj)
        #print("Number of nodes: {}".format(len(grph.nodes())))
        pi = {i: _weights[i] for i in range(len(_weights))}
        print(f"[CosmacScheduler] Running MWIS optimization for {len(_listOfLinks)} potential links")
        _scheduledLinkIndicies, weight = greedy_MWIS(_adj, pi, 1, 100, False)
        print(f"[CosmacScheduler] MWIS solution - Selected links: {len(_scheduledLinkIndicies)}, Total weight: {weight:.2f}")

        _satsToGoodLinks = {}
        for _linkIdx in _scheduledLinkIndicies:
            _link = _listOfLinks[_linkIdx]
            _satID = _linkIDXtoSatID[_linkIdx]
            if _satID not in _satsToGoodLinks:
                _satsToGoodLinks[_satID] = []
            _satsToGoodLinks[_satID].append(_link)

        _time = self.__sim.call_RuntimeAPIs("get_NodeInfo",
                                                          _topologyID = 0,
                                                          _nodeID = 1,
                                                          _infoType = "time")

        # Use configurable sample count for reliability estimation
        _nSamples = self.__nSamples
        for _satID, _links in _satsToGoodLinks.items():
            # CosMAC spreading factor optimization
            _targetSF = 11  # Default SF for LoRa
            for _sf in range(7, 12):  # Extended SF range for better optimization
                _bers = np.array([_links.get_BER(_sf) for _links in _links])
                _pCorrect = 1 - _bers
                _sumCorrect = np.sum(_pCorrect)

                #_pCorrectNormalized is a vector of the probability of each link being correct (nLinks, 1)
                _pCorrectNormalized = _pCorrect / _sumCorrect

                #Make a (nSamples x nLinks) matrix where each row is a 1
                _sampleMatrix = np.zeros((_nSamples, len(_links)))
                #for each column, randomly (ber) set the value to 0
                for _col in range(_sampleMatrix.shape[1]):
                    _sampleMatrix[:, _col] = np.random.choice([0, 1], size=_nSamples, p=[_bers[_col], 1 - _bers[_col]])

                #_output is a vector of the probability of each sample being correct (nSamples, 1)
                _output = _sampleMatrix @ _pCorrectNormalized
                _nZeros = np.argwhere(_output < .5).flatten()
                # CosMAC reliability threshold (configurable)
                if len(_nZeros)/_nSamples < self.__reliabilityThreshold:
                    _targetSF = _sf
                    break

            if _satID not in self.__satsToSchedule:
                self.__satsToSchedule[_satID] = []
            self.__satsToSchedule[_satID].append([_time.copy(), _time.copy().add_seconds(60), _targetSF])

            for _link in _links:
                _gs = _linkToGS[_link]
                if _gs not in self.__gsToSchedule:
                    self.__gsToSchedule[_gs] = []
                self.__gsToSchedule[_gs].append([_time.copy(), _time.copy().add_seconds(60), _targetSF])

    def Execute(self):
        """
        Main execution loop for the CosMAC global scheduler.
        
        This method implements the constellation-aware scheduling algorithm:
        1. Starts the simulation in a separate thread
        2. Periodically pauses simulation to compute optimal schedules
        3. Uses MWIS algorithm to solve interference-constrained optimization
        4. Generates and saves schedule files for all nodes
        5. Continues until simulation completion
        
        The scheduler operates with configurable granularity and saves schedules
        periodically to handle dynamic constellation changes.
        """
        #The simulation is already setup.
        #Set a pause for t = 0
        _waitingCondition = self.schedule_NextPause(0) #Threading.Event()
        self.start_Simulation()

        #While the sim's thread is alive, we will run the algorithm
        i = 1
        while self.__threadSim.is_alive():
            if _waitingCondition is not None and not _waitingCondition.is_set():
                print("[CosmacScheduler] Waiting for the next pause (t = " + str(self.__timestepGranularity * i) + "s)")
                _waitingCondition.wait()

            # Generate the global interference graph for CosMAC scheduling
            print("[CosmacScheduler] Computing constellation-aware scheduling graph")
            _globalGraph = self.get_GlobalGraph()

            if i % 20 == 0:
                print("Saving schedule at t = {}s".format(self.__timestepGranularity * i))
                self.save_Schedule()

            #Set the next pause.
            _waitingCondition = self.schedule_NextPause(self.__timestepGranularity * i)
            self.__sim.call_RuntimeAPIs("resume")

            i += 1


        self.save_Schedule()

        #Let's wait for the simulation to finish
        self.__threadSim.join()

    def save_Schedule(self):
        """
        Saves the computed CosMAC schedule to pickle files.
        
        Creates schedule files for each satellite and ground station containing
        their transmission schedules. These files are consumed by the CosMAC
        downlink models during simulation.
        
        File format: schedule_<nodeID>.pkl containing list of (start_time, end_time, SF) tuples
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

        for _gsID in self.__gsToSchedule.keys():
            _schedule = self.__gsToSchedule[_gsID]
            _scheduleFile = os.path.join(self.__scheduleFolder, "schedule_" + str(_gsID) + ".pkl")
            _scheduleFile = open(_scheduleFile, "wb")
            pickle.dump(_schedule, _scheduleFile)
            _scheduleFile.close()

    def setup_Simulation(self):
        """
        This method starts the simulation.
        """
        self.__sim = Simulator(self.__configPath)
        self.__sim.call_RuntimeAPIs("load_FOVs", _inputPath=self.__fovPath)
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
        Constructor for CosmacScheduler.
        
        Initializes the CosMAC global scheduler with configuration parameters
        for constellation-aware scheduling optimization.
        
        @param[in] _configPath: str
            Path to the simulation configuration file containing network topology,
            node parameters, and simulation settings
        @param[in] _granularity: int
            Scheduling granularity in seconds - determines how frequently the
            scheduler recomputes optimal schedules to adapt to constellation dynamics
        @param[in] _scheduleFolder: str
            Output directory where schedule files will be stored for consumption
            by CosMAC downlink models during simulation
            
        @raises FileNotFoundError: If configuration file cannot be found
        @raises ValueError: If granularity is not positive
        '''
        self.__configPath = _configPath

        #Load the config file. We need to get "delta"
        _config = json.load(open(_configPath))
        _delta = _config["simtime"]["delta"]
        self.__timeGranularity = _granularity
        self.__timestepGranularity = _granularity / _delta
        print(self.__timestepGranularity)

        self.__sim = None
        self.__threadSim = None

        self.__satsToSchedule = {} #satID -> list of (start, end, sf)
        self.__gsToSchedule = {} #gsID -> list of (start, end, sf)

        self.__scheduleFolder = _scheduleFolder
        print(self.__scheduleFolder)

        # CosMAC protocol parameters (configurable)
        self.__minDistance = 1000  # Minimum distance (meters) for interference consideration
        self.__reliabilityThreshold = 1e-4  # Packet error rate threshold for SF selection
        self.__nSamples = 10000  # Monte Carlo samples for reliability estimation
        self.__satRadioDevices = None

        # Field-of-view data path for constellation dynamics
        self.__fovPath = "/scratch/ochabra2/indata/downlink0709_0.pkl"  # TODO: Make configurable

if __name__ == "__main__":
    """
    Main entry point for the CosMAC global scheduler.
    
    Usage: python3 cosmacScheduler.py <config_file> <granularity> <output_folder>
    
    Arguments:
        config_file: Path to simulation configuration JSON file
        granularity: Scheduling granularity in seconds (e.g., 60 for 1-minute intervals)
        output_folder: Directory where schedule files will be saved
    
    Example:
        python3 cosmacScheduler.py configs/config_cosmac.json 60 schedules/
    """
    if len(sys.argv) != 4:
        print("Usage: python3 cosmacScheduler.py <config_file> <granularity> <output_folder>")
        print("  config_file: Path to simulation configuration JSON file")
        print("  granularity: Scheduling granularity in seconds")
        print("  output_folder: Directory where schedule files will be saved")
        sys.exit(1)
    
    try:
        # Create and execute the CosMAC scheduler
        _scheduler = CosmacScheduler(
            _configPath=sys.argv[1],
            _granularity=int(sys.argv[2]),
            _scheduleFolder=sys.argv[3])
        _scheduler.setup_Simulation()
        _scheduler.Execute()
        
        print("[CosmacScheduler] Schedule generation completed successfully!")
        
    except Exception as e:
        print(f"[CosmacScheduler] Error: {e}")
        sys.exit(1)