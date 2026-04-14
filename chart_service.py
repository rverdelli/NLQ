"""Plotly chart configuration builder."""

# Color palette
COLORS = [
    "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
    "#f43f5e", "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#06b6d4", "#3b82f6",
]


def build_plotly_config(tool_input: dict) -> dict:
    """
    Convert a create_chart tool call into a Plotly JSON config
    that the frontend can render with Plotly.newPlot().
    """
    chart_type = tool_input.get("chart_type", "bar")
    title = tool_input.get("title", "Chart")
    x_label = tool_input.get("x_label", "")
    y_label = tool_input.get("y_label", "")
    data = tool_input.get("data", {})

    traces = []
    color_idx = 0

    if chart_type == "pie":
        # Pie chart: expect data with 'labels' and 'values' at top level
        # or within a single series key
        labels = data.get("labels")
        values = data.get("values")
        if not labels:
            # Try first series key
            for key, series in data.items():
                if isinstance(series, dict):
                    labels = series.get("labels", series.get("x", []))
                    values = series.get("values", series.get("y", []))
                    break
        traces.append({
            "type": "pie",
            "labels": labels or [],
            "values": values or [],
            "hole": 0.4,
            "marker": {"colors": COLORS[:len(labels or [])]},
            "textinfo": "percent+label",
            "hoverinfo": "label+value+percent",
        })

    elif chart_type == "scatter":
        for name, series in data.items():
            if not isinstance(series, dict):
                continue
            traces.append({
                "type": "scatter",
                "mode": "markers",
                "name": name,
                "x": series.get("x", []),
                "y": series.get("y", []),
                "marker": {"color": COLORS[color_idx % len(COLORS)], "size": 8, "opacity": 0.7},
            })
            color_idx += 1

    elif chart_type == "line":
        for name, series in data.items():
            if not isinstance(series, dict):
                continue
            traces.append({
                "type": "scatter",
                "mode": "lines+markers",
                "name": name,
                "x": series.get("x", []),
                "y": series.get("y", []),
                "line": {"color": COLORS[color_idx % len(COLORS)], "width": 2},
                "marker": {"size": 6},
            })
            color_idx += 1

    elif chart_type == "area":
        for name, series in data.items():
            if not isinstance(series, dict):
                continue
            traces.append({
                "type": "scatter",
                "mode": "lines",
                "name": name,
                "x": series.get("x", []),
                "y": series.get("y", []),
                "fill": "tozeroy" if color_idx == 0 else "tonexty",
                "line": {"color": COLORS[color_idx % len(COLORS)]},
            })
            color_idx += 1

    elif chart_type == "hbar":
        series_items = [(n, s) for n, s in data.items() if isinstance(s, dict)]
        multi_series = len(series_items) > 1
        for i, (name, series) in enumerate(series_items):
            y_vals = series.get("x", series.get("y", []))
            x_vals = series.get("y", series.get("x", []))
            marker = (
                {"color": COLORS[i % len(COLORS)], "opacity": 0.9}
                if multi_series
                else {"color": COLORS[:len(y_vals)], "opacity": 0.9}
            )
            traces.append({
                "type": "bar",
                "orientation": "h",
                "name": name,
                "y": y_vals,
                "x": x_vals,
                "marker": marker,
            })

    elif chart_type == "funnel":
        for name, series in data.items():
            if not isinstance(series, dict):
                continue
            traces.append({
                "type": "funnel",
                "name": name,
                "y": series.get("x", series.get("labels", [])),
                "x": series.get("y", series.get("values", [])),
                "marker": {"color": COLORS[color_idx % len(COLORS)]},
            })
            color_idx += 1

    else:  # bar (default)
        series_items = [(n, s) for n, s in data.items() if isinstance(s, dict)]
        multi_series = len(series_items) > 1
        for i, (name, series) in enumerate(series_items):
            x_vals = series.get("x", [])
            y_vals = series.get("y", [])
            marker = (
                {"color": COLORS[i % len(COLORS)], "opacity": 0.9}
                if multi_series
                else {"color": COLORS[:len(x_vals)], "opacity": 0.9}
            )
            traces.append({
                "type": "bar",
                "name": name,
                "x": x_vals,
                "y": y_vals,
                "marker": marker,
            })

    layout = {
        "title": {"text": title, "font": {"size": 16, "weight": "bold"}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, system-ui, sans-serif", "color": "#e2e8f0"},
        "margin": {"l": 60, "r": 30, "t": 50, "b": 60},
        "showlegend": len(traces) > 1,
        "legend": {"orientation": "h", "y": -0.15},
        "bargap": 0.25,
        "bargroupgap": 0.08,
    }

    if chart_type not in ("pie", "funnel"):
        layout["xaxis"] = {
            "title": x_label,
            "gridcolor": "rgba(148,163,184,0.1)",
            "tickangle": -45 if chart_type != "hbar" else 0,
            "linecolor": "rgba(148,163,184,0.2)",
        }
        layout["yaxis"] = {
            "title": y_label if chart_type != "hbar" else x_label,
            "gridcolor": "rgba(148,163,184,0.1)",
            "linecolor": "rgba(148,163,184,0.2)",
        }

    return {"data": traces, "layout": layout}
