"""EvalKit CLI — from EVALKIT_MASTER_SPEC_v2.md Section 9."""
import json
import sys
import time
from pathlib import Path
import httpx
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

app = typer.Typer(name="evalkit", help="QA-Grade RAG Evaluation Platform")
console = Console()

DEFAULT_BASE_URL = "http://localhost:8000"


def _get_base_url() -> str:
    return DEFAULT_BASE_URL


def _handle_error(resp: httpx.Response):
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        console.print(f"[red]Error {resp.status_code}:[/red] {detail}")
        raise typer.Exit(1)


@app.command()
def evaluate(
    query: str = typer.Option(..., help="The query to evaluate"),
    response: str = typer.Option(..., help="The RAG response"),
    contexts: str = typer.Option(..., help="Path to contexts JSON file"),
    project_id: str = typer.Option("default", help="Project ID"),
    format: str = typer.Option("summary", help="Output format: summary, json, markdown"),
):
    """Run a full RAG evaluation."""
    try:
        with open(contexts) as f:
            ctx_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error reading contexts file:[/red] {e}")
        raise typer.Exit(1)

    if isinstance(ctx_data, list):
        ctx_list = ctx_data
    else:
        console.print("[red]Contexts file must contain a JSON array[/red]")
        raise typer.Exit(1)

    payload = {
        "project_id": project_id,
        "query": query,
        "response": response,
        "contexts": ctx_list,
    }

    with httpx.Client(base_url=_get_base_url(), timeout=60) as client:
        resp = client.post("/v1/evaluate", json=payload)
        _handle_error(resp)
        data = resp.json()

    if format == "json":
        console.print_json(json.dumps(data, indent=2))
    elif format == "markdown":
        from evalkit.reporting.markdown_report import generate_markdown_report
        md = generate_markdown_report(data)
        console.print(Markdown(md))
    else:
        _print_summary(data)


@app.command(name="check-chunks")
def check_chunks(
    file: str = typer.Option(..., help="Path to chunks JSON file"),
    domain: str = typer.Option(None, help="Domain for calibration"),
):
    """Evaluate chunk quality before indexing."""
    try:
        with open(file) as f:
            chunks = json.load(f)
    except Exception as e:
        console.print(f"[red]Error reading chunks file:[/red] {e}")
        raise typer.Exit(1)

    payload = {"chunks": chunks}
    if domain:
        payload["domain"] = domain

    with httpx.Client(base_url=_get_base_url(), timeout=60) as client:
        resp = client.post("/v1/evaluate/chunks", json=payload)
        _handle_error(resp)
        data = resp.json()

    quality = data.get("overall_quality", "unknown")
    quality_color = {"good": "green", "acceptable": "yellow", "poor": "red"}.get(quality, "white")
    console.print(Panel(
        f"[{quality_color}]{quality.upper()}[/{quality_color}] \u2014 Score: {data.get('score', 0):.2f}",
        title="Chunk Quality",
    ))

    summary = data.get("summary", {})
    console.print(f"  Evaluated: {summary.get('chunks_evaluated', 0)}")
    console.print(f"  Boundary issues: {summary.get('boundary_issues', 0)}")
    console.print(f"  Coherence issues: {summary.get('coherence_issues', 0)}")
    console.print(f"  Density issues: {summary.get('density_issues', 0)}")

    for issue in data.get("issues", []):
        console.print(f"  [yellow]\u2022 {issue['chunk_id']}:[/yellow] {issue['issue']} \u2014 {issue['detail']}")


