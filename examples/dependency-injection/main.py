from typer_builder import build_app_from_module

app = build_app_from_module("commands", "myapp")
app()
