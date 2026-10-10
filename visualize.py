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


def _filter_unknown_agent_nodes(nodes):
    display_nodes = []
    node_id_map = {}

    for node in nodes:
        node_id = node.get("id")
        if _is_unknown_agent_node(node):
            continue

        display_nodes.append(node)
        node_id_map[node_id] = node_id

    return display_nodes, node_id_map


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
    nodes, node_id_map = _filter_unknown_agent_nodes(
        data.get("nodes", [])
    )
    for node in nodes:
        node_id = node.get("id")
        base_label = node.get("label", node_id)
        attrs = node.get("attributes", {})
        if base_label in constraint_labels and not attrs.get("stage3_mapping"):
            continue

        category = node.get("category", "Entity")

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
        mapping_labels = {
            "stage2_mapping": "Stage 2 Mapping",
            "stage3_mapping": "Stage 3 Mapping",
        }
        attr_lines = [
            f"<b>{mapping_labels.get(k, k)}</b>: {v}"
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
        title_html = (
            f"<div style='font-family: sans-serif;'>"
            f"<b>{base_label}</b> <i>({category})</i><br>"
            f"<hr style='margin: 4px 0; border-color: #555;'>"
            f"{attr_html if attr_html else 'No extra context'}"
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
        if m_type == "Constraint":
            constraint_type = edge.get("constraint_type", "")
            if constraint_type:
                edge_title += f"<br>Constraint Type: {constraint_type}"

        # Morphism ごとの色分け
        color_map = {
            "Action": "#2ECC71",      # 緑: 動作・作用
            "Cause": "#E74C3C",       # 赤: 因果関係
            "State": "#00C2A8",       # 緑系: 状態
            "Relation": "#9B59B6",    # 紫: 一般関係
            "Manner": "#3498DB",
            "Temporal": "#E67E22",
            "Concession": "#F1C40F",
            "Constraint": "#FFD166",
        }
        constraint_colors = {
            "ClauseCondition": "#FFD166",
            "SpatialTemporalCondition": "#F4A261",
            "PassiveState": "#C084FC",
        }
        edge_color = (
            constraint_colors.get(edge.get("constraint_type"), color_map.get("Constraint", "#FFD166"))
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

    legend_html = """
    <div id="morphism-legend" style="position: fixed; right: 18px; bottom: 18px; z-index: 9999; max-width: 260px; background: rgba(34, 34, 34, 0.92); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; padding: 10px 12px; box-shadow: 0 4px 18px rgba(0,0,0,0.35); color: #ffffff; font-family: sans-serif; font-size: 12px;">
      <div style="margin: 0 0 8px 0; font-weight: 700; letter-spacing: 0.04em; color: #FFFFFF;">Morphism legend</div>
      <div style="display: grid; gap: 6px;">
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #2ECC71; border-radius: 2px;"></span>Action</div>
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #E74C3C; border-radius: 2px;"></span>Cause</div>
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #00C2A8; border-radius: 2px;"></span>State</div>
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #9B59B6; border-radius: 2px;"></span>Relation</div>
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #3498DB; border-radius: 2px;"></span>Manner</div>
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #E67E22; border-radius: 2px;"></span>Temporal</div>
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #F1C40F; border-radius: 2px;"></span>Concession</div>
        <div style="display: flex; align-items: center; gap: 8px;"><span style="display:inline-block; width: 18px; height: 3px; background: #FFD166; border-radius: 2px; border-style: dashed; border-width: 1.5px;"></span>Constraint</div>
      </div>
    </div>
    """

    with open(output_html, "r", encoding="utf-8") as f:
        html = f.read()
    if "Morphism legend" not in html:
        html = html.replace("</body>", f"{legend_html}\n</body>", 1)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"可視化完了: '{output_html}' を出力しました。")
    print("ブラウザで開いて確認してください（例: open index.html または ダブルクリック）。")


if __name__ == "__main__":
    visualize_topological_graph()
