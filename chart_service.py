"""Plotly chart configuration builder."""

# Color palette
COLORS = [
    "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
    "#f43f5e", "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#06b6d4", "#3b82f6",
]

# Keywords that indicate a series name is a metric (not a category label)
METRIC_KEYWORDS = {
    "revenue", "sales", "count", "total", "profit", "margin", "orders",
    "amount", "percentage", "percent", "rate", "ratio", "roi", "value",
    "price", "quantity", "qty", "avg", "average", "mean", "median", "sum",
    "spend", "cost", "lifetime", "units", "volume", "ltv", "aov",
}


def _looks_like_metric_name(name: str) -> bool:
    n = (name or "").lower()
    return any(kw in n for kw in METRIC_KEYWORDS)


def _normalize_series_data(data: dict) -> dict:
    """
    Detect and fix malformed multi-series data where the LLM sent one
    series per category. Returns a single flat series when the pattern
    is detected, otherwise the data unchanged.

    Patterns fixed:
    A) Every series has x and y of length 1 (one point per series).
    B) Series names don't look like metric names (e.g. "Italy", "Germany")
       — we collapse by taking each series's max y value.
    """
    if not isinstance(data, dict) or len(data) < 2:
        return data
    series_items = [(n, s) for n, s in data.items() if isinstance(s, dict)]
    if len(series_items) < 2:
        return data

    # Pattern A: every series is a single point
    if all(
        len(s.get("x", [])) == 1 and len(s.get("y", [])) == 1
        for _, s in series_items
    ):
        xs = [s.get("x", [n])[0] for n, s in series_items]
        ys = [s.get("y", [0])[0] for _, s in series_items]
        return {"Value": {"x": xs, "y": ys}}

    # Pattern B: series names are category labels, not metric names
    series_names = [n for n, _ in series_items]
    if not any(_looks_like_metric_name(n) for n in series_names):
        # Treat each series name as a category, take its highest y as the value
        xs = series_names
        ys = []
        for _, s in series_items:
            y_vals = s.get("y", [])
            # Prefer max non-zero; fall back to first
            nonzero = [v for v in y_vals if v]
            ys.append(max(nonzero) if nonzero else (y_vals[0] if y_vals else 0))
        return {"Value": {"x": xs, "y": ys}}

    return data


def _sort_by_value(x_vals, y_vals, descending=True):
    """Sort two parallel lists by y_vals."""
    if not x_vals or not y_vals or len(x_vals) != len(y_vals):
        return x_vals, y_vals
    try:
        pairs = sorted(zip(x_vals, y_vals), key=lambda p: p[1], reverse=descending)
        return [p[0] for p in pairs], [p[1] for p in pairs]
    except Exception:
        return x_vals, y_vals


def _max_label_len(labels) -> int:
    if not labels:
        return 0
    return max((len(str(l)) for l in labels), default=0)


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

    # Safety net: fix malformed multi-series data
    if chart_type in ("bar", "hbar", "line", "area"):
        data = _normalize_series_data(data)

    # Auto-upgrade bar → hbar if labels are long
    if chart_type == "bar":
        series_items = [(n, s) for n, s in data.items() if isinstance(s, dict)]
        if len(series_items) == 1:
            first_x = series_items[0][1].get("x", [])
            if _max_label_len(first_x) > 10 or len(first_x) > 8:
                chart_type = "hbar"

    traces = []
    color_idx = 0
    y_tick_labels = []  # track for dynamic margin

    if chart_type == "pie":
        labels = data.get("labels")
        values = data.get("values")
        if not labels:
            for _key, series in data.items():
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
                "marker": {"color": COLORS[color_idx % len(COLORS)], "size": 9, "opacity": 0.75},
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
                "line": {"color": COLORS[color_idx % len(COLORS)], "width": 2.5, "shape": "spline", "smoothing": 0.4},
                "marker": {"size": 7, "color": COLORS[color_idx % len(COLORS)]},
            })
            color_idx += 1

    elif chart_type == "area":
        for name, series in data.items():
            if not isinstance(series, dict):
                continue
            color = COLORS[color_idx % len(COLORS)]
            traces.append({
                "type": "scatter",
                "mode": "lines",
                "name": name,
                "x": series.get("x", []),
                "y": series.get("y", []),
                "fill": "tozeroy" if color_idx == 0 else "tonexty",
                "line": {"color": color, "width": 2},
                "fillcolor": color + "33",  # add alpha
            })
            color_idx += 1

    elif chart_type == "hbar":
        series_items = [(n, s) for n, s in data.items() if isinstance(s, dict)]
        multi_series = len(series_items) > 1
        for i, (name, series) in enumerate(series_items):
            y_vals = series.get("x", series.get("y", []))
            x_vals = series.get("y", series.get("x", []))
            # Sort ascending so the biggest bar is at the top
            if not multi_series:
                y_vals, x_vals = _sort_by_value(y_vals, x_vals, descending=False)
                y_tick_labels = y_vals
            marker = (
                {"color": COLORS[i % len(COLORS)], "opacity": 0.9}
                if multi_series
                else {"color": list(reversed(COLORS[:len(y_vals)])), "opacity": 0.9}
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
            if not multi_series:
                x_vals, y_vals = _sort_by_value(x_vals, y_vals, descending=True)
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

    # ── Layout ────────────────────────────────────────────────────────────
    # Dynamic left margin for hbar based on longest label
    if chart_type == "hbar":
        max_len = _max_label_len(y_tick_labels)
        left_margin = max(80, min(220, 8 * max_len + 20))
    else:
        left_margin = 60

    layout = {
        "title": {"text": title, "font": {"size": 16}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, system-ui, sans-serif", "color": "#e2e8f0", "size": 12},
        "margin": {"l": left_margin, "r": 30, "t": 50, "b": 80},
        "showlegend": len(traces) > 1,
        "legend": {"orientation": "h", "y": -0.2},
        "bargap": 0.2,
        "bargroupgap": 0.06,
    }

    if chart_type not in ("pie", "funnel"):
        # X-axis label rotation heuristic
        if chart_type == "hbar":
            xaxis_tickangle = 0
        else:
            # Look at first series x-labels to decide rotation
            first = next(iter(data.values()), {}) if isinstance(data, dict) else {}
            xs = first.get("x", []) if isinstance(first, dict) else []
            if _max_label_len(xs) > 8 or len(xs) > 6:
                xaxis_tickangle = -35
            else:
                xaxis_tickangle = 0

        layout["xaxis"] = {
            "title": x_label,
            "gridcolor": "rgba(148,163,184,0.1)",
            "tickangle": xaxis_tickangle,
            "linecolor": "rgba(148,163,184,0.2)",
            "automargin": True,
        }
        layout["yaxis"] = {
            "title": y_label if chart_type != "hbar" else x_label,
            "gridcolor": "rgba(148,163,184,0.1)",
            "linecolor": "rgba(148,163,184,0.2)",
            "automargin": True,
        }

    return {"data": traces, "layout": layout}
