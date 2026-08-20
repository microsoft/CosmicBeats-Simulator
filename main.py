'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
'''
import sys
import time
import random
import os
import argparse  # <-- A biblioteca mágica para terminais
from src.sim.simulator import Simulator

if __name__ == "__main__":
    # Semente fixa: Garante que os mesmos eventos acontecem para TODOS os motores
    random.seed(0) 
    
    # =================================================================
    # CONFIGURAÇÃO DO TERMINAL (CLI)
    # =================================================================
    parser = argparse.ArgumentParser(description="CosmicBeats - Simulador NTN-MEC")
    
    # Argumento 1: O Motor (com opções restritas para evitar erros de digitação)
    parser.add_argument('--engine', type=str, default="LLM", 
                        choices=["LLM", "BASELINE", "SLM", "DRL"], 
                        help="Escolha o cérebro: LLM, BASELINE, SLM, ou DRL")
    
    # Argumento 2: O arquivo de configuração JSON
    parser.add_argument('--config', type=str, default="configs/config.json", 
                        help="Caminho para o arquivo config.json")
    
    args = parser.parse_args()

    # =================================================================
    # INJEÇÃO DA CHAVE SELETORA
    # =================================================================
    os.environ["MEC_ENGINE"] = args.engine
    
    print("\n" + "="*50)
    print(f"🚀 INICIANDO COSMICBEATS")
    print(f"🧠 Motor Cognitivo : {args.engine}")
    print(f"📂 Arquivo Config  : {args.config}")
    print("="*50 + "\n")

    _sim = Simulator(args.config)

    _startTime = time.perf_counter()
    _sim.execute()
    _endTime = time.perf_counter()

    print(f"\n[Simulator Info] Tempo real de execução: {_endTime-_startTime:.4f} segundos.")