# src/sim/simulator.py (Versão Limpa)
from src.sim.orchestrator import Orchestrator
from src.sim.imanager import IManager
from src.sim.managerparallel import ManagerParallel
import time

class Simulator():
    def __init__(self, _configfilepath: str, _numWorkers: int = 1) -> None:
        self.__configFilePath = _configfilepath
        self.__orchestrator = Orchestrator(self.__configFilePath)
        self.__orchestrator.create_SimEnv()
        __simEnv = self.__orchestrator.get_SimEnv()
        self.__manager = ManagerParallel(topologies = __simEnv[0], numOfSimSteps = __simEnv[1], numOfWorkers = _numWorkers)

    def execute(self):
        self.__manager.run_Sim()