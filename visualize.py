import json
import os
import sys
from pyvis.network import Network


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

    # ネットワークグラフの初期化（有向グラフ）
    net = Network(
        height="800px", width="100%", directed=True, bgcolor="#222222", font_color="white"
    )

    # 物理演算のレイアウト調整（ノードが見やすく反発して広がる設定）
    net.barnes_hut(
        gravity=-3000, central_gravity=0.3, spring_length=150, spring_strength=0.05
    )

    # 1. Nodes (Objects: Entity / Event) の配置
    nodes = data.get("nodes", [])
    for node in nodes:
        node_id = node.get("id")
        base_label = node.get("label", node_id)
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


        # ツールチップ（マウスホバー時の表示）に 5W1H 属性を整形
        attr_lines = [
            f"<b>{k}</b>: {v}"
            for k, v in attrs.items()
            if v and v != "Unspecified"
        ]
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
        else:
            color = "#FF2E63"
            shape = "diamond"
            size = 30

        net.add_node(
            node_id,
            label=display_label,
            title=title_html,
            color=color,
            shape=shape,
            size=size,
            font={"size": 14, "color": "#FFFFFF"},
        )

    # 2. Edges (Morphisms: Action / Cause / Constraint / Relation) の配置
    edges = data.get("edges", [])
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        m_type = edge.get("morphism_type", "Relation")
        detail = edge.get("detail", "")
        how = edge.get("how", "")

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
            "Constraint": "#F1C40F",  # 黄: 制約・属性
            "Relation": "#9B59B6",    # 紫: 一般関係
        }
        edge_color = color_map.get(m_type, "#AAAAAA")

        net.add_edge(
            src,
            tgt,
            label=m_type,
            title=edge_title,
            color=edge_color,
            width=2,
            arrows={"to": {"enabled": True, "scaleFactor": 0.8}},
            font={"size": 10, "color": "#EEEEEE", "align": "middle"},
        )

    # HTML出力
    net.write_html(output_html)
    print(f"可視化完了: '{output_html}' を出力しました。")
    print("ブラウザで開いて確認してください（例: open index.html または ダブルクリック）。")


if __name__ == "__main__":
    visualize_topological_graph()
