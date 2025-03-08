# src/incept/templates.py

import json
import jinja2
from jinja2 import Environment, meta, nodes
from pathlib import Path
from typing import Optional, Any


class TemplateManager:
    """
    Encapsulates all interactions with Jinja2 templates: 
      - Locating a template
      - Reading template variables (e.g., child_folder_name, use_numeric_prefix)
      - Checking if a template references a given variable
    """

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.lookup_file = self.templates_dir / "templates.json"
        if not self.lookup_file.exists():
            raise FileNotFoundError(f"Missing templates.json at {self.lookup_file}")

        with self.lookup_file.open("r", encoding="utf-8") as f:
            self.template_map = json.load(f)

    def get_template_path(self, template_type: str, variant: str) -> Path:
        """
        Retrieve the actual .j2 file path for a given template_type and variant,
        using templates.json as a lookup.
        """
        try:
            j2_filename = self.template_map[template_type][variant]
        except KeyError:
            raise ValueError(f"No template found for type={template_type}, variant={variant}")

        template_path = self.templates_dir / j2_filename
        if not template_path.exists():
            raise FileNotFoundError(f"Template file {template_path} not found.")

        return template_path

    def get_child_template_folder_from_parent(self, template_type: str, variant: str) -> Optional[str]:
        """
        Examines the specified template, looking for:
            {% set child_folder_name = "some_folder" %}
        Returns the string value if found, or None.
        """
        template_path = self.get_template_path(template_type, variant)
        source = template_path.read_text(encoding="utf-8")
        env = Environment()
        parsed_content = env.parse(source)

        for node in parsed_content.find_all(nodes.Assign):
            if (isinstance(node.target, nodes.Name) and 
                node.target.name == "child_folder_name" and 
                isinstance(node.node, nodes.Const)):
                return node.node.value

        return None

    def template_references_variable(self, template_type: str, variant: str, variable_name: str) -> bool:
        """
        Returns True if the template references the given variable_name, else False.
        """
        template_path = self.get_template_path(template_type, variant)
        if not template_path.exists():
            return False

        source = template_path.read_text(encoding="utf-8")
        env = Environment()
        parsed_content = env.parse(source)
        referenced = meta.find_undeclared_variables(parsed_content)
        return (variable_name in referenced)

    def get_variable_value(self, template_type: str, variant: str, variable_name: str) -> Optional[Any]:
        """
        Looks for a Jinja2 assignment in the template of the form:
            {% set <variable_name> = <constant> %}
        Returns the value if found, otherwise None.
        """
        template_path = self.get_template_path(template_type, variant)
        if not template_path.exists():
            return None

        source = template_path.read_text(encoding="utf-8")
        env = Environment()
        parsed_content = env.parse(source)

        for node in parsed_content.find_all(nodes.Assign):
            if isinstance(node.target, nodes.Name) and node.target.name == variable_name:
                if isinstance(node.node, nodes.Const):
                    return node.node.value

        return None
