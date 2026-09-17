# topological-mapping / main.py

import json
import urllib.request
from src.graph import GraphBuilder

LOG_URL = "https://raw.githubusercontent.com/ao-labs-123/input-parser/main/log.json"
PARTICLE_URL = "https://raw.githubusercontent.com/ao-labs-123/particle-encapsulation/main/particles.json"

def main():
    # 1. 粒子データと元のログデータの両方を取得
    with urllib.request.urlopen(PARTICLE_URL) as resp:
        particle_data = json.loads(resp.read().decode())
    with urllib.request.urlopen(LOG_URL) as resp:
        log_data = json.loads(resp.read().decode())
    
    # 2. 両方を組み合わせて位相グラフ（Node / Edge / 5W1H State）を構築
    graph = GraphBuilder.build_graph(particle_data, log_data)
    
    # 3. 出力
    with open("topological_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
