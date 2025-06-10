import hashlib
import json
from collections import defaultdict
from pathlib import Path

import networkx as nx
from flask import Flask, jsonify, render_template

# Initialize Flask app with custom template and static folder paths
app = Flask(
    __name__,
    template_folder=str(
        (Path(__file__).resolve().parent.parent / "ui").resolve()
    ),
    static_folder=str(
        (Path(__file__).resolve().parent.parent / "ui/static").resolve()
    ),
)

# Global graph instance (loaded once per run)
G = None


@app.route("/")
def index():
    """Serve the main frontend page."""
    return render_template("index.html")


@app.route("/graph")
def graph():
    """Serve the graph data as JSON, formatted for D3.js consumption."""
    if G is None:
        return jsonify({"error": "Graph not loaded"}), 500

    elements = []
    for node_id, attrs in G.nodes(data=True):
        elements.append({"data": {"id": node_id, **attrs}})

    for source, target in G.edges():
        elements.append({"data": {"source": source, "target": target}})

    return jsonify({"elements": elements})


def safe_set_count(graph: nx.DiGraph):
    """
    Set the 'count' attribute on each node:
    - For intermediate nodes: use the number of direct children (out_degree)
    - For leaf nodes of type 'api_detail': preserve existing count
    """
    for node in graph.nodes:
        if graph.nodes[node].get("type") != "api_detail":
            graph.nodes[node]["count"] = graph.out_degree(node)


def load_graph(input_file: str):
    """
    Build a hierarchical graph from a JSON file.

    Nodes:
    - root
    - category
    - rule_group
    - rule_variant
    - api
    - api_detail (aggregated identical API calls under each api)

    Relationships are constructed as:
    root → category → rule_group → rule_variant? → api → api_detail
    """
    global G
    with open(input_file) as f:
        events = json.load(f)

    G = nx.DiGraph()
    G.add_node("root", label="Root", type="root")

    # Collect all API call attributes grouped by full API ID
    api_instance_map = defaultdict(list)

    for ev in events:
        rule_tx = ev.get("taxonomy", {}).get("rule", {})
        var_tx = ev.get("taxonomy", {}).get("variant", {})

        category_name = rule_tx.get("categories", ["unknown"])[0]
        cat_id = f"category::{category_name}"

        rule_name = ev.get("rule", {}).get("name", "unknown")
        rule_id = f"rule::{category_name}::{rule_name}"

        variant_name = ev.get("rule", {}).get("variant")
        var_id = f"variant::{category_name}::{rule_name}::{variant_name}"

        api_name = ev.get("api", "unknown")
        api_id = f"api::{category_name}::{rule_name}::{variant_name or 'direct'}::{api_name}"

        # Register API call attributes for grouping later
        api_instance_map[api_id].append(ev.get("attributes", {}))

        # Create hierarchy: root → category → rule → (variant) → api
        if not G.has_node(cat_id):
            G.add_node(cat_id, label=category_name, type="category",
                       description=rule_tx.get("description", ""),
                       tags=rule_tx.get("tags", []))
        G.add_edge("root", cat_id)

        if not G.has_node(rule_id):
            G.add_node(rule_id, label=rule_name, type="rule_group",
                       description=rule_tx.get("description", ""),
                       mbcs=rule_tx.get("mbcs", []),
                       attck=rule_tx.get("attck", []))
        G.add_edge(cat_id, rule_id)

        parent = rule_id
        if variant_name and variant_name.strip() and variant_name != rule_name:
            if not G.has_node(var_id):
                G.add_node(var_id, label=variant_name, type="rule_variant",
                           description=var_tx.get("description", ""),
                           mbcs=var_tx.get("mbcs", []),
                           attck=var_tx.get("attck", []))
            G.add_edge(rule_id, var_id)
            parent = var_id

        if not G.has_node(api_id):
            G.add_node(api_id, label=api_name, type="api")
        G.add_edge(parent, api_id)

    # Add api_detail nodes grouped by identical attributes
    for api_id, calls in api_instance_map.items():
        grouped = defaultdict(list)
        for call in calls:
            key = json.dumps(call, sort_keys=True)
            hash_key = hashlib.md5(key.encode()).hexdigest()
            grouped[hash_key].append(call)

        for hash_key, group in grouped.items():
            detail_id = f"detail::{api_id}::{hash_key}"
            label = "Call"
            G.add_node(detail_id, label=label, type="api_detail",
                       arguments=group[0],  # representative example
                       count=len(group))
            G.add_edge(api_id, detail_id)

    # Assign count to each node
    safe_set_count(G)


def serve_graph(input_file: str):
    """
    Load the graph from file and start the Flask server.
    """
    load_graph(input_file)
    app.run(host="0.0.0.0", port=8080, debug=False)
