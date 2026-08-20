# src/nodes/satellite_mec.py

import simpy
from src.nodes.satellitebasic import SatelliteBasic
from src.simlogging.ilogger import ELogType

# =============================================================================
# [ITEM 1] MEC ATTRIBUTES: Updated SatelliteMEC Class (VERSÃO FINAL KWARGS)
# =============================================================================
class SatelliteMEC(SatelliteBasic):
    '''
    A Satellite node with CPU, RAM, I/O limits, and Battery consumption.
    '''
    # Mudança: Aceitamos **kwargs para passar os argumentos da classe pai pelo NOME
    def __init__(self, _env: simpy.Environment, _mec_details, _logger, **kwargs) -> None:
        
        # Chamada explícita usando kwargs. Isso garante que cada valor vá para a variável certa.
        super().__init__(
            _nodeID=kwargs['_nodeID'],
            _topologyID=kwargs['_topologyID'],
            _tleline1=kwargs['_tleline1'],
            _tleline2=kwargs['_tleline2'],
            _timeDelta=kwargs['_timeDelta'],
            _timeStamp=kwargs['_timeStamp'],
            _endtime=kwargs['_endtime'],
            _Logger=_logger, # Passamos o logger explicitamente
            _additionalArgs=kwargs.get('_additionalArgs', "")
        )
        
        self.env = _env
        self.logger = _logger

        # --- COMPUTATION (Processing) ---
        self.cpu_capacity_mips = float(_mec_details.cpu_capacity_mips)
        self.cpu_resource = simpy.Resource(self.env, capacity=1)

        # --- MEMORY (RAM/Storage) ---
        self.ram_capacity_mb = float(getattr(_mec_details, 'ram_capacity_mb', 4096.0))
        self.ram_container = simpy.Container(self.env, capacity=self.ram_capacity_mb, init=self.ram_capacity_mb)

        # --- I/O (Throughput) ---
        self.io_throughput_mbs = float(getattr(_mec_details, 'io_throughput_mbs', 500.0))

        # --- POWER (Energy) ---
        self.battery_capacity = float(getattr(_mec_details, 'battery_capacity_joules', 10000.0))
        self.current_battery = self.battery_capacity
        self.power_idle = 5.0
        self.power_active = 20.0
        self.total_energy_consumed = 0.0
        self.battery_depleted = False

        self.tasks_completed_count = 0
        self.tasks_dropped_count = 0

        self.env.process(self.battery_drain_process())

    # --- (Os métodos abaixo continuam iguais) ---
    def get_current_load_percentage(self) -> float:
        if self.cpu_resource.capacity == 0: return 0.0
        return (self.cpu_resource.count / self.cpu_resource.capacity) * 100.0

    def get_ram_usage_percentage(self) -> float:
        used = self.ram_capacity_mb - self.ram_container.level
        return (used / self.ram_capacity_mb) * 100.0
    
    def get_queue_length(self) -> int:
        return len(self.cpu_resource.queue)

    def process_task(self, task: Task):
        current_time_obj = get_current_sim_time(self.env.now)

        if self.battery_depleted:
            self.logger.write_Log(f"Task {task.id} DROPPED. Sat {self.nodeID} dead.", "LOGWARN", current_time_obj)
            self.tasks_dropped_count += 1
            return

        if self.ram_container.level < task.data_input_size:
            self.logger.write_Log(f"Task {task.id} DROPPED. Sat {self.nodeID} OOM (Req: {task.data_input_size}MB, Free: {self.ram_container.level}MB).", "LOGWARN", current_time_obj)
            self.tasks_dropped_count += 1
            return

        yield self.ram_container.get(task.data_input_size)
        
        try:
            current_time_obj = get_current_sim_time(self.env.now)
            self.logger.write_Log(f"Task {task.id} accepted. Loading data...", "LOGINFO", current_time_obj)

            io_time = task.data_input_size / self.io_throughput_mbs
            yield self.env.timeout(io_time)

            with self.cpu_resource.request() as req:
                yield req
                current_time_obj = get_current_sim_time(self.env.now)

                if task.is_missed_deadline(self.env.now):
                     self.logger.write_Log(f"Task {task.id} missed deadline in queue! Processing anyway.", "LOGWARN", current_time_obj)

                self.logger.write_Log(f"Task {task.id} processing...", "LOGINFO", current_time_obj)
                processing_time = task.mips_required / self.cpu_capacity_mips
                yield self.env.timeout(processing_time)
                
                self.tasks_completed_count += 1
                total_time = self.env.now - task.creation_time
                current_time_obj = get_current_sim_time(self.env.now)
                self.logger.write_Log(f"Task {task.id} ({task.type}) FINISHED. Total Time: {total_time:.2f}s", "LOGINFO", current_time_obj)

        finally:
            yield self.ram_container.put(task.data_input_size)

    def battery_drain_process(self):
        while True:
            yield self.env.timeout(1.0)
            is_active = (self.cpu_resource.count > 0)
            consumption = self.power_active if is_active else self.power_idle
            
            self.current_battery -= consumption
            self.total_energy_consumed += consumption
            
            if self.current_battery <= 0:
                self.battery_depleted = True
                self.current_battery = 0
                self.logger.write_Log(f"CRITICAL: Satellite {self.nodeID} BATTERY DEPLETED.", "LOGERROR", get_current_sim_time(self.env.now))
                break