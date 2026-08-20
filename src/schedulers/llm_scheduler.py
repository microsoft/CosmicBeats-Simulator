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

API_KEY   = os.environ.get("GEMINI_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3.1-flash-lite")
RPM_LIMIT = int(os.environ.get("LLM_RPM_LIMIT", "10"))

_PROMPT_TEMPLATE = """\
You are a centralized satellite network orchestrator managing a Low-Earth-Orbit constellation.
Inter-satellite links (ISL) are always available — connectivity is never the bottleneck.
Output ONLY valid JSON — no markdown, no explanation.

TASK: id={task_id}, region={region}, ram={ram} MB, anomaly="{anomaly}"

AVAILABLE SATELLITES:
{fleet_lines}

ROUTING RULES (apply in order):
  1. EU data privacy / GDPR anomaly: route to the EUROPE satellite (return its satellite_id=ID).
     Ignore task origin region. Drop only if no EUROPE satellite meets battery/RAM requirements.
  2. Data sovereignty / national jurisdiction anomaly (e.g. soberania_brasil): route to the
     satellite in the required country (Brazil→SAT in BRAZIL region). Drop only if unavailable.
  3. Critical hardware failure (broken sensor/camera): drop task entirely (satellite_id=null).
  4. No anomaly: route to any satellite in the task's region with battery_pct > 20% and sufficient RAM.

Output ONLY valid JSON:
{{"satellite_id": <integer id or null>, "reason": "one short sentence"}}
"""


class LLMScheduler:
    def __init__(self):
        if not API_KEY:
            print("CRITICAL: GEMINI_API_KEY not found in .env!")
        else:
            print(f">>> [ENGINE] LLM Scheduler Initialized ({LLM_MODEL} | rate limit={RPM_LIMIT} RPM)")
        self._call_timestamps: collections.deque = collections.deque()

    # ------------------------------------------------------------------ #
    # Rate limiter (sliding window — idêntico ao SLM)                     #
    # ------------------------------------------------------------------ #

    def _rate_limit_wait(self):
        now = time.monotonic()
        while self._call_timestamps and now - self._call_timestamps[0] > 60.0:
            self._call_timestamps.popleft()
        if len(self._call_timestamps) >= RPM_LIMIT:
            wait = 61.0 - (now - self._call_timestamps[0])
            if wait > 0:
                print(f"   [LLM Rate Limiter] {len(self._call_timestamps)} calls/min — waiting {wait:.1f}s")
                time.sleep(wait)
            now = time.monotonic()
            while self._call_timestamps and now - self._call_timestamps[0] > 60.0:
                self._call_timestamps.popleft()
        self._call_timestamps.append(time.monotonic())

    # ------------------------------------------------------------------ #
    # Construção do prompt                                                 #
    # ------------------------------------------------------------------ #

    def _build_prompt(self, task_dict, fleet):
        fleet_lines = "\n".join(
            f"  SAT {s['id']} | region={s['region']}"
            f" | battery_pct={s['battery_pct']:.0f}%"
            f" | solar_charging={s['solar_charging']}"
            f" | ram_free={s['ram_free']} MB"
            for s in fleet
        )
        return _PROMPT_TEMPLATE.format(
            task_id=task_dict.get("id"),
            region=task_dict.get("region", "?"),
            ram=task_dict.get("ram", 0),
            anomaly=task_dict.get("semantic_anomaly", "none"),
            fleet_lines=fleet_lines,
        )

    # ------------------------------------------------------------------ #
    # Chamada API                                                          #
    # ------------------------------------------------------------------ #

    def _call_api(self, prompt):
        if not API_KEY:
            return None
        self._rate_limit_wait()
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{LLM_MODEL}:generateContent?key={API_KEY}")
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                "maxOutputTokens": 128,
            },
        }
        for attempt in range(3):
            try:
                t0 = time.perf_counter()
                r = requests.post(url, headers=headers, json=data, verify=False, timeout=60)
                latency_ms = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    print(f"   [LLM] Resposta em {latency_ms:.0f}ms")
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                elif r.status_code == 429:
                    wait = 30 * (attempt + 1)
                    print(f"   [LLM Rate Limit] Tentativa {attempt+1}/3 — aguardando {wait}s")
                    time.sleep(wait)
                    continue
                else:
                    print(f"   [LLM Error] HTTP {r.status_code} — {r.text[:120]}")
                    break
            except Exception as e:
                print(f"   [LLM Connection Error] Tentativa {attempt+1}/3: {e}")
                continue
        return None

    # ------------------------------------------------------------------ #
    # Interface principal                                                  #
    # ------------------------------------------------------------------ #

    def decide(self, task_dict, fleet, battery_safety_pct=20.0):
        # Pré-filtro: se não há satélite na região com bateria suficiente, poupa a chamada de API
        valid_exists = any(
            s.get("region") == task_dict.get("region")
            and s.get("battery_pct", 100.0) > battery_safety_pct
            for s in fleet
        )
        if not valid_exists:
            return None

        prompt = self._build_prompt(task_dict, fleet)
        raw = self._call_api(prompt)
        if not raw:
            return None

        try:
            # JSON mode ativo para Flash-Lite — resposta já é JSON puro
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extrai primeiro objeto JSON do texto livre
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if not match:
                print(f"   [LLM Parse Error] Nenhum JSON encontrado: {raw[:80]}")
                return None
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError as e:
                print(f"   [LLM Parse Error] JSON inválido: {e} | raw={raw[:80]}")
                return None

        sat_id = parsed.get("satellite_id")
        reason = parsed.get("reason", "")
        print(f"   [LLM] satellite_id={sat_id} | reason={reason}")
        return sat_id