@app.command()
def compare(
    run_a: str = typer.Option(..., help="First run ID"),
    run_b: str = typer.Option(..., help="Second run ID"),
):
    """Compare two evaluation runs."""
    with httpx.Client(base_url=_get_base_url(), timeout=30) as client:
        resp = client.get("/v1/compare", params={"run_a": run_a, "run_b": run_b})
        _handle_error(resp)
        data = resp.json()

    verdict = data.get("verdict", "unknown")
    verdict_color = {"improved": "green", "stable": "yellow", "degraded": "red"}.get(verdict, "white")
    console.print(f"\nVerdict: [{verdict_color}]{verdict.upper()}[/{verdict_color}]")

    table = Table(title="Metric Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Run A", justify="right")
    table.add_column("Run B", justify="right")
    table.add_column("Delta", justify="right")
    table.add_column("Delta %", justify="right")

    for d in data.get("deltas", []):
        val_a = f"{d['run_a_value']:.4f}" if d["run_a_value"] is not None else "N/A"
        val_b = f"{d['run_b_value']:.4f}" if d["run_b_value"] is not None else "N/A"
        delta = f"{d['delta']:+.4f}" if d["delta"] is not None else "\u2014"
        delta_pct = f"{d['delta_pct']:+.1f}%" if d["delta_pct"] is not None else "\u2014"
        table.add_row(d["metric"], val_a, val_b, delta, delta_pct)

    console.print(table)

    if data.get("regressions"):
        console.print(f"\n[red]\u26a0 Regressions detected in {len(data['regressions'])} metric(s)[/red]")


@app.command(name="list")
def list_evals(
    project: str = typer.Option(..., help="Project ID"),
):
    """List evaluations for a project."""
    with httpx.Client(base_url=_get_base_url(), timeout=30) as client:
        resp = client.get("/v1/evaluations", params={"project_id": project})
        _handle_error(resp)
        data = resp.json()

    if not data:
        console.print("[yellow]No evaluations found.[/yellow]")
        return

    table = Table(title=f"Evaluations for {project}")
    table.add_column("Run ID", style="cyan")
    table.add_column("Verdict")
    table.add_column("Root Cause")
    table.add_column("Created")

    for e in data:
        verdict = e.get("verdict", "?")
        color = {"PASS": "green", "FAIL": "red", "WARN": "yellow"}.get(verdict, "white")
        table.add_row(
            e.get("run_id", "")[:12] + "...",
            f"[{color}]{verdict}[/{color}]",
            e.get("root_cause_code", "?"),
            e.get("created_at", "?")[:19],
        )

    console.print(table)


@app.command()
def show(run_id: str = typer.Argument(..., help="Evaluation run ID")):
    """Show detailed evaluation results."""
    with httpx.Client(base_url=_get_base_url(), timeout=30) as client:
        resp = client.get(f"/v1/evaluations/{run_id}")
        _handle_error(resp)
        data = resp.json()

    from evalkit.reporting.markdown_report import generate_markdown_report
    md = generate_markdown_report(data)
    console.print(Markdown(md))


