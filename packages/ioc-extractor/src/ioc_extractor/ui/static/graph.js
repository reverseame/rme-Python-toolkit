const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3
  .select("#graph-container")
  .append("svg")
  .attr("width", width)
  .attr("height", height);

const g = svg.append("g");

// Zoom behavior
svg.call(
  d3
    .zoom()
    .scaleExtent([0.1, 5])
    .on("zoom", (e) => g.attr("transform", e.transform))
);

const tooltip = d3.select("#tooltip");

function showTooltip(event, d) {
  let html = `<strong>${d.label}</strong> (${d.count || 0})`;

  if (d.type === "category") {
    html += `<br/>Description: ${d.description || "N/A"}`;
    html += `<br/>Tags: ${d.tags?.join(", ") || "N/A"}`;
  }

  if (["rule_group", "rule_variant"].includes(d.type)) {
    html += `<br/>Description: ${d.description || "N/A"}`;
    html += `<br/>MBCs: ${d.mbcs?.join(", ") || "N/A"}`;
    html += `<br/>ATT&CK: ${d.attck?.join(", ") || "N/A"}`;
  }

  if (d.type === "api_detail") {
    html += `<br/>Arguments: <pre>${JSON.stringify(
      d.arguments,
      null,
      2
    )}</pre>`;
  }

  tooltip
    .html(html)
    .style("left", event.pageX + 10 + "px")
    .style("top", event.pageY + 10 + "px")
    .classed("hidden", false);
}

function hideTooltip() {
  tooltip.classed("hidden", true);
}

fetch("/graph")
  .then((res) => res.json())
  .then(({ elements }) => {
    const rawNodes = elements
      .filter((e) => !e.data.source)
      .map((e) => ({ ...e.data }));
    const rawLinks = elements
      .filter((e) => e.data.source)
      .map((e) => ({
        source: e.data.source,
        target: e.data.target,
      }));

    const nodeMap = Object.fromEntries(rawNodes.map((n) => [n.id, n]));
    const childrenMap = {};
    rawLinks.forEach((l) => {
      if (!childrenMap[l.source]) childrenMap[l.source] = [];
      childrenMap[l.source].push(l.target);
    });

    const visibleNodes = new Map(
      rawNodes
        .filter((n) => n.type !== "api_detail")
        .map((n) => [n.id, { ...n }])
    );

    const simulation = d3
      .forceSimulation()
      .force(
        "link",
        d3
          .forceLink()
          .id((d) => d.id)
          .distance(120)
          .strength(0.5)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "radial",
        d3
          .forceRadial(
            (d) => {
              const layer =
                {
                  root: 0,
                  category: 1,
                  rule_group: 2,
                  rule_variant: 3,
                  api: 4,
                  api_detail: 5,
                }[d.type] ?? 6;
              return layer * 140;
            },
            width / 2,
            height / 2
          )
          .strength(1)
      );

    const linkGroup = g.append("g");
    const nodeGroup = g.append("g");
    const labelGroup = g.append("g");

    function updateGraph() {
      const nodes = Array.from(visibleNodes.values());
      const nodeById = Object.fromEntries(nodes.map((n) => [n.id, n]));
      const validLinks = rawLinks
        .filter((l) => nodeById[l.source] && nodeById[l.target])
        .map((l) => ({
          source: nodeById[l.source],
          target: nodeById[l.target],
        }));

      // Links
      const linkSel = linkGroup
        .selectAll("line")
        .data(validLinks, (d) => `${d.source.id}-${d.target.id}`);
      linkSel.exit().remove();
      linkSel.enter().append("line").attr("class", "link").merge(linkSel);

      // Nodes
      const nodeSel = nodeGroup.selectAll("circle").data(nodes, (d) => d.id);
      nodeSel.exit().remove();
      nodeSel
        .enter()
        .append("circle")
        .attr("r", (d) => (d.type === "root" ? 36 : 22))
        .attr("class", (d) => `node node-${d.type}`)
        .on("mouseover", showTooltip)
        .on("mouseout", hideTooltip)
        .on("click", (_, d) => toggleChildren(d.id))
        .call(
          d3
            .drag()
            .on("start", (event, d) => {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            })
            .on("drag", (event, d) => {
              d.fx = event.x;
              d.fy = event.y;
            })
            .on("end", (event, d) => {
              if (!event.active) simulation.alphaTarget(0);
              d.fx = null;
              d.fy = null;
            })
        )
        .merge(nodeSel);

      // Labels
      const labelSel = labelGroup.selectAll("text").data(nodes, (d) => d.id);
      labelSel.exit().remove();
      labelSel
        .enter()
        .append("text")
        .attr("class", "nodelabel")
        .text((d) => d.label)
        .merge(labelSel);

      simulation.nodes(nodes);
      simulation.force("link").links(validLinks);
      simulation.alpha(0.8).restart();

      simulation.on("tick", () => {
        nodeGroup
          .selectAll("circle")
          .attr("cx", (d) => d.x)
          .attr("cy", (d) => d.y);

        labelGroup
          .selectAll("text")
          .attr("x", (d) => d.x)
          .attr("y", (d) => d.y);

        linkGroup
          .selectAll("line")
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);
      });
    }

    function toggleChildren(id) {
      const children = childrenMap[id] || [];
      const anyVisible = children.some((child) => visibleNodes.has(child));

      if (anyVisible) {
        const recurseRemove = (nid) => {
          (childrenMap[nid] || []).forEach((child) => {
            visibleNodes.delete(child);
            recurseRemove(child);
          });
        };
        recurseRemove(id);
      } else {
        if (!visibleNodes.has(id)) visibleNodes.set(id, nodeMap[id]);
        children.forEach((child) => visibleNodes.set(child, nodeMap[child]));
      }

      updateGraph();
    }

    updateGraph();
  });
