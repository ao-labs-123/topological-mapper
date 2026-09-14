import json
import urllib.request
from src.factory import ParticleFactory

# テスト用 Raw URL
URL = "https://raw.githubusercontent.com/ao-labs-123/particle-encapsulation/main/data/particle.json"
LOCAL_FILE = "particle.json"  # 保存先のローカルファイル名


def main():
    print("Fetching particle.json from GitHub...")

    # 1. GitHubからデータを取得
    with urllib.request.urlopen(URL) as response:
        raw_data = response.read().decode("utf-8")
        log_data = json.loads(raw_data)

    # 2. ローカルの log.json にそのまま保存（反映）
    with open(LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved to {LOCAL_FILE}!")


if __name__ == "__main__":
    main()
