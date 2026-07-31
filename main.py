import json
from src.mapper import process_topological_mapping

def main():
    input_path = "samples/input_log_sample.json"
    output_path = "samples/output_topological.json"

    # 1. ログ読み込み
    with open(input_path, "r", encoding="utf-8") as f:
        logs = json.load(f)

    # 2. 追跡ロジック実行
    updated_logs = process_topological_mapping(logs)

    # 3. 継承されたログを書き出し
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(updated_logs, f, indent=2, ensure_ascii=False)

    print(f"Successfully processed {len(updated_logs)} samples -> {output_path}")

if __name__ == "__main__":
    main()
