# src/core/task.py
'''
@desc
    This module defines the Task class.
    
    A Task represents a unit of computational work that needs to be
    scheduled and processed by a SatelliteMEC node.
    
    UPDATED: Now includes data size (for RAM usage) and deadlines (for QoS).
'''

class Task:
    '''
    @desc
        A data class to represent a computational task with MEC requirements.
    '''
    def __init__(
            self, 
            _task_id: int, 
            _mips_required: float, 
            _creation_time: float,
            _data_input_size_mb: float,
            _data_output_size_mb: float,
            _deadline: float = None
        ):
        '''
        @param[in] _task_id
            A unique identifier for the task.
        @param[in] _mips_required
            The total computational load (Million Instructions).
            Determines CPU time.
        @param[in] _creation_time
            The simulation time (env.now) when the task was created.
        @param[in] _data_input_size_mb
            The size of the data to be uploaded/processed (in MB).
            Determines RAM usage and I/O time.
        @param[in] _data_output_size_mb
            The size of the result data (in MB).
            Determines downlink/offload transmission time.
        @param[in] _deadline (Optional)
            The simulation time by which the task MUST be finished.
            Used for failure metrics (Task Drop Rate).
        '''
        self.id = _task_id
        self.mips_required = _mips_required
        self.creation_time = _creation_time
        
        # New MEC Attributes
        self.data_input_size = _data_input_size_mb
        self.data_output_size = _data_output_size_mb
        self.deadline = _deadline

    def is_missed_deadline(self, current_time: float) -> bool:
        '''
        @desc
            Checks if the task has already missed its deadline.
        @return
            True if deadline exists and passed, False otherwise.
        '''
        if self.deadline is None:
            return False
        return current_time > self.deadline

    def __str__(self):
        '''
        @desc
            String representation for logging.
        '''
        return (f"Task(id={self.id}, mips={self.mips_required}, "
                f"data={self.data_input_size}MB, deadline={self.deadline})")