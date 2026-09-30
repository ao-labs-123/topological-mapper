import argparse
import json
import urllib.request
import os

if __package__:
    from .graph import GraphBuilder
    from .upstream_adapter import build_graph_from_upstream_payload, load_upstream_json, load_upstream_repo
else:
    from graph import GraphBuilder
    from upstream_adapter import build_graph_from_upstream_payload, load_upstream_json, load_upstream_repo

# スクリプト（main.py）が存在するディレクトリの絶対パスを取得
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# 保存先のパスを絶対パスで組み立てる
LOG_LOCAL_PATH = os.path.join(DATA_DIR, "log.json")
PARTICLES_LOCAL_PATH = os.path.join(DATA_DIR, "particles.json")
OUTPUT_LOCAL_PATH = os.path.join(PROJECT_ROOT, "topological_graph.json")

# Raw URL 設定
LOG_URL = "https://raw.githubusercontent.com/ao-labs-123/input-parser/main/data/log.json"
PARTICLES_URL = "https://raw.githubusercontent.com/ao-labs-123/particle-encapsulation/main/particles.json"

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
    parser = argparse.ArgumentParser(description="Generate topological graph from particle and log data.")
    parser.add_argument("--upstream-json", type=str, default=None, help="Path to an upstream JSON payload with particles/records or data/records.")
    parser.add_argument("--upstream-dir", type=str, default=None, help="Path to a repo containing both particles.json and a log file.")
    parser.add_argument("--upstream-particle-dir", type=str, default=None, help="Path to the particle-encapsulation repo containing particles.json.")
    parser.add_argument("--upstream-log-dir", type=str, default=None, help="Path to the input-parser repo containing data/log.json.")
    parser.add_argument("--output", type=str, default=OUTPUT_LOCAL_PATH, help="Destination JSON path for the generated graph.")
    args = parser.parse_args()

    if args.upstream_json:
        payload = load_upstream_json(args.upstream_json)
        graph = build_graph_from_upstream_payload(payload)
    elif args.upstream_dir or args.upstream_particle_dir or args.upstream_log_dir:
        particle_data, log_data = load_upstream_repo(
            args.upstream_dir,
            particle_repo_dir=args.upstream_particle_dir,
            log_repo_dir=args.upstream_log_dir,
        )
        graph = GraphBuilder.build_graph(particle_data, log_data)
    else:
        # 1. log.json と particles.json の取得と保存
        log_data = fetch_and_save_json(LOG_URL, LOG_LOCAL_PATH)
        particle_data = fetch_and_save_json(PARTICLES_URL, PARTICLES_LOCAL_PATH)

        # 2. グラフの構築
        graph = GraphBuilder.build_graph(particle_data, log_data)

    print("\n--- Generated Topological Graph ---")
    print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")

    # 3. 構築結果を保存
    graph_dict = graph.to_dict() if hasattr(graph, 'to_dict') else graph.__dict__

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, ensure_ascii=False, indent=2)
    print(f"Successfully generated {output_path}!")

if __name__ == "__main__":
    main()
