"""
DRL Scheduler — Stable Baselines3 DQN agent for NTN-MEC routing.

Loads a pre-trained DQN model (models/best_model.zip).
Train with: python scripts/train_drl.py

Action mapping (same as NTNMECEnv):
  0 → SAT-1  (BRAZIL)
  1 → SAT-2  (EUROPE)
  2 → SAT-15 (USA)
  3 → DROP

Scientific invariant preserved: agent receives has_anomaly=1 but NOT the anomaly
type — it cannot learn GDPR/sovereignty semantics. This justifies lower
semantic_compliance vs SLM/LLM in comparative results.
"""

import os
import random
import numpy as np

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "best_model.zip")

# Satellite order MUST match NTNMECEnv._SATS
_SAT_ORDER = [
    {"id": 1,  "region": "BRAZIL"},
    {"id": 2,  "region": "EUROPE"},
    {"id": 15, "region": "USA"},
]
_REGION_IDX = {"USA": 0, "BRAZIL": 1, "EUROPE": 2}
_RAM_TOTAL   = 4096.0
_BAT_SAFETY  = 20.0


class DRLScheduler:
    def __init__(self):
        from stable_baselines3 import DQN
        path = os.path.abspath(_MODEL_PATH)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"DRL model not found at {path}. "
                "Run: python scripts/train_drl.py"
            )
        self.model = DQN.load(path)
        random.seed(0)  # DQN.load() reseeds the global RNG via SB3's set_random_seed,
        # shifting the Poisson arrival sequence — restore the canonical seed here.
        print(f">>> [ENGINE] DRL Scheduler Initialized (SB3-DQN | {path})")
        self._step = 0

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def decide(self, task_dict, fleet, battery_safety_pct=_BAT_SAFETY):
        obs = self._build_obs(task_dict, fleet)
        action, _ = self.model.predict(obs, deterministic=True)
        action = int(action)

        decision_id = self._resolve_action(action, task_dict, fleet, battery_safety_pct)

        self._step += 1
        action_names = ["PREFER_SAT1(BR)", "PREFER_SAT2(EU)", "PREFER_SAT15(US)", "DROP"]
        sat_str = f"SAT {decision_id}" if decision_id is not None else "None"
        print(f"   [DRL-DQN step={self._step}] action={action_names[action]} → {sat_str}")

        return decision_id

    # ------------------------------------------------------------------ #
    # Observation builder                                                  #
    # ------------------------------------------------------------------ #

    def _build_obs(self, task_dict, fleet):
        region_oh = [0.0, 0.0, 0.0]
        ridx = _REGION_IDX.get(task_dict.get("region", "USA"), 0)
        region_oh[ridx] = 1.0
        has_anomaly = float(bool(task_dict.get("semantic_anomaly")))

        fleet_by_id = {s["id"]: s for s in fleet}
        sat_features = []
        for sat_def in _SAT_ORDER:
            sat = fleet_by_id.get(sat_def["id"], {})
            sat_features += [
                sat.get("battery_pct", 0.0) / 100.0,
                sat.get("ram_free",    0.0) / _RAM_TOTAL,
                float(sat.get("solar_charging", True)),
            ]

        return np.array(region_oh + [has_anomaly] + sat_features, dtype=np.float32)

    # ------------------------------------------------------------------ #
    # Action → satellite mapping                                          #
    # ------------------------------------------------------------------ #

    def _resolve_action(self, action, task_dict, fleet, battery_safety_pct):
        task_region = task_dict.get("region")
        task_ram    = task_dict.get("ram", 0)

        if action == 3:
            return None  # explicit DROP

        if action >= len(_SAT_ORDER):
            return None

        target_def = _SAT_ORDER[action]
        fleet_by_id = {s["id"]: s for s in fleet}
        sat = fleet_by_id.get(target_def["id"])

        if sat is None:
            return None
        if sat.get("region") != task_region:
            return None
        if sat.get("battery_pct", 0.0) <= battery_safety_pct:
            return None
        if sat.get("ram_free", 0.0) < task_ram:
            return None

        return sat["id"]
