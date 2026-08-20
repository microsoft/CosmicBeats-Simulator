import collections
import os
import json
import re
import time
import requests
import urllib3
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY        = os.environ.get("GEMINI_API_KEY")
SLM_MODEL      = os.environ.get("SLM_MODEL", "gemma-4-26b-a4b-it")
NPU_LATENCY_MS = float(os.environ.get("SLM_NPU_LATENCY_MS", "50.0"))
RPM_LIMIT      = int(os.environ.get("SLM_RPM_LIMIT", "14"))  # conservative under the 15 RPM cap


def _parse_gemma_json(text):
    """
    Parse JSON from Gemma output which may include chain-of-thought tokens
    between fields. Strategy: try full JSON parse first, then extract
    key-value pairs and reconstruct, handling null values.
    """
    # 1. Try standard JSON parse on the full text or first {...} block
    for pattern in (r'\{[^{}]*\}', r'\{.*\}'):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # 2. Extract individual key-value pairs scattered across chain-of-thought text
    action       = re.search(r'"action"\s*:\s*"([^"]+)"', text)
    target       = re.search(r'"target_region"\s*:\s*(?:"([^"]*)"|null)', text)
    reason       = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
    if action:
        return {
            "action":        action.group(1),
            "target_region": target.group(1) if target and target.group(1) else None,
            "reason":        reason.group(1) if reason else "",
        }
    return None

_PROMPT_TEMPLATE = """\
CONTEXT: You are an AI scheduler embedded in a Low-Earth-Orbit satellite (edge node). \
You have strict resource constraints and must make fast routing decisions. \
Inter-satellite links (ISL) are always available. \
Output ONLY valid JSON — no markdown, no explanation.

TASK:
  region: {region}
  ram_required: {ram} MB
  anomaly: "{anomaly}"

AVAILABLE SATELLITES:
{fleet_lines}

ROUTING RULES (apply in order):
  1. GDPR/EU privacy anomaly: route exclusively to EUROPE. Drop if unavailable.
  2. Sovereignty/national data anomaly: route to task country region. Drop if unavailable.
  3. Critical hardware failure anomaly: drop the task entirely.
  4. No anomaly: route to satellite in task region with battery_pct > 20% and sufficient RAM.
  5. action=process when routing to task region, action=route when forwarding elsewhere, action=drop only when no valid satellite or hardware failure.

Output ONLY valid JSON:
{{"action": "process|route|drop", "target_region": "USA|BRAZIL|EUROPE|null", "reason": "one short sentence"}}
"""


