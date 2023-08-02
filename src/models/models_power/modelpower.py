"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Om Chabra
Created on March 10
@desc
    This is a energy model which the satellite generates power and has APIs to use energy. 
    All units are Jules and Watts
"""
from src.nodes.inode import INode
from src.simlogging.ilogger import ELogType, ILogger
from src.models.imodel import IModel, EModelTag

class ModelPower(IModel):
    __modeltag = EModelTag.POWER
    __ownernode: INode
    __supportednodeclasses = []
    __dependencies = [['ModelFixedOrbit', 'ModelOrbit', 'ModelOrbitOneFullUpdate']]
    __logger: ILogger
    
    
    @property
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the model class. For example, ModelPower 
            Note that the name should exactly match to your class name. 
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
        return self.__supportednodeclasses
    
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
    
    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self.__modeltag.__str__()])
    
    def __consume_Energy(
                        self,
                        **_kwargs) -> bool:
        """
        @desc
            This method consumes energy from the battery.
        @param[in]  _kwargs
            keyworded arguments that contain the following arguments:
                Option 1: if the energy in Joules is directly available, just provide the following argument 
                _kwargs["_energy"]: 'float'
                    Energy to be consumed in joules. Other following keyworded arguments are not required to

                Option 2: if the power and consumption numbers are available, just provide the following two arguments   
                _kwargs["_power"]: 'float'
                    Power in Watts
                _kwargs["_duration"]: 'float' 
                    representing the duration for which the power is consumed (in seconds)
                
                Option 3: if the power consumption number for your model tag is provided in the config file just provide the following two arguments
                _kwargs["_duration"]: 'float' 
                    representing the duration for which the power is consumed (in seconds) 
                _kwargs["_tag"]: 'str' 
                    representing the tag of the power consumption in the config file
        @return
            True: If the power was successfully consumed. 
            False: Otherwise
        """
        _ret = False
        
        _energyToConsume = 0
        _loggerTag = "Other"
        
        # if the energy to be consumed is directly provided, then just take that value
        if "_energy" in _kwargs:
            _energyToConsume = _kwargs["_energy"]
        
        # if the power and duration numbers are given, calculate the energy consumption
        elif "_power" in _kwargs and "_duration" in _kwargs:
            _energyToConsume = _kwargs["_duration"] * _kwargs["_power"]
        
        # if the modeltag and duration are provided, look for the power consumption against the tag
        elif "_tag" in _kwargs and "_duration" in _kwargs and _kwargs["_tag"] in self.__powerConsumptionDict:
            _tag = _kwargs["_tag"]
            _loggerTag = _tag
            _energyToConsume = self.__powerConsumptionDict[_tag] * _kwargs["_duration"]
        
        else:
            self.__logger.write_Log("Power consumption tag {} is not provided. Assuming this uses 0 power".format(_kwargs["_tag"])
                                    , ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
            
            #Let's add it to the dictionary so that we don't keep logging this error again and again
            self.__add_KeyToLogs(_kwargs["_tag"]) 
            self.__powerConsumptionDict[_kwargs["_tag"]] = 0
            
            _energyToConsume = 0
        if self.__currentCharge >= _energyToConsume + self.__minCharge:
            self.__currentCharge -= _energyToConsume
            _ret = True
            
        else:
            _energyToConsume = 0    
            self.__logger.write_Log("Not enough power to consume. Current charge: {} J, Required charge: {} J"\
                                .format(self.__currentCharge, _energyToConsume), ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
            _ret = False
        
        #Let's store this for our stats logging
        self.__tagsConsumedLoggerDict[_loggerTag] += _energyToConsume
        
        return _ret
    
    def __get_AvailableEnergy(
                            self,
                            **_kwargs) -> float:
        """
        @desc
            This method returns the available energy in the battery in Joules
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            The available energy in the battery in Joules
        """
        return self.__currentCharge
    
    def _get_MinCharge(self, **_kwargs) -> float:
        """
        @desc
            This method returns the minimum charge in the battery in Joules
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            The minimum charge in the battery in Joules
        """
        return self.__minCharge

    def _get_MaxCharge(self, **_kwargs) -> float:
        """
        @desc
            This method returns the maximum charge in the battery in Joules
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            None for this API
        @return
            The maximum charge in the battery in Joules
        """
        return self.__maxCharge
    
    def __has_Energy(self, **_kwargs):
        """
        @desc
            This method returns True if there is enough energy to run the requested operation
        @param[in] _kwargs
            Keyworded arguments that are passed to the corresponding API handler
            @key _tag: 'str'
                Tag of the power consumption in the config file
        @return
            True: If there is enough energy to run the requested operation
            False: Otherwise
        """
        _granted = False
        _tag = _kwargs["_tag"]
        
        if _tag not in self.__requiredEnergy:
            self.__logger.write_Log(f"Power consumption tag {_tag} not found in the requiredEnergy dictionary. Assuming this can always run if there is any power", \
                ELogType.LOGWARN, self.__ownernode.timestamp, self.iName)
            #To not have to keep putting this warning, let's add this tag to the requiredEnergy dictionary
            self.__add_KeyToLogs(_tag)
            self.__requiredEnergy[_tag] = 0
            
            _granted = self.__currentCharge > self.__minCharge      
              
        else:
            _requiredEnergy = self.__requiredEnergy[_tag]
            if self.__currentCharge >= _requiredEnergy:
                _granted = True
            else:
                _granted = False
        
        #Let's store this for our stats logging
        self.__tagsRequestedLoggerDict[_tag] = True
        self.__tagsGrantedLoggerDict[_tag] = _granted
        
        return _granted
        
    # API dictionary where API name is the key and handler function is the value
    __apiHandlerDictionary = {
        "consume_Energy": __consume_Energy,
        "get_AvailableEnergy": __get_AvailableEnergy,
        "get_MinCharge": _get_MinCharge,
        "get_MaxCharge": _get_MaxCharge,
        "has_Energy": __has_Energy,
    }
    
    def call_APIs(
            self, 
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
            print(f"[ModelPower]: An unhandled API request has been received by {self.__ownernode.nodeID}: ", e)
        
        return _ret
    
    def __add_KeyToLogs(self, _key):
        """
        @desc
            This method adds a key to the logger dictionaries
        @param[in] _key
            Key to be added
        """
        if _key not in self.__loggingTags:
            self.__loggingTags.append(_key)
            self.__tagsRequestedLoggerDict[_key] = self.__tagsRequestedLoggerDict.get(_key, False)
            self.__tagsGrantedLoggerDict[_key] = self.__tagsGrantedLoggerDict.get(_key, False)
            self.__tagsConsumedLoggerDict[_key] = self.__tagsConsumedLoggerDict.get(_key, 0)
        
    def __log_Stats(self):
        """
        @desc
            This method logs the stats of the model.
        """
        _logMessage = "PowerStats. " + \
            "CurrentCharge: [{}] J. ".format(self.__currentCharge) + \
            "ChargeGenerated: [{}] J. ".format(self.__chargeGeneratedLogger) + \
            "OutOfPower: [{}]. ".format(self.__outOfPowerLogger) + \
            "".join(["Tag: [{}]. Requested: [{}]. Granted: [{}]. Consumed: [{}]. ".format(_tag, self.__tagsRequestedLoggerDict[_tag], \
                self.__tagsGrantedLoggerDict[_tag] , self.__tagsConsumedLoggerDict[_tag]) for _tag in self.__loggingTags])
        
        self.__logger.write_Log(_logMessage, ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
        
        #Let's reset the stats
        self.__tagsRequestedLoggerDict = {_tag: False for _tag in self.__loggingTags}
        self.__tagsGrantedLoggerDict = {_tag: None for _tag in self.__loggingTags}
        self.__tagsConsumedLoggerDict = {_tag: 0 for _tag in self.__loggingTags}
        self.__chargeGeneratedLogger = 0 
        self.__previousChargeLogger = 0
        self.__outOfPowerLogger = False 
                
    def Execute(self):
        """
        @desc
            At each time step, this model will determine if the satellite is in sunlight or not. If it is, it will charge the battery.
        """
                
        if self.__orbitHelper is None:
            self.__orbitHelper = self.__ownernode.has_ModelWithTag(EModelTag.ORBITAL)
            if self.__orbitHelper is None:
                raise Exception("Orbit model is not found in the node {}".format(self.__ownernode.name))
        
        #Let's log what the charge was before we added any power
        self.__previousChargeLogger = self.__currentCharge 
        
        _inSunlight = self.__orbitHelper.call_APIs("in_Sunlight")
        if _inSunlight:
            self.__currentCharge += self.__powerGeneration * self.__timestep * self.__batteryEfficiency
        self.__currentCharge = min(self.__currentCharge, self.__maxCharge)
        
        #Let's log how much power was generated
        self.__chargeGeneratedLogger = self.__currentCharge - self.__previousChargeLogger #We need this for logging
        
        for _tag in self.__alwaysOn:
            ret = self.call_APIs("consume_Energy", _tag=_tag, _duration=self.__timestep)
            if not ret:
                self.__logger.write_Log("Not enough power to perform always on task: {}".format(_tag), ELogType.LOGINFO, self.__ownernode.timestamp)
                self.__outOfPowerLogger = True

        self.__log_Stats()
        
    def __init__(self, 
                _ownernode: INode, 
                _loggerins: ILogger,
                _powerConsumptionDict: dict,
                _powerConfigurations: dict,
                _powerGenerations: dict,
                _energyEfficiency: float,
                _alwaysOn: list,
                _requiredEnergy: dict):
        """
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _powerConsumptionDict
            Dictionary containing the power consumption of the model in W.
            For example:
            {
                "TXRADIO": .532,
                "HEATER": .532,
                "RXRADIO": .133,
                "CONCENTRATOR": .266,
                "GPS": .190
            }
        @param[in] _powerConfigurations
            Dictionary containing the power configurations of the model in Joules.
            For instance:
            {
                "MAX_CAPACITY": 25308,
                "MIN_CAPACITY": 15185,
                "INITIAL_CAPACITY": 25308 
            }
        @param[in] _powerGenerations
            Dictionary containing the power generation of the model in W. 
            For instance:
            {
                "SOLAR": 1.666667,
            }
        @param[in] _energyEfficiency
            The efficiency of the battery/panel as a float between 0 and 1
        @param[in] _alwaysOn:
            A list of the tasks that are always on
        @param[in] _timestep
            Timestep of the simulation in seconds (float)
        @param[in] _requiredEnergy
            Dictionary containing the required minimum energy for each task in Joules.
            For instance:
            {
                "Heater": 10,
                "GPS": 10,
                "TXRADIO": 20,
            }
            Means that the heater will only run when there is at least 10 J of energy available, the GPS when 10 J, and the TXRADIO when 20 J.
            If the required energy is not provided, the task will always run if more than the minimum energy is available.
            Used for the has_Energy API. 
        """
        self.__ownernode = _ownernode
        self.__logger = _loggerins
        self.__powerConsumptionDict = _powerConsumptionDict
        self.__powerGenerations = _powerGenerations
        self.__alwaysOn = _alwaysOn
        self.__batteryEfficiency = _energyEfficiency
        self.__timestep = self.__ownernode.deltaTime
        
        if "INITIAL_CAPACITY" not in _powerConfigurations or "MAX_CAPACITY" not in _powerConfigurations or "MIN_CAPACITY" not in _powerConfigurations:
            raise ValueError("[In ModelPower] Power configurations are not provided. Please provide the following configurations: MAX_CAPACITY, MIN_CAPACITY, INITIAL_CAPACITY (in W)") 
        
        self.__currentCharge = _powerConfigurations["INITIAL_CAPACITY"]
        self.__maxCharge = _powerConfigurations["MAX_CAPACITY"]
        self.__minCharge = _powerConfigurations["MIN_CAPACITY"]
        
        if "SOLAR" not in self.__powerGenerations:
            raise ValueError("[In ModelPower] This model currently only supports solar power generation. Please provide the SOLAR power generation per second in W.")
        
        self.__powerGeneration = self.__powerGenerations["SOLAR"]
        
        self.__requiredEnergy = _requiredEnergy

        self.__orbitHelper = None
        
        #Let's setup some stuff for logging
        self.__loggingTags = list(self.__powerConsumptionDict.keys())
        self.__loggingTags.extend(list(self.__requiredEnergy.keys()))
        self.__loggingTags.append("Other")
        
        self.__tagsRequestedLoggerDict = {_tag: False for _tag in self.__loggingTags} #Tag's asked if they should be on or off
        self.__tagsGrantedLoggerDict = {_tag: None for _tag in self.__loggingTags} #The response to the tags asked
        self.__tagsConsumedLoggerDict = {_tag: 0 for _tag in self.__loggingTags}
        self.__chargeGeneratedLogger = 0 #How much power was generated
        self.__previousChargeLogger = 0 #How much charge was in the battery before the timestep
        self.__outOfPowerLogger = False #If the satellite is out of power
        
    
def init_ModelPower(
                _ownernode: INode,
                _loggerins: ILogger,
                _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelImagingLogicBased class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key power_consumption
            Dict of tag to power consumption in W
        @key power_configurations
            Dict of power configurations in Joules
        @key power_generations
            Dict of power generations in W
        @key efficiency
            Efficiency of the battery/panel as a float between 0 and 1
        @key always_on
            A list of the tasks that are always on
        @key required_energy
            Dict of tag to required energy in Joules. Default is that everything is greedy and requires > 0 energy to perform
    @return
        Instance of the model class
    '''
    
    #let's check if the 3 namespaces are provided
    if not hasattr(_modelArgs, "power_consumption") or not hasattr(_modelArgs, "power_configurations") or not hasattr(_modelArgs, "power_generations"):
        raise ValueError("[In ModelPower] Please provide the following namespaces: power_consumption, power_configurations, power_generations")
    
    _powerConsumption = _modelArgs.power_consumption
    _powerConfigurations = _modelArgs.power_configurations
    _powerGenerations = _modelArgs.power_generations
    _alwaysOn = _modelArgs.always_on if hasattr(_modelArgs, "always_on") else []
    
    #convert all three of the Namespaces to dictionaries
    _powerConsumption = vars(_powerConsumption)
    _powerConfigurations = vars(_powerConfigurations)
    _powerGenerations = vars(_powerGenerations)
    
    _efficiency = _modelArgs.efficiency if hasattr(_modelArgs, "efficiency") else 1.0
    
    if hasattr(_modelArgs, "required_energy"):
        _requiredEnergy = vars(_modelArgs.required_energy)
    else:
        _requiredEnergy = {}
        
    return ModelPower(_ownernode, _loggerins, _powerConsumption, _powerConfigurations, _powerGenerations, _efficiency, _alwaysOn, _requiredEnergy)

    
    # def calculate_voltage_and_current(battery_voltage: float, resistance: float):
    #     """
    #     @desc
    #         Uses Ohm's law to calculate the voltage drop and current
    #         Assumes the units are handled by the user)
    #     @return:
    #         (voltage_drop, current) (float, float)
    #     """
    #     
    #     voltage_drop = battery_voltage - (resistance * current)
    #     current = voltage_drop / resistance
    #     return voltage_drop, current
    
    # def simulate_charging_and_discharging(battery_capacity, battery_capacity_low, battery_voltage, resistance, efficiency):
    #     """
    #     @desc
    #         This function simulates charging and discharging a battery. 
    #         This is currently not used in the simulation, but I'm leaving it here in case we need it later.
    #     @param battery_capacity: float
    #         The capacity of the battery in Joules
    #     @param battery_capacity_low: float
    #         The capacity of the battery in Joules when it is considered discharged
    #     @param battery_voltage: float
    #         The voltage of the battery in Volts
    #     @param resistance: float
    #         The resistance of the battery in Ohms
    #     @param efficiency: float
    #         The efficiency of the battery in Joules
    #     @return:
    #         (charge, time, current) (float, float, float) (Joules, seconds, Amps)
    #     """
    #        
    #     # Initialize variables
    #     charge = 0
    #     time = 0
    #     current = 0
        
    #     while charge < battery_capacity:
    #         # Calculate voltage drop and current
    #         voltage_drop, current = calculate_voltage_and_current(battery_voltage, resistance)
            
    #         # Calculate charge transferred
    #         charge_transferred = current * efficiency * (time / 3600)
            
    #         # Update charge and time
    #         charge += charge_transferred
    #         time += 1
            
    #         # If battery is fully charged, stop charging
    #         if charge >= battery_capacity:
    #             break
            
    #         # If battery is discharged below the TTL voltage level capacity, stop discharging
    #         if charge <= battery_capacity_low:
    #             break
        
    #     return charge, time, current