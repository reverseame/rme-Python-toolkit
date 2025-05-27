import json
from pathlib import Path

import networkx as nx
from flask import Flask, jsonify, render_template

# Inicialización de la aplicación Flask y grafo
app = Flask(
    __name__,
    template_folder=str(
        (Path(__file__).resolve().parent.parent / "templates").resolve()
    ),
)
G = nx.DiGraph()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/graph")
def full_graph():
    """
    Devuelve el grafo completo en formato JSON para el frontend.
    """
    elements = []
    for node_id, data in G.nodes(data=True):
        elements.append({"data": {"id": node_id, **data}})
    for src, tgt in G.edges():
        elements.append({"data": {"source": src, "target": tgt}})
    return jsonify(elements=elements)


def load_graph(input_file: str):
    """
    Carga datos desde input_file (JSON) y construye el grafo con nodos
    de tipo category, rule_group, rule_variant y api, enriquecidos con
    sus atributos (description, tags, mbcs, attck).
    El campo 'count' se define como el número de hijos inmediatos.
    """
    global G
    with open(input_file) as f:
        eventos = json.load(f)

    G = nx.DiGraph()
    G.add_node("root", label="Root", type="root")

    for ev in eventos:
        rule_tx = ev.get("taxonomy", {}).get("rule", {})
        var_tx  = ev.get("taxonomy", {}).get("variant", {})

        category_name = rule_tx.get("categories", ["unknown"])[0]
        cat_id        = f"category::{category_name}"
        rule_name     = ev.get("rule", {}).get("name", "unknown")
        rule_id       = f"rule::{category_name}::{rule_name}"
        variant_name  = ev.get("rule", {}).get("variant")
        var_id        = f"variant::{category_name}::{rule_name}::{variant_name}"
        api_name      = ev.get("api", "unknown")
        api_id        = f"api::{category_name}::{rule_name}::{variant_name or 'direct'}::{api_name}"

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

    # Calcular 'count' como número de hijos inmediatos
    for node in G.nodes:
        G.nodes[node]["count"] = G.out_degree(node)


def serve_graph(input_file: str):
    """
    Carga el grafo y lanza el servidor Flask en el puerto 8080 en modo debug.
    """
    load_graph(input_file)
    app.run(debug=True, port=8080)
