#!/usr/bin/env python3
"""
emago-test-integration-writer / scan_router.py

Parse un fichier router FastAPI Emago et liste les endpoints détectés
avec leurs codes d'erreur HTTP, pour pré-remplir la checklist de tests à écrire.

Usage :
    python scripts/scan_router.py app/routers/alliances.py

Sortie : table markdown des endpoints avec colonnes Method, Path, Status codes,
+ liste des tests recommandés (basée sur le mapping).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


METHOD_DECORATORS = ("@router.get", "@router.post", "@router.put", "@router.delete", "@router.patch")
HTTP_STATUS_RE = re.compile(r"status_code\s*=\s*(\d+)")
HTTP_EXCEPTION_RE = re.compile(r"HTTPException\s*\(\s*status_code\s*=\s*(\d+)")
PATH_RE = re.compile(r'@router\.(get|post|put|delete|patch)\s*\(\s*"([^"]*)"')

CODE_TO_VECTOR = {
    "401": "Auth manquante / token invalide",
    "402": "Ressources insuffisantes (V12 math.floor)",
    "403": "Refus explicite (alliance role, pedigree, combat participation)",
    "404": "Introuvable OU ownership masqué (V1)",
    "409": "Conflit d'état (statut bloquant, déjà existant, race condition V2)",
    "422": "Validation Pydantic",
    "429": "Rate-limit (V10)",
}

REQUIRED_TESTS_BY_METHOD = {
    "get": ["happy path 200", "404 inexistant", "401 sans auth"],
    "post": [
        "happy path 201",
        "402 si applicable",
        "409 si statut bloquant",
        "422 validation Pydantic",
        "V1 ownership 404",
        "V2 double-submission",
    ],
    "put": ["happy path 200", "V1 ownership 404", "409 si statut bloquant"],
    "delete": ["204 No Content", "V1 ownership 404", "409 si statut bloquant"],
    "patch": ["happy path 200", "V1 ownership 404", "422 validation"],
}


def scan_router(path: Path) -> list[dict]:
    """Parse a router file and return list of endpoint dicts."""
    if not path.exists():
        sys.exit(f"❌ Fichier introuvable : {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    endpoints = []
    current_endpoint = None

    for i, line in enumerate(lines):
        # Détection début d'endpoint
        m = PATH_RE.search(line)
        if m:
            method, p = m.group(1), m.group(2)
            current_endpoint = {
                "method": method.upper(),
                "path": p or "(root)",
                "line": i + 1,
                "status_codes": set(),
                "name": None,
            }
            # Cherche le status_code= dans le même appel
            stat_m = HTTP_STATUS_RE.search(line)
            if stat_m:
                current_endpoint["status_codes"].add(stat_m.group(1))
            continue

        # Suite de l'endpoint : récupérer la fonction et les status codes levés
        if current_endpoint is not None:
            # Fin du bloc : nouvelle déco ou DEF en colonne 0
            if line.startswith("async def ") or line.startswith("def "):
                fn_m = re.match(r"(?:async\s+)?def\s+(\w+)", line)
                if fn_m:
                    current_endpoint["name"] = fn_m.group(1)
            elif line.startswith("@") and not line.strip().startswith("@router."):
                continue
            elif line.startswith("@router.") and current_endpoint.get("name"):
                # Sauve l'endpoint courant et redémarre
                endpoints.append(current_endpoint)
                current_endpoint = None
                # Re-trigger detection
                m = PATH_RE.search(line)
                if m:
                    current_endpoint = {
                        "method": m.group(1).upper(),
                        "path": m.group(2) or "(root)",
                        "line": i + 1,
                        "status_codes": set(),
                        "name": None,
                    }
                    stat_m = HTTP_STATUS_RE.search(line)
                    if stat_m:
                        current_endpoint["status_codes"].add(stat_m.group(1))
            else:
                # Cherche raise HTTPException(status_code=...)
                exc_m = HTTP_EXCEPTION_RE.search(line)
                if exc_m:
                    current_endpoint["status_codes"].add(exc_m.group(1))

    if current_endpoint is not None and current_endpoint.get("name"):
        endpoints.append(current_endpoint)

    return endpoints


def render_markdown(endpoints: list[dict], router_name: str) -> str:
    """Render the analysis as a markdown report."""
    lines = [
        f"# Audit tests router `{router_name}`",
        "",
        f"## Endpoints détectés ({len(endpoints)})",
        "",
        "| Méthode | Path | Function | Codes HTTP | Ligne |",
        "|---|---|---|---|---:|",
    ]
    for ep in endpoints:
        codes = ", ".join(sorted(ep["status_codes"])) or "—"
        lines.append(f"| {ep['method']} | `{ep['path']}` | `{ep['name']}` | {codes} | {ep['line']} |")

    lines.extend(["", "## Tests recommandés par endpoint", ""])

    for ep in endpoints:
        lines.append(f"### {ep['method']} {ep['path']} (`{ep['name']}`)")
        lines.append("")
        method_tests = REQUIRED_TESTS_BY_METHOD.get(ep["method"].lower(), [])
        for t in method_tests:
            lines.append(f"- ☐ {t}")
        # Tests dérivés des status codes détectés
        for code in sorted(ep["status_codes"]):
            vector = CODE_TO_VECTOR.get(code, f"Code {code}")
            lines.append(f"- ☐ Test pour code {code} : {vector}")
        lines.append("")

    lines.append("## Récap couverture cible")
    lines.append("")
    lines.append(f"- {len(endpoints)} endpoints à tester.")
    total_cases = sum(
        len(REQUIRED_TESTS_BY_METHOD.get(ep["method"].lower(), [])) + len(ep["status_codes"])
        for ep in endpoints
    )
    lines.append(f"- ~{total_cases} cas de test à écrire au minimum.")
    lines.append("")
    lines.append("Pour générer les tests : utilise `emago-test-integration-writer` avec ce rapport en input.")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan un router FastAPI Emago.")
    parser.add_argument("router_file", type=Path, help="Chemin vers app/routers/<name>.py")
    parser.add_argument("--output", type=Path, default=None, help="Fichier markdown de sortie (sinon stdout)")
    args = parser.parse_args()

    endpoints = scan_router(args.router_file)
    md = render_markdown(endpoints, args.router_file.stem)

    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"✅ Audit sauvegardé : {args.output}")
    else:
        print(md)


if __name__ == "__main__":
    main()
