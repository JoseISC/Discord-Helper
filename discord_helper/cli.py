import typer

app = typer.Typer(help="Discord Helper CLI")


@app.command()
def setup():
    """Interactive setup wizard."""
    typer.echo("Setup wizard placeholder")


@app.command()
def doctor():
    """Validate local environment."""
    typer.echo("Doctor placeholder")


@app.command()
def run():
    """Run Discord Helper bot."""
    typer.echo("Run placeholder")


@app.command(name="install-service")
def install_service():
    """Install local background service."""
    typer.echo("Install service placeholder")


@app.command()
def logs():
    """Show application logs."""
    typer.echo("Logs placeholder")


if __name__ == "__main__":
    app()