@app.command(name="run-suite")
def run_suite(
    file: str = typer.Option(..., help="Path to golden JSONL file"),
    project: str = typer.Option(..., help="Project name"),
    baseline: bool = typer.Option(False, help="Mark passing runs as baseline"),
):
    """Run a golden test suite against the API."""
    filepath = Path(file)
    if not filepath.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    cases = []
    with open(filepath) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as e:
                console.print(f"[red]Parse error line {lineno}:[/red] {e}")
                raise typer.Exit(1)

    console.print(f"Loaded [bold]{len(cases)}[/bold] test cases from {file}")

    base_url = _get_base_url()
    with httpx.Client(base_url=base_url, timeout=120) as client:
        resp = client.post("/v1/projects", json={"name": project})
        if resp.status_code == 201:
            project_id = resp.json()["id"]
        else:
            projects = client.get("/v1/projects").json()
            project_id = next((p["id"] for p in projects if p["name"] == project), None)
            if not project_id:
                console.print(f"[red]Failed to create or find project:[/red] {project}")
                raise typer.Exit(1)

        console.print(f"Project: [cyan]{project}[/cyan] (id={project_id})")

        table = Table(title="Golden Suite Results")
        table.add_column("#", style="dim", width=8)
        table.add_column("Description", width=45)
        table.add_column("Expected", width=12)
        table.add_column("Actual", width=12)
        table.add_column("Root Cause", width=28)
        table.add_column("Match", width=6)

        passed = 0
        passing_run_ids = []

        for case in cases:
            case_id = case.get("id", "?")
            desc = case.get("description", "")[:44]
            expected = case.get("expected", {})
            payload = dict(case["input"])
            payload["project_id"] = project_id

            t0 = time.time()
            resp = client.post("/v1/evaluate", json=payload, timeout=120)
            elapsed = time.time() - t0

            if resp.status_code != 200:
                table.add_row(case_id, desc, expected.get("verdict", "?"), "[red]ERROR[/red]", f"[red]{resp.status_code}[/red]", "[red]ERR[/red]")
                continue

            data = resp.json()
            act_v = data.get("summary", {}).get("verdict", "?")
            act_rc = data.get("root_cause", {}).get("code", "?")
            act_sev = data.get("root_cause", {}).get("severity", "?")
            exp_v = expected.get("verdict", "?")
            exp_rc = expected.get("root_cause_code", "?")

            v_match = act_v == exp_v
            rc_match = act_rc == exp_rc
            all_match = v_match and rc_match

            v_color = {"PASS": "green", "FAIL": "red", "WARN": "yellow"}.get(act_v, "white")
            rc_str = f"{act_rc}" if rc_match else f"[red]{act_rc}[/red] (exp {exp_rc})"
            match_str = "[green]PASS[/green]" if all_match else "[red]FAIL[/red]"

            if all_match:
                passed += 1
                if run_id := data.get("run_id"):
                    passing_run_ids.append(run_id)

            table.add_row(case_id, desc, exp_v, f"[{v_color}]{act_v}[/{v_color}]", rc_str, match_str)

        console.print(table)

        total = len(cases)
        pct = (passed / total * 100) if total else 0
        color = "green" if pct == 100 else "yellow" if pct >= 70 else "red"
        console.print(Panel(
            f"[{color}]{passed}/{total} cases matched ({pct:.0f}%)[/{color}]",
            title="Summary",
        ))

        if baseline and passing_run_ids:
            console.print(f"\nMarking {len(passing_run_ids)} passing runs as baseline...")
            for run_id in passing_run_ids:
                client.post(f"/v1/evaluations/{run_id}/baseline")
            console.print("[green]Done.[/green]")


def _print_summary(data: dict):
    summary = data.get("summary", {})
    root_cause = data.get("root_cause", {})
    verdict = summary.get("verdict", "?")
    verdict_emoji = {"PASS": "\u2705", "FAIL": "\u274c", "WARN": "\u26a0\ufe0f"}.get(verdict, "\u2753")
    verdict_color = {"PASS": "green", "FAIL": "red", "WARN": "yellow"}.get(verdict, "white")

    console.print(Panel(
        f"[{verdict_color}]{verdict_emoji} {verdict}[/{verdict_color}]  |  "
        f"Root Cause: [bold]{root_cause.get('code', '?')}[/bold] ({root_cause.get('severity', '?')})  |  "
        f"Score: {summary.get('overall_score', 0):.2f}",
        title=f"EvalKit \u2014 Run {data.get('run_id', '?')[:12]}",
    ))

    console.print(f"\n{root_cause.get('message', '')}")

    anomalies = data.get("anomalies", [])
    if anomalies:
        console.print(f"\n[yellow]Anomalies ({len(anomalies)}):[/yellow]")
        for a in anomalies:
            console.print(f"  \u26a0 {a['code']}: {a['message']}")

    fixes = data.get("fix_suggestions", [])
    if fixes:
        console.print(f"\n[cyan]Fixes ({len(fixes)}):[/cyan]")
        for f in fixes:
            console.print(f"  \u2192 [{f.get('priority', '?')}] {f['action']}")

    telemetry = data.get("telemetry", {})
    console.print(f"\n[dim]Latency: {telemetry.get('total_latency_ms', 0)}ms | Cost: ${telemetry.get('estimated_cost_usd', 0):.4f} | Tokens: {telemetry.get('tokens_used', 0)}[/dim]")


if __name__ == "__main__":
    app()
