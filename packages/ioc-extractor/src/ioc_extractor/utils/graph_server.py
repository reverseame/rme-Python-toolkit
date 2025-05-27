import json
from pathlib import Path

import networkx as nx
from flask import Flask, jsonify, render_template

# Adaptación del grafo original
app = Flask(
    __name__,
    template_folder=str((Path(__file__).resolve().parent.parent / "templates").resolve()),
)
G = nx.DiGraph()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/graph")
def full_graph():
    nodes = []
    edges = []
    for node, data in G.nodes(data=True):
        nodes.append({"data": {"id": node, **data}})
    for source, target in G.edges():
        edges.append({"data": {"source": source, "target": target}})
    return jsonify(elements=nodes + edges)

def load_graph(input_file: str):
    global G
    with open(input_file) as f:
        eventos = json.load(f)

    G = nx.DiGraph()
    root_id = "root"
    G.add_node(root_id, label="Root", type="root")

    for ev in eventos:
        categoria = ev.get("taxonomy", {}).get("rule", {}).get("categories", ["unknown"])[0]
        rule_name = ev.get("rule", {}).get("name", "unknown")
        variant = ev.get("rule", {}).get("variant", None)
        api_name = ev.get("api", "unknown")

        cat_id = f"category::{categoria}"
        rule_id = f"rule::{categoria}::{rule_name}"
        api_id = f"api::{categoria}::{rule_name}::{variant or 'direct'}::{api_name}"

        if not G.has_node(cat_id):
            G.add_node(cat_id, label=categoria, type="category")
            G.add_edge(root_id, cat_id)

        if not G.has_node(rule_id):
            G.add_node(rule_id, label=rule_name, type="rule_group")
            G.add_edge(cat_id, rule_id)

        # Evitar nodo duplicado si variant es igual a rule_name o está vacío
        if variant and variant.strip() and variant != rule_name:
            var_id = f"variant::{categoria}::{rule_name}::{variant}"
            if not G.has_node(var_id):
                G.add_node(var_id, label=variant, type="rule_variant")
                G.add_edge(rule_id, var_id)
            parent_id = var_id
        else:
            parent_id = rule_id

        if not G.has_node(api_id):
            G.add_node(api_id, label=api_name, type="api")
            G.add_edge(parent_id, api_id)

def serve_graph(input_file: str):
    load_graph(input_file)
    app.run(debug=True, port=8080)
