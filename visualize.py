import json
import os
import re
import sys
from pyvis.network import Network


def _is_unknown_agent_node(node):
    if node.get("category") != "Entity":
        return False
    label = str(node.get("label", "")).strip().casefold()
    return label in {"", "unknown", "none", "null"}


def _group_agent_nodes(nodes):
    display_nodes = []
    node_id_map = {}
    grouped_agent_counts = {}
    agent_groups = {}

    for node in nodes:
        node_id = node.get("id")
        if _is_unknown_agent_node(node):
            continue

        if node.get("category") != "Entity":
            display_nodes.append(node)
            node_id_map[node_id] = node_id
            continue

        label = str(node.get("label", "")).strip()
        group_key = label.casefold()
        representative = agent_groups.get(group_key)
        if representative is None:
            representative = dict(node)
            agent_groups[group_key] = representative
            display_nodes.append(representative)
            grouped_agent_counts[node_id] = 1
            node_id_map[node_id] = node_id
        else:
            representative_id = representative.get("id")
            grouped_agent_counts[representative_id] += 1
            node_id_map[node_id] = representative_id

    return display_nodes, node_id_map, grouped_agent_counts


def visualize_topological_graph(
    json_path="topological_graph.json", output_html="index.html"
):
    """topological_graph.json を読み込み、インタラクティブなHTMLネットワークグラフを出力します。"""
    if not os.path.exists(json_path):
        print(f"エラー: 入力ファイル '{json_path}' が見つかりません。")
        sys.exit(1)

    print(f"'{json_path}' を読み込んで可視化を開始します...")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    particles_path = os.path.join(os.path.dirname(json_path), "data", "particles.json")
    constraint_labels = set()
    if os.path.exists(particles_path):
        with open(particles_path, "r", encoding="utf-8") as f:
            particles = json.load(f)
        for particle in particles:
            constraints = particle.get("constraints") or []
            if isinstance(constraints, str):
                constraints = [constraints]
            constraint_labels.update(str(value).strip() for value in constraints)

    # ネットワークグラフの初期化（有向グラフ）
    net = Network(
        height="800px", width="100%", directed=True, bgcolor="#222222", font_color="white"
    )

    # 物理演算のレイアウト調整（ノードが見やすく反発して広がる設定）
    net.barnes_hut(
        gravity=-3000, central_gravity=0.3, spring_length=150, spring_strength=0.05
    )

    # 1. Nodes (Objects: Entity / Event) の配置
    nodes, node_id_map, grouped_agent_counts = _group_agent_nodes(
        data.get("nodes", [])
    )
    for node in nodes:
        node_id = node.get("id")
        base_label = node.get("label", node_id)
        grouped_count = grouped_agent_counts.get(node_id, 1)
        if grouped_count > 1:
            base_label = f"{base_label} ({grouped_count} mentions)"
        if base_label in constraint_labels:
            continue

        category = node.get("category", "Entity")
        attrs = node.get("attributes", {})

        # when や where があればラベルの後ろに括弧書きで追記する
        context_text = []
        if attrs.get("when") and attrs["when"] != "Unspecified":
            context_text.append(attrs["when"])
        if attrs.get("where") and attrs["where"] != "Unspecified":
            context_text.append(attrs["where"])

        if context_text:
             # 例: "Unknown (in the meeting)" や "I (after)" になる
            display_label = f"{base_label}\n[{', '.join(context_text)}]"
        else:
            display_label = base_label

        stage5_process = attrs.get("stage5_process", "")
        stage5_category = (
            re.search(r"\[Category:\s*([^\]]+)\]", stage5_process)
            if isinstance(stage5_process, str)
            else None
        )
        has_stage5 = bool(stage5_process or attrs.get("stage5_result"))


        # ツールチップ（マウスホバー時の表示）に 5W1H 属性を整形
        attr_lines = [
            f"<b>{k}</b>: {v}"
            for k, v in attrs.items()
            if k not in {"agent", "stage5_process", "stage5_result"}
            and v
            and v != "Unspecified"
        ]
        if stage5_category:
            attr_lines.append(f"<b>Category</b>: {stage5_category.group(1).strip()}")
        stage5_result = attrs.get("stage5_result")
        if stage5_result and stage5_result != "Unspecified":
            attr_lines.append(f"<b>Interpretation</b>: {stage5_result}")
        attr_html = "<br>".join(attr_lines)
        group_note = (
            "<br><i>Grouped by matching label only; identity is unresolved.</i>"
            if grouped_count > 1
            else ""
        )

        title_html = (
            f"<div style='font-family: sans-serif;'>"
            f"<b>{base_label}</b> <i>({category})</i><br>"
            f"<hr style='margin: 4px 0; border-color: #555;'>"
            f"{attr_html if attr_html else 'No extra context'}{group_note}"
            f"</div>"
        )

        # Entity (Who) = シアン/円、Event (What) = オレンジ/ひし形
        if category == "Entity":
            color = "#00ADB5"
            shape = "dot"
            size = 25
        elif has_stage5:
            color = {
                "background": "#FF2E63",
                "border": "#FFD166",
                "highlight": {"background": "#FF2E63", "border": "#FFFFFF"},
            }
            shape = "diamond"
            size = 36
        else:
            color = "#FF2E63"
            shape = "diamond"
            size = 30

        net.add_node(
            node_id,
            label=display_label,
            title=title_html,
            color=color,
            borderWidth=5 if has_stage5 else 1,
            shape=shape,
            size=size,
            font={"size": 14, "color": "#FFFFFF"},
        )

    # 2. Edges (Morphisms: Action / Cause / Constraint / Relation) の配置
    edges = data.get("edges", [])
    displayed_edges = set()
    for edge in edges:
        if edge.get("morphism_type") == "Constraint":
            continue

        src = node_id_map.get(edge.get("source"))
        tgt = node_id_map.get(edge.get("target"))
        if src is None or tgt is None or src == tgt:
            continue
        m_type = edge.get("morphism_type", "Relation")
        detail = edge.get("detail", "")
        how = edge.get("how", "")
        edge_key = (src, tgt, m_type, detail, how)
        if edge_key in displayed_edges:
            continue
        displayed_edges.add(edge_key)

        # ホバー時の説明
        edge_title = f"Type: {m_type}"
        if detail:
            edge_title += f"<br>Detail: {detail}"
        if how:
            edge_title += f"<br>How: {how}"

        # Morphism ごとの色分け
        color_map = {
            "Action": "#2ECC71",      # 緑: 動作・作用
            "Cause": "#E74C3C",       # 赤: 因果関係
            "Relation": "#9B59B6",    # 紫: 一般関係
            "Manner": "#3498DB",
            "Temporal": "#E67E22",
        }
        constraint_colors = {
            "ClauseCondition": "#FFD166",
            "SpatialTemporalCondition": "#F4A261",
            "PassiveState": "#C084FC",
        }
        edge_color = (
            constraint_colors.get(edge.get("constraint_type"), color_map["Constraint"])
            if m_type == "Constraint"
            else color_map.get(m_type, "#AAAAAA")
        )
        edge_options = {
            "color": edge_color,
            "width": 2,
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.8}},
            "font": {"size": 10, "color": "#EEEEEE", "align": "middle"},
        }
        if m_type == "Constraint":
            edge_options.update(
                {
                    "dashes": [8, 5],
                    "width": 3,
                    "arrows": {
                        "to": {
                            "enabled": True,
                            "type": "triangle",
                            "scaleFactor": 1.1,
                        }
                    },
                    "smooth": {"enabled": True, "type": "curvedCW", "roundness": 0.25},
                }
            )

        net.add_edge(
            src,
            tgt,
            label=m_type,
            title=edge_title,
            **edge_options,
        )

    # HTML出力
    net.write_html(output_html)
    print(f"可視化完了: '{output_html}' を出力しました。")
    print("ブラウザで開いて確認してください（例: open index.html または ダブルクリック）。")


if __name__ == "__main__":
    visualize_topological_graph()
