"""
SentinelForge CLI
Enterprise AI Security Testing Command-Line Interface
"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="sf",
    help="SentinelForge - Enterprise AI Security Testing & Red Teaming Platform",
    no_args_is_help=True,
)
console = Console()

# Sub-command groups
auth_app = typer.Typer(help="Authentication commands")
tools_app = typer.Typer(help="BlackICE tool management")
attack_app = typer.Typer(help="Attack scenario management")
report_app = typer.Typer(help="Report generation and management")
probe_app = typer.Typer(help="Probe module management")
agent_app = typer.Typer(help="AI Agent testing (NEW)")
drift_app = typer.Typer(help="Model drift detection (NEW)")
synthetic_app = typer.Typer(help="Synthetic data generation (NEW)")
supply_chain_app = typer.Typer(help="Supply chain scanning (NEW)")
backdoor_app = typer.Typer(help="Backdoor detection scanning (NEW)")
webhook_app = typer.Typer(help="Webhook notification management (NEW)")
playbook_app = typer.Typer(help="IR playbook management")

app.add_typer(auth_app, name="auth")
app.add_typer(tools_app, name="tools")
app.add_typer(attack_app, name="attack")
app.add_typer(report_app, name="report")
app.add_typer(probe_app, name="probe")
app.add_typer(agent_app, name="agent")
app.add_typer(drift_app, name="drift")
app.add_typer(synthetic_app, name="synthetic")
app.add_typer(supply_chain_app, name="supply-chain")
app.add_typer(backdoor_app, name="backdoor")
app.add_typer(webhook_app, name="webhook")
app.add_typer(playbook_app, name="playbook")


# ─── Configuration ──────────────────────────────────────────
CONFIG_DIR = Path.home() / ".sentinelforge"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _get_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _get_api_url() -> str:
    config = _get_config()
    return config.get("api_url", "http://localhost:8000")


def _get_headers() -> dict:
    config = _get_config()
    token = config.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _api_request(method: str, path: str, **kwargs) -> dict:
    """Make an API request."""
    import httpx

    url = f"{_get_api_url()}{path}"
    headers = _get_headers()
    headers.update(kwargs.pop("headers", {}))
    try:
        with httpx.Client(timeout=30) as client:
            response = client.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                console.print("[red]✗ Not authenticated. Run: sf auth login[/red]")
                raise typer.Exit(1)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API at {url}[/red]")
        console.print(
            "[dim]Make sure SentinelForge services are running: docker compose up -d[/dim]"
        )
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(
            f"[red]✗ API error: {e.response.status_code} - {e.response.text}[/red]"
        )
        raise typer.Exit(1)


# ─── Version ────────────────────────────────────────────────
@app.command()
def version():
    """Show SentinelForge version."""
    console.print(
        Panel(
            "[bold cyan]SentinelForge CLI v1.4.0[/bold cyan]\n"
            "Enterprise AI Security Testing Platform\n"
            "[dim]https://github.com/CambridgeAnalytica/-SentinelForge[/dim]",
            title="🛡️ SentinelForge",
            border_style="cyan",
        )
    )


# ─── Auth Commands ──────────────────────────────────────────
@auth_app.command("login")
def auth_login(
    api_url: str = typer.Option(
        "http://localhost:8000", "--api-url", help="API base URL"
    ),
    username: str = typer.Option(None, prompt=True),
    password: str = typer.Option(None, prompt=True, hide_input=True),
):
    """Authenticate with SentinelForge API."""
    import httpx

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{api_url}/auth/login",
                json={"username": username, "password": password},
            )
            response.raise_for_status()
            data = response.json()
            _save_config(
                {
                    "api_url": api_url,
                    "token": data["access_token"],
                    "username": username,
                }
            )
            console.print("[green]✓ Login successful![/green]")
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to {api_url}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPStatusError:
        console.print("[red]✗ Invalid credentials[/red]")
        raise typer.Exit(1)


@auth_app.command("status")
def auth_status():
    """Check authentication status."""
    data = _api_request("GET", "/auth/status")
    console.print("[green]✓ Authenticated[/green]")
    console.print(f"  User: {data['username']}")
    console.print(f"  Role: {data['role']}")


@auth_app.command("logout")
def auth_logout():
    """Logout from current session."""
    config = _get_config()
    config.pop("token", None)
    _save_config(config)
    console.print("Successfully logged out")


# ─── Tools Commands ─────────────────────────────────────────
@tools_app.command("list")
def tools_list():
    """List all available BlackICE tools."""
    data = _api_request("GET", "/tools/")

    table = Table(title="Available Tools", border_style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Category")
    table.add_column("Version")
    table.add_column("Description")

    for tool in data:
        table.add_row(
            tool["name"],
            tool["category"],
            tool["version"],
            (
                tool["description"][:50] + "…"
                if len(tool["description"]) > 50
                else tool["description"]
            ),
        )

    console.print(table)


@tools_app.command("info")
def tools_info(tool_name: str = typer.Argument(..., help="Tool name")):
    """Get detailed info about a specific tool."""
    data = _api_request("GET", f"/tools/{tool_name}")

    console.print(
        Panel(
            f"[bold]{data['name']}[/bold] v{data['version']}\n"
            f"Category: {data['category']}\n"
            f"Description: {data['description']}\n\n"
            f"[bold]Capabilities:[/bold]\n"
            + "\n".join(f"  • {c}" for c in data.get("capabilities", []))
            + "\n\n"
            "[bold]MITRE ATLAS:[/bold]\n"
            + "\n".join(f"  • {m}" for m in data.get("mitre_atlas", [])),
            title=f"🔧 Tool: {data['name']}",
            border_style="cyan",
        )
    )


@tools_app.command("run")
def tools_run(
    tool_name: str = typer.Argument(..., help="Tool name"),
    target: str = typer.Argument(..., help="Target model or endpoint"),
    timeout: int = typer.Option(600, help="Timeout in seconds"),
):
    """Execute a tool against a target."""
    console.print(f"Running [bold]{tool_name}[/bold] against [cyan]{target}[/cyan]...")
    data = _api_request(
        "POST",
        f"/tools/{tool_name}/run",
        json={
            "target": target,
            "timeout": timeout,
        },
    )
    console.print(f"Status: {data['status']}")
    if data.get("output"):
        console.print(Panel(data["output"], title="Output"))


# ─── Attack Commands ────────────────────────────────────────
@attack_app.command("list")
def attack_list():
    """List all available attack scenarios."""
    data = _api_request("GET", "/attacks/scenarios")

    table = Table(title="Attack Scenarios", border_style="red")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Tools")

    for scenario in data:
        table.add_row(
            scenario["id"],
            scenario["name"],
            ", ".join(scenario.get("tools", [])),
        )

    console.print(table)


@attack_app.command("run")
def attack_run(
    scenario: str = typer.Argument(..., help="Scenario ID"),
    target: str = typer.Option(..., "--target", "-t", help="Target model"),
):
    """Run an attack scenario against a model."""
    console.print(
        f"Launching attack: [bold red]{scenario}[/bold red] → [cyan]{target}[/cyan]"
    )
    data = _api_request(
        "POST",
        "/attacks/run",
        json={
            "scenario_id": scenario,
            "target_model": target,
        },
    )

    console.print(
        Panel(
            f"Run ID: {data['id']}\n"
            f"Status: {data['status']}\n"
            f"Created: {data['created_at']}\n\n"
            f"Track progress: [dim]sf attack runs {data['id']}[/dim]",
            title="⚔️ Attack Launched",
            border_style="red",
        )
    )


@attack_app.command("runs")
def attack_runs(run_id: str = typer.Argument(None, help="Specific run ID")):
    """List all runs or get status of specific run."""
    if run_id:
        data = _api_request("GET", f"/attacks/runs/{run_id}")
        console.print(
            Panel(
                f"Scenario: {data['scenario_id']}\n"
                f"Target: {data['target_model']}\n"
                f"Status: {data['status']}\n"
                f"Progress: {data['progress']}%\n"
                f"Findings: {len(data.get('findings', []))}",
                title=f"Run: {data['id'][:12]}…",
                border_style="cyan",
            )
        )

        if data.get("findings"):
            table = Table(title="Findings")
            table.add_column("Severity", style="bold")
            table.add_column("Tool")
            table.add_column("Title")
            for f in data["findings"]:
                sev_color = {
                    "critical": "red",
                    "high": "yellow",
                    "medium": "bright_yellow",
                    "low": "blue",
                }.get(f["severity"], "dim")
                table.add_row(
                    f"[{sev_color}]{f['severity'].upper()}[/{sev_color}]",
                    f["tool_name"],
                    f["title"],
                )
            console.print(table)
    else:
        data = _api_request("GET", "/attacks/runs")
        table = Table(title="Recent Attack Runs", border_style="cyan")
        table.add_column("Run ID")
        table.add_column("Scenario")
        table.add_column("Target")
        table.add_column("Status")
        for run in data:
            table.add_row(
                run["id"][:12] + "…",
                run["scenario_id"],
                run["target_model"],
                run["status"],
            )
        console.print(table)


# ─── Report Commands ────────────────────────────────────────
@report_app.command("list")
def report_list():
    """List all generated reports."""
    data = _api_request("GET", "/reports/")
    table = Table(title="Reports", border_style="green")
    table.add_column("ID")
    table.add_column("Run ID")
    table.add_column("Format")
    table.add_column("Generated")
    for r in data:
        table.add_row(
            r["id"][:12] + "…", r["run_id"][:12] + "…", r["format"], r["generated_at"]
        )
    console.print(table)


@report_app.command("generate")
def report_generate(
    run_id: str = typer.Argument(..., help="Attack run ID"),
    format: str = typer.Option(
        "html", "--format", "-f", help="Report format(s): html,pdf,jsonl"
    ),
):
    """Generate report for an attack run."""
    formats = [f.strip() for f in format.split(",")]
    data = _api_request(
        "POST", "/reports/generate", json={"run_id": run_id, "formats": formats}
    )
    for report in data:
        console.print(
            f"[green]✓[/green] Generated {report['format']} report: {report['id'][:12]}…"
        )


@report_app.command("show")
def report_show(run_id: str = typer.Argument(..., help="Run ID")):
    """Show report for a run."""
    data = _api_request("GET", f"/attacks/runs/{run_id}")
    console.print(
        Panel(json.dumps(data, indent=2, default=str), title=f"Report: {run_id[:12]}…")
    )


# ─── Probe Commands ─────────────────────────────────────────
@probe_app.command("list")
def probe_list():
    """List all registered probes."""
    data = _api_request("GET", "/probes/")
    table = Table(title="Probes", border_style="magenta")
    table.add_column("Name", style="bold")
    table.add_column("Category")
    table.add_column("Description")
    for p in data:
        table.add_row(p["name"], p.get("category", ""), p.get("description", ""))
    console.print(table)


@probe_app.command("run")
def probe_run(
    probe_name: str = typer.Argument(...),
    target: str = typer.Option(..., "--target", "-t"),
):
    """Run a probe against a target model."""
    data = _api_request(
        "POST", "/probes/run", json={"probe_name": probe_name, "target_model": target}
    )
    console.print(f"[green]✓[/green] {data.get('message', 'Probe completed')}")


# ─── Playbook Commands ──────────────────────────────────────
@playbook_app.command("list")
def playbook_list():
    """List all IR playbooks."""
    data = _api_request("GET", "/playbooks/")
    table = Table(title="IR Playbooks", border_style="yellow")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Severity")
    table.add_column("Trigger")
    for p in data:
        table.add_row(p["id"], p["name"], p.get("severity", ""), p.get("trigger", ""))
    console.print(table)


@playbook_app.command("run")
def playbook_run(
    playbook_id: str = typer.Argument(...),
    context_file: str = typer.Option(None, "--context", "-c"),
):
    """Execute an IR playbook."""
    context = {}
    if context_file:
        context = json.loads(Path(context_file).read_text())
    data = _api_request(
        "POST",
        f"/playbooks/{playbook_id}/run",
        json={"playbook_id": playbook_id, "context": context},
    )
    console.print(
        f"[green]✓[/green] Playbook {playbook_id} executed: {data.get('steps_executed', 0)} steps"
    )


# ─── NEW: Agent Testing ─────────────────────────────────────
@agent_app.command("test")
def agent_test(
    endpoint: str = typer.Argument(..., help="Agent API endpoint"),
    tools_list: str = typer.Option("", "--tools", help="Comma-separated allowed tools"),
    forbidden: str = typer.Option(
        "", "--forbidden", help="Comma-separated forbidden actions"
    ),
    scenarios: str = typer.Option(
        "tool_misuse,hallucination,unauthorized_access",
        "--scenarios",
        help="Comma-separated test scenarios",
    ),
):
    """Test an AI agent for tool misuse and safety."""
    allowed = [t.strip() for t in tools_list.split(",") if t.strip()]
    forbidden_list = [f.strip() for f in forbidden.split(",") if f.strip()]
    scenario_list = [s.strip() for s in scenarios.split(",")]

    console.print(f"Testing agent at [cyan]{endpoint}[/cyan]...")
    data = _api_request(
        "POST",
        "/agent/test",
        json={
            "endpoint": endpoint,
            "allowed_tools": allowed,
            "forbidden_actions": forbidden_list,
            "test_scenarios": scenario_list,
        },
    )

    risk_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }
    risk_style = risk_colors.get(data.get("risk_level", "unknown"), "dim")
    console.print(
        Panel(
            f"Test ID: {data['id']}\n"
            f"Endpoint: {data['endpoint']}\n"
            f"Status: {data['status']}\n"
            f"Risk Level: [{risk_style}]{data.get('risk_level', 'unknown').upper()}[/{risk_style}]\n"
            f"Findings: {data.get('findings_count', 0)}\n\n"
            f"[bold]Scenario Results:[/bold]\n"
            + "\n".join(
                f"  {k}: {v.get('status', 'unknown')} "
                f"(findings: {len(v.get('findings', []))})"
                for k, v in data.get("results", {}).items()
                if isinstance(v, dict) and "status" in v
            ),
            title="Agent Safety Test",
            border_style=risk_style.split()[-1] if " " in risk_style else risk_style,
        )
    )


@agent_app.command("tests")
def agent_list_tests(
    endpoint: str = typer.Option(None, "--endpoint", help="Filter by endpoint"),
):
    """List previous agent tests."""
    params = {}
    if endpoint:
        params["endpoint"] = endpoint
    data = _api_request("GET", "/agent/tests", params=params)
    table = Table(title="Agent Tests", border_style="cyan")
    table.add_column("ID")
    table.add_column("Endpoint")
    table.add_column("Status")
    table.add_column("Risk")
    table.add_column("Findings")
    table.add_column("Created")
    for t in data:
        table.add_row(
            t["id"][:12] + "...",
            t["endpoint"][:30],
            t["status"],
            t["risk_level"],
            str(t["findings_count"]),
            t["created_at"][:10],
        )
    console.print(table)


@agent_app.command("show")
def agent_show(test_id: str = typer.Argument(..., help="Test ID")):
    """Get details of a specific agent test."""
    data = _api_request("GET", f"/agent/tests/{test_id}")
    risk_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }
    risk_style = risk_colors.get(data.get("risk_level", "unknown"), "dim")
    console.print(
        Panel(
            f"Test ID: {data['id']}\n"
            f"Endpoint: {data['endpoint']}\n"
            f"Status: {data['status']}\n"
            f"Risk Level: [{risk_style}]{data.get('risk_level', 'unknown').upper()}[/{risk_style}]\n"
            f"Findings: {data.get('findings_count', 0)}\n\n"
            f"[bold]Results:[/bold]\n"
            + json.dumps(data.get("results", {}), indent=2, default=str)[:500],
            title=f"Agent Test: {data['id'][:12]}...",
            border_style=risk_style.split()[-1] if " " in risk_style else risk_style,
        )
    )


# ─── NEW: Drift Detection ───────────────────────────────────
@drift_app.command("baseline")
def drift_baseline(
    model: str = typer.Argument(..., help="Model name"),
    test_suite: str = typer.Option("default", "--suite", help="Test suite name"),
    save: str = typer.Option("baseline.json", "--save", help="Output file"),
):
    """Create safety baseline for a model."""
    console.print(f"Creating baseline for [cyan]{model}[/cyan]...")
    data = _api_request(
        "POST",
        "/drift/baseline",
        json={
            "model": model,
            "test_suite": test_suite,
        },
    )
    console.print(
        Panel(
            f"Baseline ID: {data['id']}\n"
            f"Model: {data['model']}\n"
            f"Test Suite: {data['test_suite']}\n"
            f"Prompts: {data['prompt_count']}\n\n"
            f"[bold]Scores:[/bold]\n"
            + "\n".join(f"  {k}: {v:.4f}" for k, v in data.get("scores", {}).items()),
            title="Drift Baseline Created",
            border_style="green",
        )
    )
    # Save baseline ID for future comparisons
    Path(save).write_text(
        json.dumps({"baseline_id": data["id"], "model": model}, indent=2)
    )
    console.print(f"[dim]Baseline ID saved to {save}[/dim]")


@drift_app.command("compare")
def drift_compare(
    model: str = typer.Argument(..., help="Model name"),
    baseline: str = typer.Option(..., "--baseline", help="Baseline file or ID"),
):
    """Compare current model to baseline."""
    # Support both file path and raw ID
    baseline_id = baseline
    if Path(baseline).exists():
        baseline_data = json.loads(Path(baseline).read_text())
        baseline_id = baseline_data.get("baseline_id", baseline)

    console.print(f"Comparing [cyan]{model}[/cyan] to baseline {baseline_id[:12]}...")
    data = _api_request(
        "POST",
        "/drift/compare",
        json={
            "model": model,
            "baseline_id": baseline_id,
        },
    )

    drift_icon = (
        "[red]DRIFT DETECTED[/red]"
        if data["drift_detected"]
        else "[green]STABLE[/green]"
    )
    console.print(
        Panel(
            f"Status: {drift_icon}\n"
            f"Summary: {data['summary']}\n\n"
            f"[bold]Score Deltas:[/bold]\n"
            + "\n".join(
                f"  {k}: {v:+.2%}" + (" [red]!!![/red]" if abs(v) > 0.1 else "")
                for k, v in data.get("deltas", {}).items()
            ),
            title="Drift Comparison",
            border_style="red" if data["drift_detected"] else "green",
        )
    )


@drift_app.command("baselines")
def drift_list_baselines(
    model: str = typer.Option(None, "--model", help="Filter by model"),
):
    """List all drift baselines."""
    params = {}
    if model:
        params["model"] = model
    data = _api_request("GET", "/drift/baselines")
    table = Table(title="Drift Baselines", border_style="cyan")
    table.add_column("ID")
    table.add_column("Model")
    table.add_column("Suite")
    table.add_column("Created")
    for b in data:
        table.add_row(
            b["id"][:12] + "...", b["model"], b["test_suite"], b["created_at"][:10]
        )
    console.print(table)


# ─── NEW: Synthetic Data ────────────────────────────────────
@synthetic_app.command("generate")
def synthetic_generate(
    seed: str = typer.Option(
        None, "--seed", help="Seed prompts file (one prompt per line)"
    ),
    mutations: str = typer.Option(
        "encoding,translation,synonym", help="Mutation types"
    ),
    count: int = typer.Option(100, "--count", help="Number of prompts to generate"),
    output: str = typer.Option("synthetic_dataset.json", "--output", "-o"),
):
    """Generate synthetic adversarial prompts."""
    seed_prompts = []
    if seed and Path(seed).exists():
        seed_prompts = [
            line.strip() for line in Path(seed).read_text().splitlines() if line.strip()
        ]

    mutation_list = [m.strip() for m in mutations.split(",")]
    console.print(f"Generating {count} synthetic prompts...")
    console.print(f"Mutations: {', '.join(mutation_list)}")

    data = _api_request(
        "POST",
        "/synthetic/generate",
        json={
            "seed_prompts": seed_prompts,
            "mutations": mutation_list,
            "count": count,
        },
    )

    console.print(
        Panel(
            f"Dataset ID: {data['id']}\n"
            f"Status: {data['status']}\n"
            f"Generated: {data['total_generated']} prompts\n"
            f"Mutations: {', '.join(data.get('mutations_applied', []))}\n\n"
            f"[bold]Samples (first {len(data.get('samples', []))}):[/bold]\n"
            + "\n".join(
                f"  [{s.get('mutation_type', '?')}] {s.get('mutated_prompt', '')[:80]}..."
                for s in data.get("samples", [])[:5]
            ),
            title="Synthetic Dataset Generated",
            border_style="magenta",
        )
    )

    # Save full response to output file
    Path(output).write_text(json.dumps(data, indent=2, default=str))
    console.print(f"[dim]Dataset saved to {output}[/dim]")


@synthetic_app.command("datasets")
def synthetic_list():
    """List generated synthetic datasets."""
    data = _api_request("GET", "/synthetic/datasets")
    table = Table(title="Synthetic Datasets", border_style="magenta")
    table.add_column("ID")
    table.add_column("Seeds")
    table.add_column("Generated")
    table.add_column("Mutations")
    table.add_column("Status")
    table.add_column("Created")
    for d in data:
        table.add_row(
            d["id"][:12] + "...",
            str(d["seed_count"]),
            str(d["total_generated"]),
            ", ".join(d.get("mutations_applied", [])),
            d["status"],
            d["created_at"][:10],
        )
    console.print(table)


@synthetic_app.command("show")
def synthetic_show(dataset_id: str = typer.Argument(..., help="Dataset ID")):
    """Get details of a specific synthetic dataset."""
    data = _api_request("GET", f"/synthetic/datasets/{dataset_id}")
    console.print(
        Panel(
            f"Dataset ID: {data['id']}\n"
            f"Status: {data['status']}\n"
            f"Generated: {data['total_generated']} prompts\n"
            f"Mutations: {', '.join(data.get('mutations_applied', []))}\n\n"
            f"[bold]Samples:[/bold]\n"
            + "\n".join(
                f"  [{s.get('mutation_type', '?')}] {s.get('mutated_prompt', '')[:100]}"
                for s in data.get("samples", [])
            ),
            title=f"Synthetic Dataset: {data['id'][:12]}...",
            border_style="magenta",
        )
    )


# ─── NEW: Supply Chain ──────────────────────────────────────
@supply_chain_app.command("scan")
def supply_chain_scan(
    model_source: str = typer.Argument(
        ..., help="Model source (e.g. huggingface:gpt2)"
    ),
    checks: str = typer.Option(
        "dependencies,model_card,license,data_provenance",
        "--checks",
        help="Comma-separated checks to run",
    ),
):
    """Scan model supply chain for vulnerabilities."""
    check_list = [c.strip() for c in checks.split(",")]
    console.print(f"Scanning: [cyan]{model_source}[/cyan]...")
    console.print(f"Checks: {', '.join(check_list)}")
    data = _api_request(
        "POST",
        "/supply-chain/scan",
        json={
            "model_source": model_source,
            "checks": check_list,
        },
    )

    risk_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }
    risk_style = risk_colors.get(data["risk_level"], "dim")
    console.print(
        Panel(
            f"Scan ID: {data['id']}\n"
            f"Model: {data['model_source']}\n"
            f"Risk Level: [{risk_style}]{data['risk_level'].upper()}[/{risk_style}]\n"
            f"Issues Found: {data['issues_found']}\n\n"
            f"[bold]Results:[/bold]\n"
            + "\n".join(
                f"  {k}: {v.get('status', 'unknown')}"
                for k, v in data.get("results", {}).items()
            ),
            title="Supply Chain Scan",
            border_style=risk_style.split()[-1] if " " in risk_style else risk_style,
        )
    )


@supply_chain_app.command("scans")
def supply_chain_list():
    """List previous supply chain scans."""
    data = _api_request("GET", "/supply-chain/scans")
    table = Table(title="Supply Chain Scans", border_style="cyan")
    table.add_column("ID")
    table.add_column("Model")
    table.add_column("Issues")
    table.add_column("Risk")
    table.add_column("Created")
    for s in data:
        table.add_row(
            s["id"][:12] + "...",
            s["model_source"],
            str(s["issues_found"]),
            s["risk_level"],
            s["created_at"][:10],
        )
    console.print(table)


# ─── NEW: Backdoor Detection ──────────────────────────────
@backdoor_app.command("scan")
def backdoor_scan(
    model_source: str = typer.Argument(
        ..., help="Model source (e.g. huggingface:gpt2)"
    ),
    scan_type: str = typer.Option(
        "behavioral", "--type", help="Scan type: behavioral, pickle, weight"
    ),
):
    """Run a backdoor detection scan on a model."""
    console.print(f"Scanning: [cyan]{model_source}[/cyan] (type: {scan_type})...")
    data = _api_request(
        "POST",
        "/backdoor/scan",
        params={
            "model_source": model_source,
            "scan_type": scan_type,
        },
    )

    risk_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }
    risk_style = risk_colors.get(data["risk_level"], "dim")
    console.print(
        Panel(
            f"Scan ID: {data['id']}\n"
            f"Model: {data['model_source']}\n"
            f"Scan Type: {data['scan_type']}\n"
            f"Risk Level: [{risk_style}]{data['risk_level'].upper()}[/{risk_style}]\n"
            f"Indicators Found: {data['indicators_found']}\n\n"
            f"[bold]Results:[/bold]\n"
            + "\n".join(
                f"  {k}: {v}"
                for k, v in data.get("results", {}).items()
                if isinstance(v, str)
            ),
            title="Backdoor Scan",
            border_style=risk_style.split()[-1] if " " in risk_style else risk_style,
        )
    )


@backdoor_app.command("scans")
def backdoor_list(
    model: str = typer.Option(None, "--model", help="Filter by model source"),
):
    """List previous backdoor scans."""
    params = {}
    if model:
        params["model"] = model
    data = _api_request("GET", "/backdoor/scans", params=params)
    table = Table(title="Backdoor Scans", border_style="cyan")
    table.add_column("ID")
    table.add_column("Model")
    table.add_column("Type")
    table.add_column("Indicators")
    table.add_column("Risk")
    table.add_column("Created")
    for s in data:
        table.add_row(
            s["id"][:12] + "...",
            s["model_source"],
            s["scan_type"],
            str(s["indicators_found"]),
            s["risk_level"],
            s["created_at"][:10],
        )
    console.print(table)


@backdoor_app.command("show")
def backdoor_show(scan_id: str = typer.Argument(..., help="Scan ID")):
    """Get details of a specific backdoor scan."""
    data = _api_request("GET", f"/backdoor/scans/{scan_id}")
    risk_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }
    risk_style = risk_colors.get(data["risk_level"], "dim")
    console.print(
        Panel(
            f"Scan ID: {data['id']}\n"
            f"Model: {data['model_source']}\n"
            f"Scan Type: {data['scan_type']}\n"
            f"Risk Level: [{risk_style}]{data['risk_level'].upper()}[/{risk_style}]\n"
            f"Indicators Found: {data['indicators_found']}\n\n"
            f"[bold]Results:[/bold]\n" + json.dumps(data.get("results", {}), indent=2),
            title=f"Backdoor Scan: {data['id'][:12]}...",
            border_style=risk_style.split()[-1] if " " in risk_style else risk_style,
        )
    )


# ─── Webhook Commands ──────────────────────────────────────


@webhook_app.command("create")
def webhook_create(
    url: str = typer.Argument(..., help="Webhook endpoint URL"),
    events: str = typer.Option(
        "attack.completed",
        help="Comma-separated event types (attack.completed,scan.completed,report.generated,attack.failed,agent.test.completed)",
    ),
    description: str = typer.Option("", help="Webhook description"),
):
    """Register a new webhook endpoint."""
    event_list = [e.strip() for e in events.split(",") if e.strip()]
    payload = {"url": url, "events": event_list}
    if description:
        payload["description"] = description
    data = _api_request("POST", "/webhooks", json=payload)
    console.print(
        Panel(
            f"Webhook ID: {data['id']}\n"
            f"URL: {data['url']}\n"
            f"Events: {', '.join(data['events'])}\n"
            f"Secret: [bold yellow]{data['secret']}[/bold yellow]\n\n"
            f"[dim]Save the secret — it won't be shown again.[/dim]",
            title="✅ Webhook Created",
            border_style="green",
        )
    )


@webhook_app.command("list")
def webhook_list():
    """List registered webhooks."""
    data = _api_request("GET", "/webhooks")
    table = Table(title="Webhooks", border_style="cyan")
    table.add_column("ID")
    table.add_column("URL")
    table.add_column("Events")
    table.add_column("Active")
    table.add_column("Failures")
    table.add_column("Created")
    for w in data:
        active = "[green]✓[/green]" if w["is_active"] else "[red]✗[/red]"
        table.add_row(
            w["id"][:12] + "...",
            w["url"][:50] + ("..." if len(w["url"]) > 50 else ""),
            ", ".join(w["events"]),
            active,
            str(w["failure_count"]),
            w["created_at"][:10],
        )
    console.print(table)


@webhook_app.command("delete")
def webhook_delete(webhook_id: str = typer.Argument(..., help="Webhook ID")):
    """Delete a webhook endpoint."""
    _api_request("DELETE", f"/webhooks/{webhook_id}")
    console.print(f"[green]✅ Webhook {webhook_id[:12]}... deleted[/green]")


@webhook_app.command("test")
def webhook_test(webhook_id: str = typer.Argument(..., help="Webhook ID")):
    """Send a test ping to a webhook endpoint."""
    data = _api_request("POST", f"/webhooks/{webhook_id}/test")
    if data["status"] == "success":
        console.print(
            Panel(
                f"Webhook: {data['webhook_id'][:12]}...\n"
                f"Status: [green]{data['status']}[/green]\n"
                f"Response Code: {data.get('response_code', 'N/A')}",
                title="✅ Webhook Test",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"Webhook: {data['webhook_id'][:12]}...\n"
                f"Status: [red]{data['status']}[/red]\n"
                f"Error: {data.get('error', 'Unknown error')}",
                title="❌ Webhook Test Failed",
                border_style="red",
            )
        )


def main():
    app()


if __name__ == "__main__":
    main()
