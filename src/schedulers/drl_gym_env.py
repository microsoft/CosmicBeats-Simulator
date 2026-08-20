"""
NTNMECEnv — Gymnasium environment for NTN-MEC satellite routing.

Observation (13 floats, normalized [0,1]):
  [0:3]  task_region_onehot  (USA=0, BRAZIL=1, EUROPE=2)
  [3]    has_anomaly
  [4]    sat1_battery_pct / 100      (SAT-1, BRAZIL)
  [5]    sat1_ram_free / 4096
  [6]    sat1_solar_charging
  [7]    sat2_battery_pct / 100      (SAT-2, EUROPE)
  [8]    sat2_ram_free / 4096
  [9]    sat2_solar_charging
  [10]   sat15_battery_pct / 100     (SAT-15, USA)
  [11]   sat15_ram_free / 4096
  [12]   sat15_solar_charging

Action (Discrete 4):
  0 → route to SAT-1  (BRAZIL)
  1 → route to SAT-2  (EUROPE)
  2 → route to SAT-15 (USA)
  3 → DROP

Reward:
  Successful valid route:    +1.0 + 0.1*(battery/100)
  Drop with no valid cands:  -0.5   (forced drop)
  Invalid action (wrong     -2.0   (region mismatch / battery/RAM fail)
    region or resource fail)
  Voluntary drop w/ cands:  -1.0
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

# Satellite definitions — match simulation config
_SATS = [
    {"id": 1,  "region": "BRAZIL", "capacity_wh": 75.0},
    {"id": 2,  "region": "EUROPE", "capacity_wh": 50.0},
    {"id": 15, "region": "USA",    "capacity_wh": 100.0},
]
_REGION_IDX = {"USA": 0, "BRAZIL": 1, "EUROPE": 2}
_IDX_REGION = {v: k for k, v in _REGION_IDX.items()}
_RAM_TOTAL  = 4096.0
_TASK_RAM   = 500.0
_BAT_SAFETY = 20.0
_ANOMALY_RATE = 0.10

# Hidden anomaly subtypes used only to SHAPE the reward signal during training.
# They are NEVER exposed in the observation (_build_obs only sees has_anomaly) —
# the agent must learn the single best "blind" fallback action for has_anomaly=1,
# the same way it would have to act in the real simulation without reading the
# anomaly's semantic meaning. This preserves the scientific invariant while still
# letting the agent do better than ignoring the flag entirely.
_ANOMALY_TYPES = ["hardware", "gdpr", "sovereignty"]


class NTNMECEnv(gym.Env):
    """Single-step routing decision environment for NTN-MEC satellites."""

    metadata = {"render_modes": []}

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(13,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(4)  # 0=SAT1, 1=SAT2, 2=SAT15, 3=DROP
        self._task  = None
        self._fleet = None

    # ------------------------------------------------------------------ #
    # Core Gym interface                                                   #
    # ------------------------------------------------------------------ #

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._task, self._fleet = self._sample_state()
        return self._build_obs(), {}

    def step(self, action):
        action = int(action)
        decision_id, reward = self._evaluate_action(action)

        # Single-step env — every step is terminal
        obs, _ = self.reset()
        return obs, reward, True, False, {"decision_id": decision_id}

    def render(self):
        pass

    # ------------------------------------------------------------------ #
    # State sampling                                                       #
    # ------------------------------------------------------------------ #

    def _sample_state(self):
        rng = self.np_random

        task_region = _IDX_REGION[rng.integers(0, 3)]
        has_anomaly = float(rng.random() < _ANOMALY_RATE)
        anomaly_type = _ANOMALY_TYPES[rng.integers(0, 3)] if has_anomaly else None

        fleet = []
        for sat in _SATS:
            # Sample battery in range realistic for simulation
            battery = float(rng.uniform(15.0, 100.0))
            ram_free = float(rng.uniform(0.0, _RAM_TOTAL))
            solar    = float(rng.integers(0, 2))
            fleet.append({
                "id":             sat["id"],
                "region":         sat["region"],
                "battery_pct":    battery,
                "ram_free":       ram_free,
                "solar_charging": bool(solar),
            })

        task = {
            "region":          task_region,
            "ram":             _TASK_RAM,
            "semantic_anomaly": "anomaly" if has_anomaly else None,
            "_anomaly_type":   anomaly_type,  # hidden — reward shaping only
        }
        return task, fleet

    # ------------------------------------------------------------------ #
    # Observation builder                                                  #
    # ------------------------------------------------------------------ #

    def _build_obs(self):
        region_oh = [0.0, 0.0, 0.0]
        region_oh[_REGION_IDX[self._task["region"]]] = 1.0
        has_anomaly = float(bool(self._task.get("semantic_anomaly")))

        sat_features = []
        for sat in self._fleet:
            sat_features += [
                sat["battery_pct"] / 100.0,
                sat["ram_free"]    / _RAM_TOTAL,
                float(sat["solar_charging"]),
            ]

        return np.array(region_oh + [has_anomaly] + sat_features, dtype=np.float32)

    # ------------------------------------------------------------------ #
    # Action evaluation                                                    #
    # ------------------------------------------------------------------ #

    def _evaluate_action(self, action):
        """Map action → (decision_id, reward).

        Reward is shaped by the hidden anomaly subtype (never exposed in the
        observation) so the agent learns the best possible "blind" fallback
        action for has_anomaly=1 — it still cannot tell GDPR from a hardware
        failure, but training nudges it toward whichever single behavior
        maximizes expected compliance across the real anomaly mix.
        """
        task_region  = self._task["region"]
        task_ram     = self._task["ram"]
        anomaly_type = self._task.get("_anomaly_type")

        # Hardware failures must always be dropped, regardless of resources.
        if anomaly_type == "hardware":
            if action == 3:
                return None, 1.0
            return None, -2.0

        # GDPR tasks must be routed to EUROPE; sovereignty tasks must be routed
        # to BRAZIL specifically (matches ai_logic._semantic_compliant) — only
        # plain (no-anomaly) tasks use the task's own region as the target.
        if anomaly_type == "gdpr":
            required_region = "EUROPE"
        elif anomaly_type == "sovereignty":
            required_region = "BRAZIL"
        else:
            required_region = task_region
        candidates = [
            s for s in self._fleet
            if s["region"] == required_region
            and s["battery_pct"] > _BAT_SAFETY
            and s["ram_free"]    >= task_ram
        ]

        if action == 3:  # explicit DROP
            # Per ai_logic._semantic_compliant, drop is only ever compliant for
            # hardware failures (handled above) — GDPR/sovereignty/none always
            # require an actual route to be compliant, so drop is never rewarded here.
            if candidates:
                return None, -1.0   # voluntary drop when a valid route existed
            return None, -0.5       # forced drop, no valid candidate available

        # Satellite selection: action 0→SAT[0], 1→SAT[1], 2→SAT[2]
        if action >= len(self._fleet):
            return None, -2.0

        chosen = self._fleet[action]

        # Validate: region, battery, RAM
        if chosen["region"] != required_region:
            return None, -2.0
        if chosen["battery_pct"] <= _BAT_SAFETY:
            return None, -2.0
        if chosen["ram_free"] < task_ram:
            return None, -2.0

        reward = 1.0 + 0.1 * (chosen["battery_pct"] / 100.0)
        return chosen["id"], reward

    # ------------------------------------------------------------------ #
    # Public helper for scheduler use                                      #
    # ------------------------------------------------------------------ #

    def build_obs_from_context(self, task_dict, fleet):
        """Build observation vector from live simulation state."""
        region_oh = [0.0, 0.0, 0.0]
        ridx = _REGION_IDX.get(task_dict.get("region", "USA"), 0)
        region_oh[ridx] = 1.0
        has_anomaly = float(bool(task_dict.get("semantic_anomaly")))

        # fleet must be ordered: SAT-1, SAT-2, SAT-15 (same as _SATS)
        sat_order = {s["id"]: i for i, s in enumerate(_SATS)}
        ordered_fleet = sorted(fleet, key=lambda s: sat_order.get(s["id"], 99))

        sat_features = []
        for sat in ordered_fleet:
            sat_features += [
                sat.get("battery_pct", 0.0) / 100.0,
                sat.get("ram_free",    0.0) / _RAM_TOTAL,
                float(sat.get("solar_charging", True)),
            ]

        # Pad if fewer than 3 satellites
        while len(sat_features) < 9:
            sat_features += [0.0, 0.0, 0.0]

        return np.array(region_oh + [has_anomaly] + sat_features[:9], dtype=np.float32)