class SLMScheduler:
    def __init__(self):
        if not API_KEY:
            print(">>> [SLM] WARNING: GEMINI_API_KEY not found. API calls will return None (drop).")
        else:
            print(f">>> [ENGINE] SLM Scheduler Initialized ({SLM_MODEL} via Gemini API | NPU latency={NPU_LATENCY_MS}ms)")
        self.npu_busy_until = 0.0
        self.pending_tasks = []
        self._call_timestamps: collections.deque = collections.deque()

    # ------------------------------------------------------------------ #
    # Async state machine                                                  #
    # ------------------------------------------------------------------ #

    def receive_task(self, task_dict, current_time, fleet):
        ready_time = max(current_time, self.npu_busy_until) + (NPU_LATENCY_MS / 1000.0)
        self.npu_busy_until = ready_time
        task_dict["slm_ready_time"] = ready_time
        task_dict["slm_fleet_snapshot"] = list(fleet)
        self.pending_tasks.append(task_dict)
        return ready_time

    def check_completed_inferences(self, current_time):
        completed, remaining = [], []
        for task in self.pending_tasks:
            if current_time >= task.get("slm_ready_time", 0):
                completed.append((task, self._decide_route(task)))
            else:
                remaining.append(task)
        self.pending_tasks = remaining
        return completed

    # ------------------------------------------------------------------ #
    # Decision logic                                                       #
    # ------------------------------------------------------------------ #

    def _decide_route(self, task_dict):
        fleet = task_dict.get("slm_fleet_snapshot", [])
        t0 = time.perf_counter()
        api_result = self._call_gemini(task_dict, fleet)
        result = self._resolve_action(api_result, fleet, task_dict) if api_result is not None else None
        task_dict["slm_wall_latency_ms"] = (time.perf_counter() - t0) * 1000
        return result

    def _build_prompt(self, task_dict, fleet):
        fleet_lines = "\n".join(
            f"  SAT {s['id']} | region={s['region']}"
            f" | battery_pct={s['battery_pct']:.0f}%"
            f" | solar_charging={s['solar_charging']}"
            f" | ram_free={s['ram_free']:.0f} MB"
            for s in fleet
        )
        return _PROMPT_TEMPLATE.format(
            region=task_dict.get("region", "?"),
            ram=task_dict.get("ram", 0),
            anomaly=task_dict.get("semantic_anomaly", "none"),
            fleet_lines=fleet_lines,
        )

    def _rate_limit_wait(self):
        """Block until making another API call stays within RPM_LIMIT calls/minute."""
        now = time.monotonic()
        while self._call_timestamps and now - self._call_timestamps[0] > 60.0:
            self._call_timestamps.popleft()
        if len(self._call_timestamps) >= RPM_LIMIT:
            wait = 61.0 - (now - self._call_timestamps[0])
            if wait > 0:
                print(f"   [SLM Rate Limiter] {len(self._call_timestamps)} calls/min — waiting {wait:.1f}s")
                time.sleep(wait)
            now = time.monotonic()
            while self._call_timestamps and now - self._call_timestamps[0] > 60.0:
                self._call_timestamps.popleft()
        self._call_timestamps.append(time.monotonic())

    def _call_gemini(self, task_dict, fleet):
        if not API_KEY:
            return None
        self._rate_limit_wait()
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{SLM_MODEL}:generateContent?key={API_KEY}")
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": self._build_prompt(task_dict, fleet)}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 1024,
            },
        }
        for attempt in range(4):
            try:
                t0 = time.perf_counter()
                r = requests.post(url, headers=headers, json=data, verify=False, timeout=30)
                latencia_ms = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    parts = r.json()["candidates"][0]["content"].get("parts", [])
                    # Gemma returns thinking and the final answer as separate parts
                    # (each tagged "thought": true/false) — use the non-thought
                    # parts; some thinking-heavy responses omit the flag on the
                    # final part, so fall back to concatenating everything.
                    answer_parts = [p.get("text", "") for p in parts if not p.get("thought", False)]
                    raw = "".join(answer_parts) if answer_parts else "".join(p.get("text", "") for p in parts)
                    combined = "{" + raw if not raw.lstrip().startswith("{") else raw
                    result = _parse_gemma_json(combined)
                    if result is None:
                        print(f"   [SLM Parse Error] Tentativa {attempt+1}/4 — No JSON found in: {raw[:80]}")
                        continue
                    print(f"   [SLM {SLM_MODEL} {latencia_ms:.0f}ms] action={result.get('action')}"
                          f" target={result.get('target_region')} reason={result.get('reason', '')}")
                    return result
                elif r.status_code == 429:
                    wait = 30 * (attempt + 1)
                    print(f"   [SLM Rate Limit] Tentativa {attempt+1}/4 — aguardando {wait}s")
                    time.sleep(wait)
                    continue
                elif r.status_code == 500:
                    wait = 10 * (attempt + 1)
                    print(f"   [SLM Server Error 500] Tentativa {attempt+1}/4 — aguardando {wait}s")
                    time.sleep(wait)
                    continue
                else:
                    print(f"   [SLM Error] HTTP {r.status_code} — {r.text[:120]}")
                    break
            except Exception as e:
                print(f"   [SLM Connection Error] {e}")
                continue
        return None

    def _resolve_action(self, api_result, fleet, task_dict):
        action = api_result.get("action", "drop")
        target_region = api_result.get("target_region")
        if action == "drop":
            return None
        if action == "process":
            target_region = task_dict.get("region")
        if target_region:
            for s in fleet:
                if (s.get("region") == target_region
                        and s.get("battery_pct", 100.0) > 20.0
                        and s.get("ram_free", 0) >= task_dict.get("ram", 0)):
                    return s.get("id")
        return None
