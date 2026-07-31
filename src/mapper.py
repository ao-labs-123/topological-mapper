import json

def process_topological_mapping(input_logs):
    updated_logs = []
    
    for entry in input_logs:
        # entry が文字列（"It is required..."）の場合と、辞書（{"input": "..."}）の場合の両方に対応
        if isinstance(entry, str):
            input_text = entry
            agent = "Unknown"  # 単文の場合は後続処理やトポロジーエンジンで特定
            
            # 追跡用オブジェクトの基本構造を作成
            log_item = {
                "input": input_text,
                "topological_mapping": {
                    "status": "Incomplete",
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
            }
            updated_logs.append(log_item)
            
        elif isinstance(entry, dict):
            input_text = entry.get("input", "")
            stage2 = entry.get("stage2", {})
            agent = stage2.get("resolved_agent", "Unknown")
            
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
            updated_logs.append(entry)
            
    return updated_logs
