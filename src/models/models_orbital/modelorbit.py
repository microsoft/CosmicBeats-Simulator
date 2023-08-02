"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on: 27 Oct 2022

@desc
    This module implements the orbital propagation model for the satellite.  
"""
import numpy as np
from datetime import datetime, timedelta

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from skyfield.api import load, wgs84, EarthSatellite
from skyfield.framelib import itrs
from skyfield.positionlib import build_position, Barycentric
from src.utils import Location, Time

class ModelOrbit(IModel):
    '''
    This model class basically calculates the orbital propagation of the satellite based on the TLE.
    It takes the timestamp of the node and updates the location of the node, i.e., satellite
    '''
    __modeltag = EModelTag.ORBITAL
    __ownernode: INode
    __supportednodeclasses = ['SatelliteBasic'] #List of node classes that this model supports
    __dependencies = []
    __earthsatellite: EarthSatellite
    __logger: ILogger
    
    @property
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the model class. For example, 'ModelPower' 
        """
        return self.__class__.__name__
    
    @property
    def modelTag(self) -> EModelTag:
        """
        @type
            EModelTag
        @desc
            The model tag for the implemented model
        """
        return self.__modeltag

    @property
    def ownerNode(self):
        """
        @type
            INode
        @desc
            Instance of the owner node that incorporates this model instance.
            The subclass (implementing a model) should keep a private variable holding the owner node instance. 
            This method can return that variable.
        """
        return self.__ownernode
    
    @property
    def supportedNodeClasses(self) -> 'list[str]':
        '''
        @type
            List of string
        @desc
            A model may not support all the node implementation. 
            supportedNodeClasses gives the list of names of the node implementation classes that it supports.
            For example, if a model supports only the SatBasic and SatAdvanced, the list should be ['SatBasic', 'SatAdvanced']
            If the model supports all the node implementations, just keep the list EMPTY.
        '''
        return  self.__supportednodeclasses
    
    @property
    def dependencyModelClasses(self) -> 'list[list[str]]':
        '''
        @type
            Nested list of string
        @desc
            dependencyModelClasses gives the nested list of name of the model implementations that this model has dependency on.
            For example, if a model has dependency on the ModelPower and ModelOrbitalBasic, the list should be [['ModelPower'], ['ModelOrbitalBasic']].
            Now, if the model can work with EITHER of the ModelOrbitalBasic OR ModelOrbitalAdvanced, the these two should come under one sublist looking like [['ModelPower'], ['ModelOrbitalBasic', 'ModelOrbitalAdvanced']]. 
            So each exclusively dependent model should be in a separate sublist and all the models that can work with either of the dependent models should be in the same sublist.
            If your model does not have any dependency, just keep the list EMPTY. 
        '''
        return self.__dependencies
    
    def __in_Sunlight(self, **_kwargs) -> bool:
        '''
        This method checks if the satellite is in sunlight. Since sunlight calculations are very expensive,
        this uses a binary search to find when the satellite switches from sunlight to darkness or vice versa and then 
        uses that information to find the sunlight status for the current time.
        
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this method
        @return
            True if the satellite is in sunlight, false otherwise
        '''
        if self.__timesAndSunlight is None:
            #Let's calculate all the sunlight times at once for the whole simulation
            _startTime = self.__ownernode.simStartTime.to_datetime()
            _endTime = self.__ownernode.simEndTime.to_datetime()
            assert _startTime < _endTime, "Start time should be less than end time"
            
            _secondsInSimulation =  (_endTime - _startTime).total_seconds()
            
            #For a LEO, it takes 90 min for one orbit, and about 60% of the time is spent in sunlight
            #This means that about 30 min is spent in darkness
            
            #We want to ensure that we don't miss any switches from sunlight to darkness or vice versa
            #So let's start the search at every 15 minutes
            
            _granularity = 15 * 60
            
            #If the simulation is less, than let's use the simulation time as the starting granularity
            if _secondsInSimulation < _granularity:
                _granularity = _secondsInSimulation
                
            #Let's setup some lambdas so we can keep calling them multiple times
            _convertDatetimeToSkyfieldTime = lambda _datetime: self.__skyfieldts.utc(_datetime.year, _datetime.month, _datetime.day, \
                _datetime.hour, _datetime.minute, _datetime.second)
            _getSunlit = lambda _times: self.__earthsatellite.at(_times).is_sunlit(self.__ephem)
            
            #Let's first find the sunlight status for our starting granularity
            _times = self.__skyfieldts.utc(_startTime.year, _startTime.month, _startTime.day, \
                _startTime.hour, _startTime.minute, np.arange(0, (_endTime - _startTime).total_seconds(), _granularity))
            
            _sunlits = _getSunlit(_times)
            
            #Now, let's find all the times when the status changes
            #Find all the indexes where it switches from T to F or F to T
            _sunlitIndexes = np.where(np.diff(_sunlits) != 0)[0] #This is an array of indexes. This is the index of the first element of the pair
            
            _endTimesAndSunlight = [] #tuple of (datetime, bool)
            
            #Now, we need to find the exact timestep when the status changes. Let's keep binary searching until we reach the desired granularity
            _desiredGranularity = self.__ownernode.deltaTime 
            for _index in _sunlitIndexes:
                _currentGranularity = _granularity
                _startInSunlight = _sunlits[_index]
                
                _currentStartTime = _startTime + timedelta(seconds = float(_index * _granularity))
                _currentEndTime = _currentStartTime + timedelta(seconds = _currentGranularity)
                
                while _currentGranularity > _desiredGranularity:
                    #Let's calculate the midpoint's state between the start and end time
                    _midTime = _currentStartTime + timedelta(seconds = _currentGranularity / 2)
                    _midInSunlight = _getSunlit(_convertDatetimeToSkyfieldTime(_midTime))
                    
                    if _midInSunlight == _startInSunlight:
                        #The switch happens in the right half
                        _currentStartTime = _midTime
                    else:
                        #The switch happens in the left half
                        _currentEndTime = _midTime
                        
                    _currentGranularity = (_currentEndTime - _currentStartTime).total_seconds()
                
                _endTimesAndSunlight.append((_currentEndTime, not _startInSunlight))
                        
            _timesAndSunlight = []
            #Now, let's create a list of (timeToChange, isSunlit) tuples
            for _endDateTimeAndSunlight in _endTimesAndSunlight:
                _time = Time().from_datetime(_endDateTimeAndSunlight[0])
                _sunlit = _endDateTimeAndSunlight[1]
                _timesAndSunlight.append((_time, _sunlit))
            
            #Add another entry in the variable for the end time. This is to ensure that [last switch, end time] is also covered
            _timesAndSunlight.append((Time().from_datetime(_endTime).add_seconds(_granularity), not _sunlits[-1]))
            
            self.__timesAndSunlight = _timesAndSunlight 

        #Now, let's find the sunlight status for the current time
        _sunlit = False
        _currTime = self.__ownernode.timestamp
        for _idx in range(len(self.__timesAndSunlight)):
            if self.__timesAndSunlight[_idx][0] >= _currTime:
                _sunlit = not self.__timesAndSunlight[_idx][1]
                if _idx > 0:
                    self.__timesAndSunlight = self.__timesAndSunlight[_idx:]
                break
        
        return _sunlit

    def __get_RelativeMotion(self, **_kwargs) -> 'Tuple[float, float]':
        '''
        This method calculates the relative motion between the satellite and a ground device such as ground station, IoT device.
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _gs
                The ground device (Assumed that the ground device is stationary)
        @return
            Tuple (distance, relative velocity) in m and m/s respectively
        '''
        pos = self.__ownernode.get_Position()
        if pos is None:
            raise Exception("[In ModelOrbit] Position is not set")
        _time = self.__ownernode.timestamp
        if _time is None:
            raise Exception("[In ModelOrbit] Timestamp is not set")
        if '_gs' not in _kwargs:
            raise Exception("[In ModelOrbit] Ground station position not provided")
        
        _gsPos = _kwargs['_gs'].get_Position()
        
        _satPosTup = np.array(pos.to_tuple()) # (x,y,z) in m in ITRF frame
        _gsPosTup = np.array(_gsPos.to_tuple()) # (x,y,z) in m in ITRF frame
        _metres_to_au = 1.496e11 #meters to astronomical units
        
        _satPos = build_position(position_au = _satPosTup*_metres_to_au, t=_time, center=itrs)
        _gsPos = build_position(position_au = _gsPosTup*_metres_to_au, t=_time, center=itrs)
        
        _, _, dist, _, _, range_rate = _satPos.frame_latlon_and_rates(_gsPos)
        dist = dist.m
        range_rate = range_rate.m_per_s
        
        self.__logger.write_Log("Satellite is moving with distance {} with a speed of {} from {}". \
                                                format(dist, range_rate, _kwargs['_gs'].name), \
                                                    ELogType.LOGINFO, self.__ownernode.timestamp)
        return (dist, range_rate)
    
    def __get_Passes(self, **_kwargs) -> 'list[(Time, Time)]':
        """
        This method tells you the start and end time of the passes for a ground station
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _gs
                The ground device (Assumed that the ground device is stationary)
            @key _start
                The start time of the passes (utils.Time)
            @key _end
                The end time of the passes (utils.Time)
            @key _minElevation
                The minimum elevation angle for the passes (float)
        @return
            List of tuples of start and end time of the passes. If the start or end time is during a pass, the start or end time is returned respectively.
        """
        #take a look at https://rhodesmill.org/skyfield/earth-satellites.html for more details
        
        gs = _kwargs['_gs']
        if gs is None:
            raise Exception("[In ModelOrbit] Ground station is not set")
        
        _start = _kwargs['_start']
        if not isinstance(_start, Time):
            raise Exception("[In ModelOrbit] Start time is not set/valid")
        
        _end = _kwargs['_end']
        if not isinstance(_end, Time):
            raise Exception("[In ModelOrbit] End time is not set/valid")

        if '_minElevation' not in _kwargs:
            raise Exception("[In ModelOrbit] Minimum elevation angle is not set")
        
        #We need to add a buffer of 10 minutes to the start and end time
        #If not, there is a chance that the pass is missed: https://github.com/skyfielders/python-skyfield/issues/856
        _startTs = self.__skyfieldts.utc(_start.copy().add_seconds(-10*60).to_datetime())
        _endTs = self.__skyfieldts.utc(_end.copy().add_seconds(10*60).to_datetime())
        
        lat, lon, alt = gs.lat, gs.lon, gs.alt 
        gsPos = wgs84.latlon(lat, lon, elevation_m=alt)

        #get the passes using the skyfield API
        _t, _events = self.__earthsatellite.find_events(gsPos, _startTs, _endTs, altitude_degrees=_kwargs['_minElevation'])    
        
        #events = 0 for enter, 1 for maximum, 2 for exit
        #we only need the enter and exit events
        _cleanedList = [(ti, event) for ti, event in zip(_t, _events) if event != 1]
                
        #let's convert the list to our own time format
        _cleanedList = [(Time().from_datetime(ti.utc_datetime()), event) for ti, event in _cleanedList]
        #let's only consider ones that are in the time range
        _cleanedList = [(ti, event) for ti, event in _cleanedList if ti >= _start and ti <= _end]
        
        #if the list is empty, return empty lis
        if len(_cleanedList) == 0:
            return []
        
        _out = []
        #if the first event is an exit, add the start time
        if _cleanedList[0][1] == 2:
            _out.append((_start.copy(), _cleanedList[0][0]))
            _cleanedList = _cleanedList[1:]
        
        #Now, let's match all the tuples
        for (time, event) in _cleanedList:
            #If the event is an enter, add the tuple to the list
            if event == 0:
                _out.append((time, None))
            #Now, update the last tuple in the list
            elif event == 2:
                _out[-1] = (_out[-1][0], time)
        
        #If the last event is an enter, add the end time
        if _out[-1][1] is None:
            _out[-1] = (_out[-1][0], _end.copy())
        
        return _out
            
    def __get_Position(self, **kwargs):
        """
        This method calculates the position of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _time
                The time at which the position is to be calculated (utils.Time)
        @return
            utils.Location object containing the position of the satellite
        """
        _time = kwargs['_time']
        if not isinstance(_time, Time):
            raise Exception("[In ModelOrbit] Time is not set/valid")
        
        _utcTime = self.__skyfieldts.utc(_time.to_datetime())

        # calculate the location
        _gcrsLocation = self.__earthsatellite.at(_utcTime)
        _itrs = _gcrsLocation.itrf_xyz().m
        _newLocation = Location(_itrs[0], _itrs[1], _itrs[2])

        # update the object's dictionary
        self.__ownernode.update_Position(_newLocation, _time)

        return _newLocation
    
    def __get_Velocity(self, **kwargs):
        """
        This method calculates the velocity of the satellite at a given time
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _time
                The time at which the velocity is to be calculated (utils.Time)
        @return
            The velocity of the satellite at the given time (x, y, z) in m/s (tuple of floats)
        """
        _time = kwargs['_time']
        if not isinstance(_time, Time):
            raise Exception("[In ModelOrbit] Time is not set/valid")
        
        _utcTime = self.__skyfieldts.utc(_time.to_datetime())
        _gcrsLocation = self.__earthsatellite.at(_utcTime)
        _vel = _gcrsLocation.velocity.m_per_s
        return (_vel[0], _vel[1], _vel[2])
    
    def __setup_Skyfield(self, **kwargs):
        '''
        @desc
            Set's up the skyfield package for the model. 
            This is important because the skyfield package cannot be pickled.
            See https://github.com/brandon-rhodes/python-sgp4/issues/80
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        '''
        # initiate the earth satellite instance
        _tlelines = self.__ownernode.get_TLE()
        
        if len(_tlelines) == 2:
            self.__earthsatellite = EarthSatellite(_tlelines[0], _tlelines[1])
        elif len(_tlelines) == 3:
            self.__earthsatellite = EarthSatellite(_tlelines[1], _tlelines[2])
        else:
            raise Exception(f"Invalid number of TLE lines in {self.iName}")
        
        #initiate the time scale for skyfield operation 
        self.__skyfieldts = load.timescale()
        
    def __remove_Skyfield(self, **kwargs):
        '''
        @desc
            Removes the skyfield package for the model. 
            This is important because the skyfield package cannot be pickled.
            See https://github.com/brandon-rhodes/python-sgp4/issues/80
        @param[in] kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        '''
        self.__earthsatellite = None
        self.__skyfieldts = None
    
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "in_Sunlight": __in_Sunlight,
        "get_RelativeMotion": __get_RelativeMotion,
        "get_Passes": __get_Passes,
        "get_Position": __get_Position,
        "get_Velocity": __get_Velocity,
        "setup_Skyfield": __setup_Skyfield,
        "remove_Skyfield": __remove_Skyfield,
    }
    
    def call_APIs(self, 
                _apiName: str, 
                **_kwargs):
        '''
        This method acts as an API interface of the model. 
        An API offered by the model can be invoked through this method.
        @param[in] _apiName
            Name of the API. Each model should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        _ret = None
        try:
            _ret = self.__apiHandlerDictionary[_apiName](self, **_kwargs)
        except Exception as e:
            print(f"[ModelOrbit]: An unhandled API request has been received by {self.__ownernode.nodeID}:", e)
            
        return _ret
        
    def __init__(
            self, 
            _ownernodeins: INode, 
            _loggerins: ILogger,
            _alwaysCalculate: bool = False) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance 
        @param[in]  _alwaysCalculate
            Wether to automatically update the location of the node at every time step or not. Default is False
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins

        self.__earthsatellite = None
        self.__skyfieldts = None
        self.__setup_Skyfield()
        
        self.__ephem = load("./dependencies/de440s.bsp") #ephemeris file. This is a binary file that contains the positions of the earth and the sun. 
        #NASA JPL Horizons Ephemeris Service: https://ssd.jpl.nasa.gov/ephem.html provides the ephemeris file 
        
        self.__alwaysCalculate = _alwaysCalculate
        
        self.__timesAndSunlight = None #list of tuples of the form (time, inSunlight). See __in_Sunlight for more details 
        
    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self.__modeltag.__str__()])

    def Execute(self):
        """
        @desc
            This method executes the tasks that needed to be performed by the model.
            The model reads the time of the owner node which is a satellite and updates its location
        """
        if self.__skyfieldts is None:
            self.__setup_Skyfield()
        
        if self.__alwaysCalculate: 
            # calculate the time of the node
            _nodeTime = self.__ownernode.timestamp
            #In the method call below, the position will be calculated and stored in the satellitebasic's position dictionary
            _newLocation = self.__get_Position({'_time': _nodeTime})
        #If not alwaysCalculate, then the position of the node will be calculated & updated when the get_Position API is called
        #This API is currently called by the satellitebasic's get_Position method
        
def init_ModelOrbit(
        _ownernodeins: INode, 
        _loggerins: ILogger, 
        _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key always_calculate
            Wether to automatically update the location of the node at every timestep
    @return
        Instance of the model class
    '''
    # check the arguments
    assert _ownernodeins is not None
    assert _loggerins is not None


    _alwaysCalc = False
    if hasattr(_modelArgs, 'always_calculate'):
        _alwaysCalc = _modelArgs['always_calculate']
    else:
        _loggerins.write_Log("always_calculate not provided provided. Defaulting to False", ELogType.LOGWARN, _ownernodeins.timestamp, "ModelOrbit")
        
    return ModelOrbit(_ownernodeins, _loggerins, _alwaysCalc)