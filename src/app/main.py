from __future__ import annotations

import typer
import uvicorn

from app.cli.main import cli as cli_app
from app.web.app import create_app


app = typer.Typer(help="Telegram Client Copier")
app.add_typer(cli_app, name="db")


@app.command()
def api(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the FastAPI server."""
    uvicorn.run(create_app(), host=host, port=port)


def run() -> None:
    app()

