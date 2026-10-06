#!/usr/bin/env python3
"""
VoiceDesk Marketplace Package Builder

Creates a CodeCanyon-compliant submission ZIP with the required structure:
  item-name-v1.0.0.zip
  ├── Documentation/
  │   ├── VoiceDesk_User_Guide.pdf
  │   ├── VoiceDesk_Admin_Guide.pdf
  │   └── credits.txt
  ├── Source/
  │   ├── voice-engine/ (full unencrypted source)
  │   └── admin/ (admin dashboard source)
  ├── Database/
  │   └── schema.sql
  └── Preview/
      ├── cover.jpg (3:2 @ 2340x1560)
      ├── preview1.jpg
      ├── preview2.jpg
      └── preview3.jpg
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
VERSION = "1.0.0"
ITEM_NAME = f"VoiceDesk-v{VERSION}"

# Files/dirs to EXCLUDE from the source package
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".git",
    ".venv",
    "venv",
    "dist",
    "*.db",
    "*.sqlite",
    ".env",
    ".env.*",
    "node_modules",
    "*.log",
    "*.spec",
    "build",
    "*.egg-info",
]


def should_exclude(path: Path) -> bool:
    for pattern in EXCLUDE_PATTERNS:
        if path.match(pattern) or any(part.match(pattern) for part in path.parts):
            return True
    return False


def copy_source(src: Path, dst: Path) -> None:
    """Copy source tree excluding unwanted files."""
    for item in src.rglob("*"):
        if item.is_file() and not should_exclude(item):
            rel = item.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def generate_schema_sql(output: Path) -> None:
    """Dump PostgreSQL schema using alembic."""
    # This would normally run: alembic upgrade head --sql > schema.sql
    # For now, create a placeholder.
    output.write_text("-- VoiceDesk schema.sql\n-- Run: alembic upgrade head --sql > schema.sql\n")


def build_zip() -> Path:
    DIST.mkdir(exist_ok=True)
    zip_path = DIST / f"{ITEM_NAME}.zip"

    if zip_path.exists():
        zip_path.unlink()

    # Create temporary staging directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / ITEM_NAME
        (stage / "Documentation").mkdir(parents=True)
        (stage / "Source").mkdir(parents=True)
        (stage / "Database").mkdir(parents=True)
        (stage / "Preview").mkdir(parents=True)

        # Documentation
        doc_src = ROOT / "Documentation"
        if doc_src.exists():
            copy_source(doc_src, stage / "Documentation")
        else:
            # Create placeholder docs
            (stage / "Documentation" / "VoiceDesk_User_Guide.pdf").write_bytes(b"%PDF placeholder")
            (stage / "Documentation" / "VoiceDesk_Admin_Guide.pdf").write_bytes(b"%PDF placeholder")
            (stage / "Documentation" / "credits.txt").write_text(
                "VoiceDesk — AI Voice Receptionist\n"
                "Third-party licenses:\n"
                "  - FastAPI (MIT)\n"
                "  - SQLAlchemy (MIT)\n"
                "  - Pydantic (MIT)\n"
                "  - Pipecat (BSD-2-Clause)\n"
                "  - Deepgram API (proprietary)\n"
                "  - ElevenLabs API (proprietary)\n"
                "  - OpenAI API (proprietary)\n"
                "  - Twilio API (proprietary)\n"
                "  - PostgreSQL (PostgreSQL License)\n"
                "  - Docker (Apache-2.0)\n"
            )

        # Source code (voice-engine + admin dashboard if exists)
        copy_source(ROOT / "voice-engine", stage / "Source" / "voice-engine")
        admin_src = ROOT / "admin"
        if admin_src.exists():
            copy_source(admin_src, stage / "Source" / "admin")

        # Database schema
        generate_schema_sql(stage / "Database" / "schema.sql")

        # Preview assets (placeholders — replace with real images)
        for i in range(1, 4):
            (stage / "Preview" / f"preview{i}.jpg").write_bytes(b"JPEG placeholder")
        (stage / "Preview" / "cover.jpg").write_bytes(b"JPEG placeholder 3:2 2340x1560")

        # Create the ZIP
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for file in stage.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(stage.parent)
                    zf.write(file, arcname)

    print(f"Created {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return zip_path


if __name__ == "__main__":
    try:
        out = build_zip()
        print(f"\n✅ Package ready: {out}")
        print("Next steps:")
        print("  1. Replace Preview/*.jpg with real screenshots (cover 3:2 2340x1560)")
        print("  2. Generate real Documentation/*.pdf from source")
        print("  3. Run alembic upgrade head --sql > Database/schema.sql")
        print("  4. Verify ZIP size < 2 GB")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)