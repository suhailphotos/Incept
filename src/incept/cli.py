# src/incept/cli.py

from incept.templates.manager import ensure_templates_from_package, TEMPLATE_DIR

def cli_init_templates():
    """
    CLI entry point. Ensure user-level templates
    are up to date with the package's built-in templates.
    """
    print("Initializing Incept templates...")
    ensure_templates_from_package()
    print(f"Templates ready in: {TEMPLATE_DIR}")
