"""Plotly chart configuration builder."""
import sys
import json

# Color palette
COLORS = [
    "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
    "#f43f5e", "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#06b6d4", "#3b82f6",
]


def _cycle_colors(n: int) -> list:
    """Return a list of n colors, cycling through the palette."""
    return [COLORS[i % len(COLORS)] for i in range(n)]


# Max items to display in ranking charts (bar/hbar) before truncating
MAX_BARS = 15

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
    series per category. Returns a single flat series when any of these
    patterns is detected:

    A) Every series has y of length 1 (one point per series).
    B) Every series has AT MOST one non-zero y value (one bar per series
       spread across a shared x array — very common LLM mistake).
    C) No series name looks like a metric keyword (all category labels).

    IMPORTANT early exit: if any series has >= 3 data points, we treat
    the input as a legitimate multi-series comparison (e.g. YoY:
    {"2022": {x: months, y: [12 vals]}, "2023": {...}, "2024": {...}})
    and return it unchanged. Normalization only runs on SPARSE data.
    """
    if not isinstance(data, dict) or len(data) < 2:
        return data
    series_items = [(n, s) for n, s in data.items() if isinstance(s, dict)]
    if len(series_items) < 2:
        return data

    def _nonzero_values(y_vals):
        return [v for v in y_vals if v]

    # Early exit: if any series has >= 3 non-zero data points, treat as
    # legit multi-series (e.g. YoY with 12 months per year). Sparse
    # malformed data has only 0 or 1 non-zero value per series.
    max_nonzero = max(
        (len(_nonzero_values(s.get("y", []))) for _, s in series_items),
        default=0,
    )
    if max_nonzero >= 3:
        return data

    # Pattern A: every series is a single point
    if all(
        len(s.get("y", [])) == 1
        for _, s in series_items
    ):
        xs = []
        ys = []
        for n, s in series_items:
            x_val = s.get("x", [])
            xs.append(x_val[0] if x_val else n)
            y_val = s.get("y", [0])
            ys.append(y_val[0] if y_val else 0)
        return {"Value": {"x": xs, "y": ys}}

    # Pattern B: every series has at most one non-zero y value
    nonzero_counts = [len(_nonzero_values(s.get("y", []))) for _, s in series_items]
    if all(c <= 1 for c in nonzero_counts):
        xs = [n for n, _ in series_items]
        ys = []
        for _, s in series_items:
            nz = _nonzero_values(s.get("y", []))
            ys.append(max(nz) if nz else 0)
        return {"Value": {"x": xs, "y": ys}}

    # Pattern C: no series name looks like a metric (all category labels)
    series_names = [n for n, _ in series_items]
    if not any(_looks_like_metric_name(n) for n in series_names):
        xs = series_names
        ys = []
        for _, s in series_items:
            y_vals = s.get("y", [])
            nz = _nonzero_values(y_vals)
            ys.append(max(nz) if nz else (y_vals[0] if y_vals else 0))
        return {"Value": {"x": xs, "y": ys}}

    # Pattern D (final safety net): too many series (>= 5) — legitimate
    # multi-metric comparisons rarely have > 4 series.
    if len(series_items) >= 5:
        xs = series_names
        ys = []
        for _, s in series_items:
            y_vals = s.get("y", [])
            nz = _nonzero_values(y_vals)
            ys.append(max(nz) if nz else (y_vals[0] if y_vals else 0))
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

    # Debug: log what the LLM sent so we can diagnose malformed charts
    try:
        preview = {k: {kk: (vv[:3] if isinstance(vv, list) else vv) for kk, vv in v.items()}
                   if isinstance(v, dict) else v for k, v in list(data.items())[:5]}
        print(f"[chart] type={chart_type} series_count={len(data)} sample={json.dumps(preview, default=str)[:400]}", file=sys.stderr)
    except Exception:
        pass

    # Safety net: fix malformed multi-series data
    if chart_type in ("bar", "hbar", "line", "area"):
        before_keys = list(data.keys())[:5]
        data = _normalize_series_data(data)
        if list(data.keys()) != before_keys:
            print(f"[chart] normalized → keys={list(data.keys())}", file=sys.stderr)

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
            "marker": {"colors": _cycle_colors(len(labels or []))},
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
            raw_x = series.get("x", [])
            raw_y = series.get("y", [])
            # For hbar: labels go on y, values go on x.
            # Detect which is which by type — strings = labels, numbers = values
            x_is_num = raw_x and isinstance(raw_x[0], (int, float))
            y_is_num = raw_y and isinstance(raw_y[0], (int, float))
            if y_is_num and not x_is_num:
                # Standard: x=labels, y=values → swap for hbar
                y_vals = raw_x
                x_vals = raw_y
            elif x_is_num and not y_is_num:
                # Already hbar-shaped: x=values, y=labels
                y_vals = raw_y
                x_vals = raw_x
            else:
                # Fallback: assume x=labels, y=values
                y_vals = raw_x
                x_vals = raw_y
            # Sort descending, then keep top N, then reverse so biggest is on top
            if not multi_series:
                y_vals, x_vals = _sort_by_value(y_vals, x_vals, descending=True)
                y_vals = y_vals[:MAX_BARS]
                x_vals = x_vals[:MAX_BARS]
                y_vals = list(reversed(y_vals))
                x_vals = list(reversed(x_vals))
                y_tick_labels = y_vals
            marker = (
                {"color": COLORS[i % len(COLORS)], "opacity": 0.9}
                if multi_series
                else {"color": list(reversed(_cycle_colors(len(y_vals)))), "opacity": 0.9}
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
                x_vals = x_vals[:MAX_BARS]
                y_vals = y_vals[:MAX_BARS]
            marker = (
                {"color": COLORS[i % len(COLORS)], "opacity": 0.9}
                if multi_series
                else {"color": _cycle_colors(len(x_vals)), "opacity": 0.9}
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

    # Dynamic height for hbar so every bar label fits
    if chart_type == "hbar":
        n_bars = len(y_tick_labels) if y_tick_labels else 0
        chart_height = max(400, 36 * n_bars + 120)
    else:
        chart_height = 400

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
        "height": chart_height,
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
        # Force every y-tick label to appear in horizontal bar charts
        if chart_type == "hbar":
            layout["yaxis"]["tickmode"] = "linear"
            layout["yaxis"]["dtick"] = 1

    return {"data": traces, "layout": layout}
