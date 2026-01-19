#!/usr/bin/env python3
"""
Azure AI Foundry Agent Creation & Demo Toolkit

Main entry point for running the toolkit via CLI and TUI.

Usage:
    python main.py tui          # Launch Textual TUI
    python main.py generate     # Generate code from template
    python main.py list         # List available templates
"""

import argparse
import sys
from pathlib import Path

from src.core import config


def run_tui():
    """Launch the Textual TUI application."""
    from ui.terminal.app import run_tui as launch_tui
    launch_tui()


def list_templates():
    """List available industry templates."""
    from src.templates.template_loader import TemplateLoader

    loader = TemplateLoader()
    templates = loader.list_templates()

    print("\nAvailable Industry Templates:")
    print("=" * 50)

    for template_id in templates:
        try:
            info = loader.get_template_info(template_id)
            print(f"\n  {info['id']}")
            print(f"    Name: {info['name']}")
            print(f"    Agent Types: {info['agent_types']}")
            print(f"    Departments: {info['departments']}")
        except Exception as e:
            print(f"\n  {template_id}")
            print(f"    Error loading: {e}")

    print("\n" + "=" * 50)


def generate_code(args):
    """Generate simulation code from a template."""
    from src.templates.template_loader import TemplateLoader
    from src.codegen.generator import generate_code_for_profile

    loader = TemplateLoader()

    # Validate template
    templates = loader.list_templates()
    if args.template not in templates:
        print(f"Error: Template '{args.template}' not found.")
        print(f"Available templates: {', '.join(templates)}")
        sys.exit(1)

    print(f"\nGenerating code for template: {args.template}")
    print(f"Output directory: {args.output}")

    try:
        profile = loader.load_template(args.template)
        result = generate_code_for_profile(
            profile=profile,
            output_dir=args.output,
            agents_csv=args.agents_csv,
        )

        print("\nGenerated files:")
        for filename, filepath in result.items():
            print(f"  - {filepath}")

        print(f"\nCode generation complete!")

    except Exception as e:
        print(f"Error generating code: {e}")
        sys.exit(1)


def create_agents(args):
    """Create agents from a template."""
    from src.templates.template_loader import TemplateLoader
    from src.core.agent_manager import AgentManager

    loader = TemplateLoader()

    # Validate template
    templates = loader.list_templates()
    if args.template not in templates:
        print(f"Error: Template '{args.template}' not found.")
        sys.exit(1)

    profile = loader.load_template(args.template)

    print(f"\nCreating agents for template: {args.template}")
    print(f"  Organizations: {args.orgs}")
    print(f"  Agents per type: {args.count}")
    print(f"  Total agent types: {len(profile.agent_types)}")

    total = args.orgs * args.count * len(profile.agent_types)
    print(f"  Total agents to create: {total}")

    if not args.yes:
        response = input("\nProceed? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    def progress_callback(current, total_count, message):
        print(f"  [{current}/{total_count}] {message}")

    try:
        manager = AgentManager(models=profile.models.allowed)
        result = manager.create_agents_from_profile(
            profile=profile,
            agent_count=args.count,
            org_count=args.orgs,
            progress_callback=progress_callback,
        )

        manager.save_agents_to_csv(result.created, args.output)

        print(f"\nCreated {len(result.created)} agents successfully")
        if result.failed:
            print(f"Failed: {len(result.failed)}")

        print(f"Results saved to: {args.output}")

    except Exception as e:
        print(f"Error creating agents: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Azure AI Foundry Agent Creation & Demo Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py tui                    # Launch terminal UI
  python main.py list                   # List available templates
  python main.py generate retail        # Generate code for retail template
  python main.py create retail -n 2     # Create 2 agents per type
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # TUI command
    tui_parser = subparsers.add_parser("tui", help="Launch Textual TUI")

    # List command
    list_parser = subparsers.add_parser("list", help="List available templates")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate simulation code")
    gen_parser.add_argument("template", help="Template ID (e.g., retail, healthcare)")
    gen_parser.add_argument("-o", "--output", default=str(config.GENERATED_CODE_DIR), help="Output directory")
    gen_parser.add_argument("--agents-csv", default=str(config.CREATED_AGENTS_CSV), help="Agents CSV path")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create agents from template")
    create_parser.add_argument("template", help="Template ID")
    create_parser.add_argument("-n", "--count", type=int, default=1, help="Agents per type")
    create_parser.add_argument("--orgs", type=int, default=1, help="Number of organizations")
    create_parser.add_argument("-o", "--output", default=str(config.CREATED_AGENTS_CSV), help="Output CSV")
    create_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    if args.command == "tui":
        run_tui()
    elif args.command == "list":
        list_templates()
    elif args.command == "generate":
        generate_code(args)
    elif args.command == "create":
        create_agents(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
