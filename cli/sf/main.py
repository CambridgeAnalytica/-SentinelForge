"""
SentinelForge CLI
Enterprise AI Security Testing Command-Line Interface
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

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
app.add_typer(playbook_app, name="playbook")


# ─── Configuration ──────────────────────────────────────────
import json
from pathlib import Path

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
        console.print("[dim]Make sure SentinelForge services are running: docker compose up -d[/dim]")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ API error: {e.response.status_code} - {e.response.text}[/red]")
        raise typer.Exit(1)


# ─── Version ────────────────────────────────────────────────
@app.command()
def version():
    """Show SentinelForge version."""
    console.print(Panel(
        "[bold cyan]SentinelForge CLI v1.0.0[/bold cyan]\n"
        "Enterprise AI Security Testing Platform\n"
        "[dim]https://github.com/sentinelforge[/dim]",
        title="🛡️ SentinelForge",
        border_style="cyan",
    ))


# ─── Auth Commands ──────────────────────────────────────────
@auth_app.command("login")
def auth_login(
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
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
            _save_config({
                "api_url": api_url,
                "token": data["access_token"],
                "username": username,
            })
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
    console.print(f"[green]✓ Authenticated[/green]")
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
            tool["description"][:50] + "…" if len(tool["description"]) > 50 else tool["description"],
        )

    console.print(table)


@tools_app.command("info")
def tools_info(tool_name: str = typer.Argument(..., help="Tool name")):
    """Get detailed info about a specific tool."""
    data = _api_request("GET", f"/tools/{tool_name}")

    console.print(Panel(
        f"[bold]{data['name']}[/bold] v{data['version']}\n"
        f"Category: {data['category']}\n"
        f"Description: {data['description']}\n\n"
        f"[bold]Capabilities:[/bold]\n" +
        "\n".join(f"  • {c}" for c in data.get('capabilities', [])) + "\n\n"
        f"[bold]MITRE ATLAS:[/bold]\n" +
        "\n".join(f"  • {m}" for m in data.get('mitre_atlas', [])),
        title=f"🔧 Tool: {data['name']}",
        border_style="cyan",
    ))


@tools_app.command("run")
def tools_run(
    tool_name: str = typer.Argument(..., help="Tool name"),
    target: str = typer.Argument(..., help="Target model or endpoint"),
    timeout: int = typer.Option(600, help="Timeout in seconds"),
):
    """Execute a tool against a target."""
    console.print(f"Running [bold]{tool_name}[/bold] against [cyan]{target}[/cyan]...")
    data = _api_request("POST", f"/tools/{tool_name}/run", json={
        "target": target,
        "timeout": timeout,
    })
    console.print(f"Status: {data['status']}")
    if data.get('output'):
        console.print(Panel(data['output'], title="Output"))


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
    console.print(f"Launching attack: [bold red]{scenario}[/bold red] → [cyan]{target}[/cyan]")
    data = _api_request("POST", "/attacks/run", json={
        "scenario_id": scenario,
        "target_model": target,
    })

    console.print(Panel(
        f"Run ID: {data['id']}\n"
        f"Status: {data['status']}\n"
        f"Created: {data['created_at']}\n\n"
        f"Track progress: [dim]sf attack runs {data['id']}[/dim]",
        title="⚔️ Attack Launched",
        border_style="red",
    ))


@attack_app.command("runs")
def attack_runs(run_id: str = typer.Argument(None, help="Specific run ID")):
    """List all runs or get status of specific run."""
    if run_id:
        data = _api_request("GET", f"/attacks/runs/{run_id}")
        console.print(Panel(
            f"Scenario: {data['scenario_id']}\n"
            f"Target: {data['target_model']}\n"
            f"Status: {data['status']}\n"
            f"Progress: {data['progress']}%\n"
            f"Findings: {len(data.get('findings', []))}",
            title=f"Run: {data['id'][:12]}…",
            border_style="cyan",
        ))

        if data.get('findings'):
            table = Table(title="Findings")
            table.add_column("Severity", style="bold")
            table.add_column("Tool")
            table.add_column("Title")
            for f in data['findings']:
                sev_color = {"critical": "red", "high": "yellow", "medium": "bright_yellow", "low": "blue"}.get(f['severity'], "dim")
                table.add_row(f"[{sev_color}]{f['severity'].upper()}[/{sev_color}]", f['tool_name'], f['title'])
            console.print(table)
    else:
        data = _api_request("GET", "/attacks/runs")
        table = Table(title="Recent Attack Runs", border_style="cyan")
        table.add_column("Run ID")
        table.add_column("Scenario")
        table.add_column("Target")
        table.add_column("Status")
        for run in data:
            table.add_row(run['id'][:12] + "…", run['scenario_id'], run['target_model'], run['status'])
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
        table.add_row(r['id'][:12] + "…", r['run_id'][:12] + "…", r['format'], r['generated_at'])
    console.print(table)


@report_app.command("generate")
def report_generate(
    run_id: str = typer.Argument(..., help="Attack run ID"),
    format: str = typer.Option("html", "--format", "-f", help="Report format(s): html,pdf,jsonl"),
):
    """Generate report for an attack run."""
    formats = [f.strip() for f in format.split(",")]
    data = _api_request("POST", "/reports/generate", json={"run_id": run_id, "formats": formats})
    for report in data:
        console.print(f"[green]✓[/green] Generated {report['format']} report: {report['id'][:12]}…")


@report_app.command("show")
def report_show(run_id: str = typer.Argument(..., help="Run ID")):
    """Show report for a run."""
    data = _api_request("GET", f"/attacks/runs/{run_id}")
    console.print(Panel(json.dumps(data, indent=2, default=str), title=f"Report: {run_id[:12]}…"))


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
        table.add_row(p['name'], p.get('category', ''), p.get('description', ''))
    console.print(table)


@probe_app.command("run")
def probe_run(
    probe_name: str = typer.Argument(...),
    target: str = typer.Option(..., "--target", "-t"),
):
    """Run a probe against a target model."""
    data = _api_request("POST", "/probes/run", json={"probe_name": probe_name, "target_model": target})
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
        table.add_row(p['id'], p['name'], p.get('severity', ''), p.get('trigger', ''))
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
    data = _api_request("POST", f"/playbooks/{playbook_id}/run", json={"playbook_id": playbook_id, "context": context})
    console.print(f"[green]✓[/green] Playbook {playbook_id} executed: {data.get('steps_executed', 0)} steps")


# ─── NEW: Agent Testing ─────────────────────────────────────
@agent_app.command("test")
def agent_test(
    endpoint: str = typer.Argument(..., help="Agent API endpoint"),
    tools_list: str = typer.Option("", "--tools", help="Comma-separated allowed tools"),
    forbidden: str = typer.Option("", "--forbidden", help="Comma-separated forbidden actions"),
):
    """Test an AI agent for tool misuse and safety."""
    console.print(Panel(
        f"Testing: [cyan]{endpoint}[/cyan]\n"
        f"Allowed tools: {tools_list or 'all'}\n"
        f"Forbidden: {forbidden or 'none'}\n\n"
        "[yellow]🔬 AI Agent Testing Framework[/yellow]\n"
        "Tests: tool misuse, hallucination, unauthorized access",
        title="🤖 Agent Tester",
        border_style="cyan",
    ))
    # Stub - will call API when module is fully implemented
    console.print("[dim]Agent testing module active. Deploy with full stack for execution.[/dim]")


# ─── NEW: Drift Detection ───────────────────────────────────
@drift_app.command("baseline")
def drift_baseline(
    model: str = typer.Argument(..., help="Model name"),
    save: str = typer.Option("baseline.json", "--save", help="Output file"),
):
    """Create safety baseline for a model."""
    console.print(f"Creating baseline for [cyan]{model}[/cyan]...")
    console.print("[dim]Drift detection module active. Deploy with full stack for execution.[/dim]")


@drift_app.command("compare")
def drift_compare(
    model: str = typer.Argument(..., help="Model name"),
    baseline: str = typer.Option(..., "--baseline", help="Baseline file"),
):
    """Compare current model to baseline."""
    console.print(f"Comparing [cyan]{model}[/cyan] to baseline...")
    console.print("[dim]Drift detection module active. Deploy with full stack for execution.[/dim]")


# ─── NEW: Synthetic Data ────────────────────────────────────
@synthetic_app.command("generate")
def synthetic_generate(
    seed: str = typer.Option(None, "--seed", help="Seed prompts file"),
    mutations: str = typer.Option("encoding,translation,synonym", help="Mutation types"),
    count: int = typer.Option(100, "--count", help="Number of prompts to generate"),
    output: str = typer.Option("synthetic_dataset.json", "--output", "-o"),
):
    """Generate synthetic adversarial prompts."""
    console.print(f"Generating {count} synthetic prompts...")
    console.print(f"Mutations: {mutations}")
    console.print("[dim]Synthetic data module active. Deploy with full stack for execution.[/dim]")


# ─── NEW: Supply Chain ──────────────────────────────────────
@supply_chain_app.command("scan")
def supply_chain_scan(
    model_source: str = typer.Argument(..., help="Model source (e.g. huggingface:gpt2)"),
):
    """Scan model supply chain for vulnerabilities."""
    console.print(f"Scanning: [cyan]{model_source}[/cyan]...")
    console.print("[dim]Supply chain scanner active. Deploy with full stack for execution.[/dim]")


def main():
    app()


if __name__ == "__main__":
    main()
