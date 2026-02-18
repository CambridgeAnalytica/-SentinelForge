#!/usr/bin/env python3
"""
SentinelForge — OpenAPI Documentation Export

Generates the OpenAPI JSON schema from the FastAPI application and optionally
converts it to Redoc HTML for a self-contained, publishable API reference.

Usage:
    # Export openapi.json only
    python scripts/export_openapi.py

    # Export openapi.json + Redoc HTML
    python scripts/export_openapi.py --html

    # Custom output directory
    python scripts/export_openapi.py --output docs/api

    # Fetch from running server (instead of importing the app)
    python scripts/export_openapi.py --url http://localhost:8000
"""

import argparse
import json
import os
import sys
from pathlib import Path


def get_schema_from_app() -> dict:
    """Import the FastAPI app and extract the OpenAPI schema."""
    # Add service path so we can import the app
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "services" / "api"))

    from main import app  # noqa: E402

    schema = app.openapi()
    return schema


def get_schema_from_url(url: str) -> dict:
    """Fetch the OpenAPI schema from a running server."""
    import urllib.request

    endpoint = url.rstrip("/") + "/openapi.json"
    with urllib.request.urlopen(endpoint, timeout=10) as resp:
        return json.loads(resp.read().decode())


def generate_redoc_html(schema: dict) -> str:
    """Generate a self-contained Redoc HTML page from the schema."""
    schema_json = json.dumps(schema, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{schema.get("info", {}).get("title", "SentinelForge")} — API Reference</title>
  <style>body {{ margin: 0; padding: 0; }}</style>
</head>
<body>
  <div id="redoc-container"></div>
  <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
  <script>
    const spec = {schema_json};
    Redoc.init(spec, {{
      theme: {{
        colors: {{ primary: {{ main: '#6366f1' }} }},
        typography: {{ fontFamily: 'Inter, system-ui, sans-serif' }},
      }},
      hideDownloadButton: false,
      expandResponses: '200,201',
    }}, document.getElementById('redoc-container'));
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(
        description="Export SentinelForge OpenAPI documentation"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="docs/api",
        help="Output directory (default: docs/api)",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Also generate Redoc HTML reference",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Fetch schema from running server URL instead of importing app",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get schema
    print("📄 Fetching OpenAPI schema...")
    if args.url:
        schema = get_schema_from_url(args.url)
    else:
        schema = get_schema_from_app()

    # Write openapi.json
    json_path = output_dir / "openapi.json"
    json_path.write_text(json.dumps(schema, indent=2))
    print(f"✅ Wrote {json_path} ({json_path.stat().st_size:,} bytes)")

    # Optionally write Redoc HTML
    if args.html:
        html_path = output_dir / "index.html"
        html_content = generate_redoc_html(schema)
        html_path.write_text(html_content)
        print(f"✅ Wrote {html_path} ({html_path.stat().st_size:,} bytes)")

    # Summary
    info = schema.get("info", {})
    paths = schema.get("paths", {})
    endpoints = sum(len(v) for v in paths.values())
    print(f"\n📊 {info.get('title', 'API')} v{info.get('version', '?')}")
    print(f"   {len(paths)} paths, {endpoints} endpoints")


if __name__ == "__main__":
    main()
