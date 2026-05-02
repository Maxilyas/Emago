#!/usr/bin/env python3
"""
emago-attack-vector-audit / audit_router.py

Scan statique d'un router FastAPI Emago — flag les vecteurs d'attaque
détectables par analyse de code.

Usage :
    python scripts/audit_router.py app/routers/<name>.py [--verbose]

Détecte automatiquement :
- C1 : helper `_get_owned_*` présent ?
- C2/M1 : `with_for_update` sur les POST/PUT/DELETE ?
- E6 : rate-limit `_LIMITS` ?
- M2 : `math.floor` sur comparaison ressources ?
- Codes erreur en français ?
- Routes statiques avant paramétrées ?

Sortie : rapport markdown des risques détectés.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class AuditFinding:
    severity: str  # "CRITIQUE", "ÉLEVÉ", "MOYEN", "FAIBLE"
    vector: str  # "C1", "C2", "E6", "M1", "M2", etc.
    message: str
    line: int | None = None


@dataclass
class RouterAudit:
    file: str
    findings: list[AuditFinding] = field(default_factory=list)
    helpers_found: list[str] = field(default_factory=list)
    endpoints: list[dict] = field(default_factory=list)
    has_rate_limit_import: bool = False


HELPER_PATTERN = re.compile(r"async def _get_owned_(\w+)|def _get_owned_(\w+)")
ROUTE_PATTERN = re.compile(r'@router\.(get|post|put|delete|patch)\s*\(\s*"([^"]*)"', re.MULTILINE)
FOR_UPDATE_PATTERN = re.compile(r"with_for_update\s*\(\s*\)")
MATH_FLOOR_PATTERN = re.compile(r"math\.floor\s*\(")
RATE_LIMIT_IMPORT_PATTERN = re.compile(r"from\s+app\.middleware\.rate_limit\s+import|check_rate_limit")
HTTP_EXCEPTION_PATTERN = re.compile(r'HTTPException\s*\(\s*status_code\s*=\s*(\d+)[^)]*detail\s*=\s*[\'"f]?["\']([^"\']+)')
ENGLISH_DETAIL_PATTERN = re.compile(r'detail\s*=\s*["\']([A-Z][a-z]+\s+(not|cannot|invalid|missing|forbidden|unauthorized))', re.IGNORECASE)


def audit(path: Path) -> RouterAudit:
    if not path.exists():
        sys.exit(f"❌ Fichier introuvable : {path}")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    audit = RouterAudit(file=str(path))

    # 1. Helpers ownership
    for m in HELPER_PATTERN.finditer(text):
        helper = m.group(1) or m.group(2)
        audit.helpers_found.append(helper)

    # 2. Endpoints
    for m in ROUTE_PATTERN.finditer(text):
        method, path_str = m.group(1).upper(), m.group(2) or "(root)"
        line_no = text[: m.start()].count("\n") + 1
        audit.endpoints.append({"method": method, "path": path_str, "line": line_no})

    # 3. Routes statiques avant paramétrées ?
    paths = [(e["method"], e["path"], e["line"]) for e in audit.endpoints]
    # Pour chaque base path commun, vérifier que statiques sont avant /{...}
    by_base = {}
    for method, p, ln in paths:
        # extraire la base avant le 1er segment paramétré
        if "{" in p:
            base = p.split("{")[0].rstrip("/")
        else:
            base = p
        by_base.setdefault((method, base), []).append((p, ln, "{" in p))

    for (method, base), items in by_base.items():
        # Si on a au moins une statique et une paramétrée pour la même base ET la statique est après → warning
        params = [(p, ln) for p, ln, is_param in items if is_param]
        statics = [(p, ln) for p, ln, is_param in items if not is_param]
        if params and statics:
            for static_path, static_ln in statics:
                for param_path, param_ln in params:
                    if static_ln > param_ln:
                        audit.findings.append(AuditFinding(
                            severity="MOYEN",
                            vector="ROUTE_ORDER",
                            message=f"Route statique `{method} {static_path}` (ligne {static_ln}) déclarée APRÈS route paramétrée `{param_path}` (ligne {param_ln}) — risque parsing UUID",
                            line=static_ln,
                        ))

    # 4. with_for_update présent ?
    for_update_count = len(FOR_UPDATE_PATTERN.findall(text))
    mutation_count = sum(1 for e in audit.endpoints if e["method"] in ("POST", "PUT", "DELETE"))

    if mutation_count > 0 and for_update_count == 0:
        audit.findings.append(AuditFinding(
            severity="MOYEN",
            vector="M1",
            message=f"{mutation_count} endpoint(s) de mutation détecté(s) mais AUCUN `with_for_update()` — risque race conditions",
        ))
    elif mutation_count > 0 and for_update_count < mutation_count:
        audit.findings.append(AuditFinding(
            severity="FAIBLE",
            vector="M1",
            message=f"{mutation_count} endpoints de mutation, seulement {for_update_count} `with_for_update()` — vérifier que les mutations sensibles sont protégées",
        ))

    # 5. math.floor sur ressources ?
    if "metal" in text or "crystal" in text or "deuterium" in text:
        if not MATH_FLOOR_PATTERN.search(text):
            # Cherche les comparaisons sans math.floor
            risky = re.search(r"(planet\.metal|planet\.crystal|planet\.deuterium)\s*[<>]=?", text)
            if risky:
                audit.findings.append(AuditFinding(
                    severity="MOYEN",
                    vector="M2",
                    message="Comparaison ressources sans `math.floor(float(...))` — bug arrondi possible (1999.87 vs 2000)",
                ))

    # 6. Rate-limit ?
    audit.has_rate_limit_import = bool(RATE_LIMIT_IMPORT_PATTERN.search(text))

    # 7. Codes erreur — anti-énumération login ?
    if "/login" in text or "auth/login" in path.name:
        # Chercher des messages distincts pour email vs password
        if re.search(r'detail\s*=\s*["\'](Email|email)\s+(unknown|incorrect|inconnu)', text):
            if re.search(r'detail\s*=\s*["\'](Password|password|Mot)', text):
                audit.findings.append(AuditFinding(
                    severity="ÉLEVÉ",
                    vector="E3",
                    message="Login : messages distincts pour email inconnu vs MDP — VECTEUR ÉNUMÉRATION DE COMPTES",
                ))

    # 8. Détecter messages d'erreur non-français
    english_matches = ENGLISH_DETAIL_PATTERN.findall(text)
    if english_matches:
        for match in english_matches[:3]:  # limite à 3 pour éviter spam
            audit.findings.append(AuditFinding(
                severity="FAIBLE",
                vector="LANG",
                message=f'Message d\'erreur en anglais : "{match[0][:50]}" — préférer français',
            ))

    # 9. TODO/FIXME critiques
    for ln, line in enumerate(lines, 1):
        if re.search(r"#\s*(TODO|FIXME|XXX|HACK)", line, re.IGNORECASE):
            audit.findings.append(AuditFinding(
                severity="FAIBLE",
                vector="TODO",
                message=f"TODO/FIXME : `{line.strip()[:80]}`",
                line=ln,
            ))

    return audit


def render_markdown(audit: RouterAudit) -> str:
    lines = [
        f"# Audit sécurité — `{audit.file}`",
        "",
        "## Résumé",
        "",
        f"- **Endpoints** : {len(audit.endpoints)}",
        f"- **Helpers ownership détectés** : {', '.join(audit.helpers_found) if audit.helpers_found else '(aucun)'}",
        f"- **Rate-limit import** : {'✅' if audit.has_rate_limit_import else '❌'}",
        f"- **Findings** : {len(audit.findings)}",
        "",
    ]

    by_severity = {}
    for f in audit.findings:
        by_severity.setdefault(f.severity, []).append(f)

    for sev in ["CRITIQUE", "ÉLEVÉ", "MOYEN", "FAIBLE"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        lines.append(f"## {sev} ({len(items)})")
        lines.append("")
        for f in items:
            ln = f" (ligne {f.line})" if f.line else ""
            lines.append(f"- **{f.vector}**{ln} : {f.message}")
        lines.append("")

    if not audit.findings:
        lines.extend(["## ✅ Aucune anomalie détectée par l'analyse statique", ""])
        lines.append("⚠️ Note : l'analyse statique ne détecte pas tous les vecteurs (ex. C3 immuabilité, E2 isolation WS).")
        lines.append("Compléter par audit manuel et tests d'intégration (`emago-test-integration-writer`).")

    lines.append("")
    lines.append("## Endpoints scannés")
    lines.append("")
    lines.append("| Méthode | Path | Ligne |")
    lines.append("|---|---|---:|")
    for e in audit.endpoints:
        lines.append(f"| {e['method']} | `{e['path']}` | {e['line']} |")
    lines.append("")

    lines.append("## Vecteurs NON couverts par l'analyse statique")
    lines.append("")
    lines.append("L'analyse statique ne détecte PAS :")
    lines.append("- C3 (trigger PG immuabilité — global)")
    lines.append("- C4 (RNG manipulation — design)")
    lines.append("- C5 (JWT expired — runtime)")
    lines.append("- C7 (SECRET_KEY fuitée — git history)")
    lines.append("- E2 (WS isolation — runtime test)")
    lines.append("- E5 (Pedigree d'autrui — sémantique)")
    lines.append("- E7 (JSONB injection — payload-dependent)")
    lines.append("")
    lines.append("Pour ces vecteurs : audit manuel + tests d'intégration (`emago-test-integration-writer`).")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit sécurité statique d'un router Emago.")
    parser.add_argument("router_file", type=Path, help="Chemin vers app/routers/<name>.py")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    a = audit(args.router_file)
    md = render_markdown(a)

    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"✅ Audit sauvegardé : {args.output}")
    else:
        print(md)

    # Exit code selon criticité
    if any(f.severity == "CRITIQUE" for f in a.findings):
        sys.exit(2)
    if any(f.severity == "ÉLEVÉ" for f in a.findings):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
