#!/usr/bin/env python3
"""
Claude ACE - One-Click Installation Script
Installs Agentic Context Engineering system into any Claude Code project
"""
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime


class ACEInstaller:
    """Installer for Claude ACE system"""

    def __init__(self, project_dir: Path, force: bool = False, skip_hooks: bool = False):
        self.project_dir = project_dir.resolve()
        self.force = force
        self.skip_hooks = skip_hooks
        self.ace_core = Path(__file__).parent / "ace_core"
        self.claude_dir = self.project_dir / ".claude"

        self.stats = {
            'created_files': [],
            'updated_files': [],
            'skipped_files': [],
            'errors': []
        }

    def validate_environment(self):
        """Validate that installation is possible"""
        print("🔍 Validating environment...")

        if not self.project_dir.exists():
            raise ValueError(f"Project directory does not exist: {self.project_dir}")

        if not self.ace_core.exists():
            raise ValueError(f"ACE core files not found at: {self.ace_core}")

        print(f"   ✓ Project directory: {self.project_dir}")
        print(f"   ✓ ACE core found: {self.ace_core}")

    def create_directory_structure(self):
        """Create .claude directory structure"""
        print("\n📁 Creating directory structure...")

        dirs = [
            self.claude_dir,
            self.claude_dir / "hooks",
            self.claude_dir / "prompts",
            self.claude_dir / "scripts",
            self.claude_dir / "diagnostic"
        ]

        for dir_path in dirs:
            if dir_path.exists():
                print(f"   ○ Already exists: {dir_path.relative_to(self.project_dir)}")
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"   ✓ Created: {dir_path.relative_to(self.project_dir)}")
                self.stats['created_files'].append(str(dir_path.relative_to(self.project_dir)))

    def copy_hooks(self):
        """Copy hook scripts to project"""
        print("\n🪝 Installing hooks...")

        hooks_src = self.ace_core / "hooks"
        hooks_dst = self.claude_dir / "hooks"

        hook_files = [
            "common.py",
            "delta_manager.py",
            "user_prompt_inject.py",
            "pre_tool_use.py",
            "post_tool_use.py",
            "precompact.py",
            "session_end.py"
        ]

        for filename in hook_files:
            src = hooks_src / filename
            dst = hooks_dst / filename

            if dst.exists() and not self.force:
                print(f"   ○ Skipped (exists): {filename}")
                self.stats['skipped_files'].append(filename)
            else:
                shutil.copy2(src, dst)
                # Make executable
                dst.chmod(0o755)
                action = "Updated" if dst.exists() else "Created"
                print(f"   ✓ {action}: {filename}")
                self.stats['created_files'].append(filename)

    def copy_prompts(self):
        """Copy prompt templates to project"""
        print("\n📝 Installing prompt templates...")

        prompts_src = self.ace_core / "prompts"
        prompts_dst = self.claude_dir / "prompts"

        prompt_files = ["reflection.txt", "playbook.txt"]

        for filename in prompt_files:
            src = prompts_src / filename
            dst = prompts_dst / filename

            if dst.exists() and not self.force:
                print(f"   ○ Skipped (exists): {filename}")
                self.stats['skipped_files'].append(filename)
            else:
                shutil.copy2(src, dst)
                action = "Updated" if dst.exists() else "Created"
                print(f"   ✓ {action}: {filename}")
                self.stats['created_files'].append(filename)

    def copy_roles(self):
        """Copy ACE role modules to project"""
        print("\n🎭 Installing ACE roles...")

        roles_src = self.ace_core / "roles"
        roles_dst = self.claude_dir / "hooks"  # Place in hooks for easy import

        role_files = [
            "reflector.py",
            "curator.py",
            "feedback_environment.py"
        ]

        for filename in role_files:
            src = roles_src / filename
            dst = roles_dst / filename

            if dst.exists() and not self.force:
                print(f"   ○ Skipped (exists): {filename}")
                self.stats['skipped_files'].append(filename)
            else:
                shutil.copy2(src, dst)
                action = "Updated" if dst.exists() else "Created"
                print(f"   ✓ {action}: {filename}")
                self.stats['created_files'].append(filename)

    def copy_scripts(self):
        """Copy management scripts to project"""
        print("\n🛠️  Installing management scripts...")

        scripts_src = self.ace_core / "scripts"
        scripts_dst = self.claude_dir / "scripts"

        script_files = [
            "view_playbook.py",
            "cleanup_playbook.py",
            "analyze_diagnostics.py",
            "view_history.py"
        ]

        for filename in script_files:
            src = scripts_src / filename
            dst = scripts_dst / filename

            if dst.exists() and not self.force:
                print(f"   ○ Skipped (exists): {filename}")
                self.stats['skipped_files'].append(filename)
            else:
                shutil.copy2(src, dst)
                # Make executable
                dst.chmod(0o755)
                action = "Updated" if dst.exists() else "Created"
                print(f"   ✓ {action}: {filename}")
                self.stats['created_files'].append(filename)

        # Copy setup_vector_search.py to scripts directory
        # Always update this file as it's frequently updated with critical fixes
        setup_src = Path(__file__).parent / "setup_vector_search.py"
        setup_dst = scripts_dst / "setup_vector_search.py"

        if setup_src.exists():
            # Always overwrite setup_vector_search.py (it's frequently updated)
            shutil.copy2(setup_src, setup_dst)
            setup_dst.chmod(0o755)
            action = "Updated" if setup_dst.exists() else "Created"
            print(f"   ✓ {action}: setup_vector_search.py (always updated)")
            self.stats['created_files'].append('setup_vector_search.py')

        # Copy diagnose_vector_index.py to scripts directory
        diagnose_src = Path(__file__).parent / "diagnose_vector_index.py"
        diagnose_dst = scripts_dst / "diagnose_vector_index.py"

        if diagnose_src.exists():
            # Always overwrite diagnostic tool
            shutil.copy2(diagnose_src, diagnose_dst)
            diagnose_dst.chmod(0o755)
            action = "Updated" if diagnose_dst.exists() else "Created"
            print(f"   ✓ {action}: diagnose_vector_index.py (always updated)")
            self.stats['created_files'].append('diagnose_vector_index.py')

    def copy_storage(self):
        """Copy storage modules to project"""
        print("\n💾 Installing storage modules (production vector search)...")

        storage_src = self.ace_core / "storage"
        # Create storage subdirectory to maintain package structure
        storage_dst = self.claude_dir / "hooks" / "storage"
        storage_dst.mkdir(parents=True, exist_ok=True)

        storage_files = [
            "__init__.py",
            "vector_store.py",
            "ollama_embedding.py",
            "qdrant_store.py"
        ]

        for filename in storage_files:
            src = storage_src / filename
            dst = storage_dst / filename

            # Always overwrite storage modules (they contain critical async fixes)
            shutil.copy2(src, dst)
            action = "Updated" if dst.exists() else "Created"
            print(f"   ✓ {action}: storage/{filename} (always updated)")
            self.stats['created_files'].append(f"storage/{filename}")

    def setup_settings(self):
        """Create or merge settings.json with hooks configuration"""
        print("\n⚙️  Configuring hooks...")

        settings_path = self.claude_dir / "settings.json"
        template_path = self.ace_core / "templates" / "settings.json"

        with open(template_path, 'r', encoding='utf-8') as f:
            ace_settings = json.load(f)

        if settings_path.exists() and not self.skip_hooks:
            # Merge with existing settings
            print(f"   ℹ  Existing settings.json found")

            if not self.force:
                # Check if running in non-interactive mode (piped from curl)
                if not sys.stdin.isatty():
                    print("   ℹ  Non-interactive mode detected: auto-approving merge")
                    print("   💡 Use --force flag or FORCE=true to skip this message")
                    response = 'y'
                else:
                    response = input("   Merge ACE hooks into existing settings? (y/n): ")
                    if response.lower() != 'y':
                        print("   ○ Skipped settings.json update")
                        self.stats['skipped_files'].append('settings.json')
                        return

            with open(settings_path, 'r', encoding='utf-8') as f:
                existing_settings = json.load(f)

            # Backup original
            backup_path = self.claude_dir / f"settings.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, indent=2, ensure_ascii=False)
            print(f"   ✓ Backed up to: {backup_path.name}")

            # Merge hooks
            if 'hooks' not in existing_settings:
                existing_settings['hooks'] = {}

            for hook_name, hook_config in ace_settings['hooks'].items():
                existing_settings['hooks'][hook_name] = hook_config

            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, indent=2, ensure_ascii=False)

            print(f"   ✓ Merged ACE hooks into settings.json")
            self.stats['updated_files'].append('settings.json')

        elif not self.skip_hooks:
            # Create new settings.json
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(ace_settings, f, indent=2, ensure_ascii=False)
            print(f"   ✓ Created settings.json")
            self.stats['created_files'].append('settings.json')
        else:
            print(f"   ○ Skipped settings.json (--skip-hooks)")

    def setup_playbook(self):
        """Initialize playbook.json"""
        print("\n📚 Initializing playbook...")

        playbook_path = self.claude_dir / "playbook.json"

        if playbook_path.exists():
            print(f"   ○ Playbook already exists: {playbook_path.name}")
            print(f"   ○ Keeping existing playbook data")
            self.stats['skipped_files'].append('playbook.json')
        else:
            template_path = self.ace_core / "templates" / "playbook.json"
            shutil.copy2(template_path, playbook_path)
            print(f"   ✓ Created playbook.json")
            self.stats['created_files'].append('playbook.json')

    def setup_config(self):
        """Create ACE configuration file"""
        print("\n🔧 Setting up configuration...")

        config_path = self.claude_dir / "ace_config.json"

        if config_path.exists() and not self.force:
            print(f"   ○ Config already exists: {config_path.name}")
            self.stats['skipped_files'].append('ace_config.json')
        else:
            template_path = self.ace_core / "templates" / "ace_config.json"
            shutil.copy2(template_path, config_path)
            action = "Updated" if config_path.exists() else "Created"
            print(f"   ✓ {action}: ace_config.json")
            self.stats['created_files'].append('ace_config.json')

    def print_summary(self):
        """Print installation summary"""
        print("\n" + "═" * 80)
        print("✅ INSTALLATION COMPLETE!")
        print("═" * 80)

        print(f"\n📊 Summary:")
        print(f"   Created:  {len(self.stats['created_files'])} files/directories")
        print(f"   Updated:  {len(self.stats['updated_files'])} files")
        print(f"   Skipped:  {len(self.stats['skipped_files'])} files")

        if self.stats['errors']:
            print(f"   ⚠ Errors:  {len(self.stats['errors'])}")

    def print_next_steps(self):
        """Print next steps and usage information"""
        print("\n📖 Next Steps:")

        print("\n1. Install required dependencies:")
        print("   pip install aiohttp qdrant-client")
        print("   (Required for production vector search)")
        print("\n   Optional fallback:")
        print("   pip install chromadb")
        print("   (Development fallback if Qdrant unavailable)")

        print("\n2. Set up production vector search (OPTIONAL):")
        print("   a. Start Qdrant (if not running):")
        print("      docker run -d -p 6333:6333 qdrant/qdrant")
        print("\n   b. Start Ollama (if not running):")
        print("      ollama serve")
        print("\n   c. Pull embedding model:")
        print("      ollama pull qwen3-embedding:0.6b")
        print("\n   d. Run setup script:")
        print(f"      python {(self.claude_dir / 'scripts' / 'setup_vector_search.py').relative_to(self.project_dir)}")

        print("\n3. Start using Claude Code! 🎉")
        print("   The ACE system is ready to use (vector search is optional)")
        print("   cd to your project and start a Claude Code session")
        print("   The system will automatically:")
        print("   • Inject learned knowledge at session start")
        print("   • Extract learnings during context compaction")
        print("   • Reflect and update knowledge at session end")

        print("\n4. Manage your playbook:")
        print(f"   python {(self.claude_dir / 'scripts' / 'view_playbook.py').relative_to(self.project_dir)}")
        print(f"   python {(self.claude_dir / 'scripts' / 'cleanup_playbook.py').relative_to(self.project_dir)}")
        print(f"   python {(self.claude_dir / 'scripts' / 'analyze_diagnostics.py').relative_to(self.project_dir)}")

        print("\n5. Enable diagnostic mode (optional, for debugging):")
        print(f"   touch {(self.claude_dir / 'diagnostic_mode').relative_to(self.project_dir)}")

        print("\n💡 Tips:")
        print("   • The playbook starts empty and learns from your interactions")
        print("   • Key points are automatically scored and pruned")
        print("   • Vector search uses Qdrant + Ollama (production) or ChromaDB (fallback)")
        print("   • Check .claude/diagnostic/ for detailed reflection logs (if enabled)")

        print("\n📚 Documentation:")
        print("   • README: ./docs/README.md")
        print("   • Usage Guide: ./docs/USAGE.md")
        print("   • Phase 3 Improvements: ./PHASE3_IMPROVEMENTS.md")

        print("\n" + "═" * 80)

    def install(self):
        """Run complete installation process"""
        try:
            print("═" * 80)
            print("🚀 CLAUDE ACE INSTALLER")
            print("═" * 80)
            print("Installing Agentic Context Engineering into your Claude Code project")
            print(f"Target: {self.project_dir}")
            print("─" * 80)

            self.validate_environment()
            self.create_directory_structure()
            self.copy_hooks()
            self.copy_roles()
            self.copy_storage()
            self.copy_prompts()
            self.copy_scripts()
            self.setup_settings()
            self.setup_playbook()
            self.setup_config()
            self.print_summary()
            self.print_next_steps()

            return True

        except Exception as e:
            print(f"\n❌ Installation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point for installer"""
    parser = argparse.ArgumentParser(
        description="Install Claude ACE (Agentic Context Engineering) into a Claude Code project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install in current directory
  python install.py

  # Install in specific project
  python install.py --project /path/to/my-project

  # Force overwrite existing files
  python install.py --force

  # Install without modifying settings.json
  python install.py --skip-hooks
        """
    )

    parser.add_argument(
        '--project',
        type=Path,
        default=Path.cwd(),
        help='Project directory (default: current directory)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files'
    )

    parser.add_argument(
        '--skip-hooks',
        action='store_true',
        help='Skip settings.json hook configuration'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='Claude ACE Installer v1.0.0'
    )

    args = parser.parse_args()

    # Run installation
    installer = ACEInstaller(
        project_dir=args.project,
        force=args.force,
        skip_hooks=args.skip_hooks
    )

    success = installer.install()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
