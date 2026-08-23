#!/usr/bin/env python3
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def find_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    for manifest in sorted(src_root.glob("siminspect_*/package.xml")):
        root = ET.parse(manifest).getroot()
        package = (root.findtext("name") or manifest.parent.name).strip()
        if package == "siminspect_benchmark":
            continue
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            value = (element.text or "").strip()
            if (tag == "depend" or tag.endswith("_depend")) and value == "siminspect_benchmark":
                violations.append(f"{package}: {tag} -> {value}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=Path("src"))
    args = parser.parse_args()
    violations = find_violations(args.src)
    for violation in violations:
        print(f"VIOLATION: {violation}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
