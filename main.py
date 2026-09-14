# main.py (topological-mapping リポジトリ用)

import json
import urllib.request
from src.graph import GraphBuilder

# particle-encapsulation リポジトリの particle.json の Raw URL
URL = "https://raw.githubusercontent.com/ao-labs-123/particle-encapsulation/main/data/particle.json"
LOCAL_FILE = "particle.json"

def main():
    print("Fetching particle.json from GitHub...")
    with urllib.request.urlopen(URL) as response:
        particle_data = json.loads(response.read().decode())
    
    with open(LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump(particle_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved to {LOCAL_FILE}!")

    # 粒子データから圏論的グラフ（Node / Edge）を構築
    graph = GraphBuilder.build_graph(particle_data)
    
    print(f"\n--- Generated Topological Graph ---")
    print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
    
    # 出力結果を topological_graph.json に保存
    with open("topological_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
