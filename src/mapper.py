import json

def process_topological_mapping(input_logs):
    """Inputモジュールのログを受け取り、トポロジー情報（継承層）を追記する"""
    for entry in input_logs:
        input_text = entry.get("input", "")
        # input_analysis がない場合の安全策も入れておく
        input_analysis = entry.get("input_analysis", entry)
        stage2 = input_analysis.get("stage2", {})
        agent = stage2.get("resolved_agent", "Unknown")

        # トポロジーマッピング層を追記（継承）
        entry["topological_mapping"] = {
            "status": "Success" if agent != "Unknown" else "Incomplete",
            "category_of_entities": {
                "subject": agent,
                "with_whom": None
            },
            "category_of_events": {
                "what": input_text,
                "when": "unspecified",
                "why": "unspecified"
            },
            "morphism": {
                "relation": f"Subject({agent}) -> Event",
                "constraint": "none"
            }
        }
    return input_logs
