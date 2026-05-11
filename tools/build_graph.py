#!/usr/bin/env python3
"""Build a deterministic graph from xWiki wikilinks.

The graph uses only explicit Obsidian-style links, so it is reproducible and
does not invent relationships. Outputs are written to graph/ by default.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict, deque
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "_wiki"
GRAPH_DIR = REPO_ROOT / "graph"
GRAPH_JSON = GRAPH_DIR / "graph.json"
GRAPH_HTML = GRAPH_DIR / "graph.html"
GRAPH_REPORT = GRAPH_DIR / "graph-report.md"

TYPE_COLORS = {
    "source": "#2f7d32",
    "concept": "#b26a00",
    "entity": "#1565c0",
    "synthesis": "#6a1b9a",
    "question": "#00695c",
    "timeline": "#ad1457",
    "index": "#455a64",
    "log": "#5d4037",
    "unknown": "#616161",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def wiki_pages() -> list[Path]:
    if not WIKI_DIR.exists():
        return []
    return sorted(
        p
        for p in WIKI_DIR.rglob("*.md")
        if p.name not in {"log.md", "health-report.md", "lint-report.md", "graph-report.md"}
    )


def frontmatter_value(content: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*['\"]?(.+?)['\"]?\s*$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def page_type(content: str) -> str:
    value = frontmatter_value(content, "type")
    return value if value in TYPE_COLORS else "unknown"


def page_title(path: Path, content: str) -> str:
    title = frontmatter_value(content, "title")
    if title:
        return title
    heading = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
    return heading.group(1).strip() if heading else path.stem


def page_id(path: Path) -> str:
    return path.relative_to(WIKI_DIR).as_posix().removesuffix(".md")


def normalize_link(value: str) -> str:
    value = value.strip()
    value = value.split("|", 1)[0]
    value = value.split("#", 1)[0]
    value = value.removesuffix(".md")
    return re.sub(r"\s+", " ", value).casefold()


def extract_wikilinks(content: str) -> list[str]:
    return sorted(set(re.findall(r"\[\[([^\]]+)\]\]", content)))


def build_page_lookup(pages: list[Path]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for page in pages:
        content = read_text(page)
        pid = page_id(page)
        candidates = {
            page.stem,
            pid,
            page.relative_to(WIKI_DIR).as_posix(),
            page_title(page, content),
        }
        for candidate in candidates:
            lookup[normalize_link(candidate)] = pid
    return lookup


def build_graph() -> tuple[list[dict], list[dict], list[dict]]:
    pages = wiki_pages()
    lookup = build_page_lookup(pages)
    nodes = []
    edges = []
    unresolved = []
    seen_edges = set()

    for page in pages:
        content = read_text(page)
        pid = page_id(page)
        body_preview = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", content, flags=re.DOTALL)
        preview = " ".join(line.strip() for line in body_preview.splitlines() if line.strip())[:220]
        ptype = page_type(content)
        nodes.append(
            {
                "id": pid,
                "label": page_title(page, content),
                "type": ptype,
                "path": rel(page),
                "color": TYPE_COLORS[ptype],
                "preview": preview,
            }
        )

        for link in extract_wikilinks(content):
            target = lookup.get(normalize_link(link))
            if not target:
                unresolved.append({"from": pid, "link": link})
                continue
            if target == pid:
                continue
            key = (pid, target)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(
                {
                    "id": f"{pid}->{target}",
                    "from": pid,
                    "to": target,
                    "type": "EXTRACTED",
                    "confidence": 1.0,
                }
            )

    return nodes, edges, unresolved


def adjacency(nodes: list[dict], edges: list[dict]) -> dict[str, set[str]]:
    graph = {node["id"]: set() for node in nodes}
    for edge in edges:
        graph[edge["from"]].add(edge["to"])
        graph[edge["to"]].add(edge["from"])
    return graph


def connected_components(graph: dict[str, set[str]]) -> list[set[str]]:
    seen = set()
    components = []
    for node in graph:
        if node in seen:
            continue
        component = set()
        queue = deque([node])
        seen.add(node)
        while queue:
            current = queue.popleft()
            component.add(current)
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return sorted(components, key=len, reverse=True)


def find_phantom_hubs(unresolved: list[dict], min_refs: int = 2) -> list[dict]:
    refs: dict[str, set[str]] = defaultdict(set)
    for item in unresolved:
        refs[item["link"]].add(item["from"])
    hubs = [
        {"link": link, "ref_count": len(sources), "referenced_by": sorted(sources)}
        for link, sources in refs.items()
        if len(sources) >= min_refs
    ]
    return sorted(hubs, key=lambda item: (-item["ref_count"], item["link"].casefold()))


def graph_report(nodes: list[dict], edges: list[dict], unresolved: list[dict]) -> str:
    graph = adjacency(nodes, edges)
    node_types = {node["id"]: node["type"] for node in nodes}
    degrees = {node: len(neighbors) for node, neighbors in graph.items()}
    degree_values = list(degrees.values())
    mean_degree = statistics.mean(degree_values) if degree_values else 0
    stdev_degree = statistics.pstdev(degree_values) if len(degree_values) > 1 else 0
    hub_threshold = mean_degree + (2 * stdev_degree)
    hubs = sorted(
        [
            {"id": node, "degree": degree}
            for node, degree in degrees.items()
            if degree > 0 and degree >= hub_threshold and node_types.get(node) != "index"
        ],
        key=lambda item: (-item["degree"], item["id"]),
    )
    orphans = sorted(node for node, degree in degrees.items() if degree == 0)
    components = connected_components(graph)
    phantom_hubs = find_phantom_hubs(unresolved)
    node_count = len(nodes)
    edge_count = len(edges)
    orphan_pct = (len(orphans) / node_count * 100) if node_count else 0

    lines = [
        f"# xWiki Graph Report - {date.today().isoformat()}",
        "",
        "## Summary",
        "",
        f"- Nodes: {node_count}",
        f"- Edges: {edge_count}",
        f"- Edge/node ratio: {(edge_count / node_count):.2f}" if node_count else "- Edge/node ratio: 0.00",
        f"- Orphan pages: {len(orphans)} ({orphan_pct:.1f}%)",
        f"- Connected components: {len(components)}",
        f"- Unresolved wikilinks: {len(unresolved)}",
        "",
        f"## Orphan Pages ({len(orphans)})",
        "",
    ]
    lines.extend([f"- `{node}`" for node in orphans] or ["No orphan pages."])
    lines.extend(["", f"## Hub Pages ({len(hubs)})", ""])
    lines.extend([f"- `{hub['id']}` - degree {hub['degree']}" for hub in hubs] or ["No disproportionate hubs."])
    lines.extend(["", f"## Phantom Hubs ({len(phantom_hubs)})", ""])
    if phantom_hubs:
        for hub in phantom_hubs:
            refs = ", ".join(f"`{src}`" for src in hub["referenced_by"])
            lines.append(f"- `[[{hub['link']}]]` - {hub['ref_count']} references from {refs}")
    else:
        lines.append("No missing pages are referenced by multiple wiki pages.")
    lines.extend(["", f"## Largest Components ({min(5, len(components))})", ""])
    for idx, component in enumerate(components[:5], 1):
        sample = ", ".join(f"`{node}`" for node in sorted(component)[:8])
        more = " ..." if len(component) > 8 else ""
        lines.append(f"- Component {idx}: {len(component)} pages - {sample}{more}")
    return "\n".join(lines)


def write_html(nodes: list[dict], edges: list[dict]) -> None:
    data = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>xWiki Graph</title>
  <style>
    html, body {{ width: 100%; height: 100%; margin: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f7f4; color: #1f2933; overflow: hidden; }}
    #toolbar {{ position: fixed; z-index: 2; top: 12px; left: 12px; background: white; border: 1px solid #ddd; padding: 10px 12px; border-radius: 6px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }}
    #toolbar strong {{ display: block; margin-bottom: 4px; }}
    #graph {{ width: 100vw; height: 100vh; display: block; }}
    .edge {{ stroke: #8a8f98; stroke-opacity: .42; stroke-width: 1; }}
    .node {{ stroke: #fff; stroke-width: 1.5; cursor: pointer; }}
    .label {{ font-size: 11px; fill: #1f2933; pointer-events: none; paint-order: stroke; stroke: #f7f7f4; stroke-width: 3px; stroke-linejoin: round; }}
    .tip {{ position: fixed; display: none; max-width: 360px; background: #111827; color: white; padding: 8px 10px; border-radius: 6px; font-size: 12px; line-height: 1.4; z-index: 3; }}
  </style>
</head>
<body>
  <div id="toolbar">
    <strong>xWiki Graph</strong>
    <span>{len(nodes)} nodes, {len(edges)} links</span>
  </div>
  <svg id="graph" role="img" aria-label="xWiki link graph"></svg>
  <div id="tip" class="tip"></div>
  <script>
    const graph = {data};
    const svg = document.getElementById("graph");
    const tip = document.getElementById("tip");
    const width = window.innerWidth;
    const height = window.innerHeight;
    svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);

    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.max(180, Math.min(width, height) * 0.38);
    const nodes = graph.nodes.map((node, index) => {{
      const angle = (Math.PI * 2 * index) / graph.nodes.length - Math.PI / 2;
      const ring = node.type === "index" ? 0 : radius;
      return {{
        ...node,
        x: centerX + Math.cos(angle) * ring,
        y: centerY + Math.sin(angle) * ring
      }};
    }});
    const byId = new Map(nodes.map(node => [node.id, node]));

    function el(name, attrs = {{}}, text = "") {{
      const node = document.createElementNS("http://www.w3.org/2000/svg", name);
      Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
      if (text) node.textContent = text;
      svg.appendChild(node);
      return node;
    }}

    graph.edges.forEach(edge => {{
      const from = byId.get(edge.from);
      const to = byId.get(edge.to);
      if (!from || !to) return;
      el("line", {{ class: "edge", x1: from.x, y1: from.y, x2: to.x, y2: to.y }});
    }});

    nodes.forEach(node => {{
      const size = node.type === "index" ? 10 : 7;
      const circle = el("circle", {{ class: "node", cx: node.x, cy: node.y, r: size, fill: node.color }});
      circle.addEventListener("mousemove", event => {{
        tip.style.display = "block";
        tip.style.left = `${{event.clientX + 12}}px`;
        tip.style.top = `${{event.clientY + 12}}px`;
        tip.innerHTML = `<strong>${{node.label}}</strong><br>${{node.path}}<br><br>${{node.preview || ""}}`;
      }});
      circle.addEventListener("mouseleave", () => {{ tip.style.display = "none"; }});
      if (node.type !== "source" || graph.nodes.length < 80) {{
        const label = node.label.length > 30 ? `${{node.label.slice(0, 29)}}...` : node.label;
        el("text", {{ class: "label", x: node.x + 10, y: node.y + 4 }}, label);
      }}
    }});
  </script>
</body>
</html>
"""
    GRAPH_HTML.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic xWiki graph.")
    parser.add_argument("--json-only", action="store_true", help="Only write graph/graph.json.")
    parser.add_argument("--report", action="store_true", help="Print a graph health report.")
    parser.add_argument("--save-report", action="store_true", help="Save graph/graph-report.md.")
    args = parser.parse_args()

    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    nodes, edges, unresolved = build_graph()
    payload = {
        "built": date.today().isoformat(),
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
    }
    GRAPH_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if not args.json_only:
        write_html(nodes, edges)

    report = graph_report(nodes, edges, unresolved)
    if args.report:
        print(report)
    if args.save_report:
        GRAPH_REPORT.write_text(report, encoding="utf-8")
        print(f"Saved: {rel(GRAPH_REPORT)}")
    if not args.report and not args.save_report:
        print(f"Wrote {rel(GRAPH_JSON)}")
        if not args.json_only:
            print(f"Wrote {rel(GRAPH_HTML)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
