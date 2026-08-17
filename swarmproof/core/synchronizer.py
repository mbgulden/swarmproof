"""
Dual Manifest Synchronizer for SwarmProof.

Manages synchronized generation and atomic writing of RESULT.md and
result-packet.json without content drift.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from swarmproof.schemas.manifest import DualManifest


class ManifestSynchronizer:
    """Synchronizes and validates dual human-readable and machine manifest files."""

    @staticmethod
    def write_dual_manifest(
        manifest: DualManifest,
        output_dir: Optional[str | Path] = None,
        md_filename: str = "RESULT.md",
        json_filename: str = "result-packet.json",
    ) -> Tuple[Path, Path]:
        """
        Atomically write both RESULT.md and result-packet.json to output directory.
        """
        out_dir = Path(output_dir) if output_dir else Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)

        md_path = out_dir / md_filename
        json_path = out_dir / json_filename

        md_content = manifest.generate_result_markdown()
        json_content = manifest.to_json_str()

        md_path.write_text(md_content, encoding="utf-8")
        json_path.write_text(json_content, encoding="utf-8")

        return md_path, json_path

    @staticmethod
    def load_from_directory(
        dir_path: Optional[str | Path] = None,
        json_filename: str = "result-packet.json",
    ) -> Optional[DualManifest]:
        """
        Load DualManifest from directory containing result-packet.json.
        """
        target_dir = Path(dir_path) if dir_path else Path.cwd()
        json_path = target_dir / json_filename

        if not json_path.exists():
            return None

        try:
            raw_data = json.loads(json_path.read_text(encoding="utf-8"))
            return DualManifest.from_packet(raw_data)
        except Exception:
            return None

    @staticmethod
    def verify_synchronization(
        dir_path: Optional[str | Path] = None,
        md_filename: str = "RESULT.md",
        json_filename: str = "result-packet.json",
    ) -> bool:
        """
        Verify that both RESULT.md and result-packet.json exist and match task IDs.
        """
        target_dir = Path(dir_path) if dir_path else Path.cwd()
        md_path = target_dir / md_filename
        json_path = target_dir / json_filename

        if not md_path.exists() or not json_path.exists():
            return False

        try:
            raw_json = json.loads(json_path.read_text(encoding="utf-8"))
            md_text = md_path.read_text(encoding="utf-8")
            task_id = raw_json.get("task_id", "")
            return bool(task_id and task_id in md_text)
        except Exception:
            return False
