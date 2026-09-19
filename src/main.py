import json
import urllib.request
import os

if __package__:
    from .graph import GraphBuilder
else:
    from graph import GraphBuilder

# スクリプト（main.py）が存在するディレクトリの絶対パスを取得
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 保存先のパスを絶対パスで組み立てる
LOG_LOCAL_PATH = os.path.join(BASE_DIR, "log.json")
PARTICLES_LOCAL_PATH = os.path.join(BASE_DIR, "particles.json")
# プロジェクトルート（ひとつ上の階層）に出力したい場合はこちら:
# OUTPUT_LOCAL_PATH = os.path.join(BASE_DIR, "..", "topological_graph.json")
OUTPUT_LOCAL_PATH = os.path.join(BASE_DIR, "topological_graph.json")

# Raw URL 設定
LOG_URL = "https://raw.githubusercontent.com/ao-labs-123/input-parser/main/data/log.json"
PARTICLES_URL = "https://raw.githubusercontent.com/ao-labs-123/particle-encapsulation/main/data/particles.json"

def fetch_and_save_json(url, local_path):
    """指定したURLからJSONを取得し、ローカルに保存してデータを返す"""
    print(f"Fetching {url} ...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
    
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved to {local_path}!")
    return data

def main():
    # 1. log.json と particles.json の取得と保存
    log_data = fetch_and_save_json(LOG_URL, LOG_LOCAL_PATH)
    particle_data = fetch_and_save_json(PARTICLES_URL, PARTICLES_LOCAL_PATH)

    # 2. グラフの構築
    graph = GraphBuilder.build_graph(particle_data)

    print("\n--- Generated Topological Graph ---")
    print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")

    # 3. 構築結果を保存
    graph_dict = graph.to_dict() if hasattr(graph, 'to_dict') else graph.__dict__
    
    with open(OUTPUT_LOCAL_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, ensure_ascii=False, indent=2)
    print(f"Successfully generated {OUTPUT_LOCAL_PATH}!")

if __name__ == "__main__":
    main()
