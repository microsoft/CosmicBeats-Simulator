class BaselineScheduler:
    def __init__(self):
        print(">>> [ENGINE] Baseline Scheduler Initialized (Greedy — battery + RAM | ISL always available)")

    def decide(self, task_dict, fleet, battery_safety_pct=20.0):
        candidatos = []

        for sat in fleet:
            if sat.get('region') != task_dict.get('region'):
                continue
            if sat.get('battery_pct', 100.0) <= battery_safety_pct:
                continue
            if sat.get('ram_free', 0) < task_dict.get('ram', 0):
                continue
            candidatos.append(sat)

        if not candidatos:
            return None

        # Prioriza maior bateria, desempata por maior RAM livre
        best = max(candidatos, key=lambda s: (s.get('battery_pct', 0), s.get('ram_free', 0)))
        return best.get('id')
