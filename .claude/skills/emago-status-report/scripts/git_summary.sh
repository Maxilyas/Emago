#!/usr/bin/env bash
#
# emago-status-report / git_summary.sh
#
# Résume l'activité Git Emago d'une fenêtre temporelle, par auteur et par scope.
# Utilisé par le skill emago-status-report pour pré-remplir le rapport hebdomadaire.
#
# Usage :
#   bash scripts/git_summary.sh [--since="7 days ago"] [--path=backend/] [--format=json|md]
#
# Le path est filtré sur le repo Emago — par défaut tout le repo.
# Le format de sortie : "md" (humain) ou "json" (parsable).

set -euo pipefail

SINCE="7 days ago"
PATH_FILTER="."
FORMAT="md"

# Parse args
for arg in "$@"; do
  case $arg in
    --since=*)  SINCE="${arg#*=}" ;;
    --path=*)   PATH_FILTER="${arg#*=}" ;;
    --format=*) FORMAT="${arg#*=}" ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

# Vérifie qu'on est dans un repo Git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo "ERREUR : pas dans un repo Git" >&2
  exit 1
fi

# Génère le résumé
NUM_COMMITS=$(git log --since="$SINCE" --no-merges --oneline -- "$PATH_FILTER" | wc -l | tr -d ' ')
LINES_ADDED=$(git log --since="$SINCE" --no-merges --shortstat -- "$PATH_FILTER" \
  | grep -E "^ [0-9]+ files? changed" \
  | awk '{adds += $4} END {print adds+0}')
LINES_DELETED=$(git log --since="$SINCE" --no-merges --shortstat -- "$PATH_FILTER" \
  | grep -E "^ [0-9]+ files? changed" \
  | awk '{dels += $6} END {print dels+0}')
FILES_TOUCHED=$(git log --since="$SINCE" --no-merges --name-only --pretty="format:" -- "$PATH_FILTER" \
  | sort -u \
  | grep -v "^$" \
  | wc -l | tr -d ' ')

case "$FORMAT" in
  md)
    echo "## Activité Git — depuis $SINCE"
    echo ""
    echo "- Commits : $NUM_COMMITS"
    echo "- Lignes : +$LINES_ADDED / -$LINES_DELETED"
    echo "- Fichiers touchés : $FILES_TOUCHED"
    echo ""
    echo "### Commits par auteur"
    echo ""
    git log --since="$SINCE" --no-merges --pretty="format:%an" -- "$PATH_FILTER" \
      | sort | uniq -c | sort -rn \
      | awk '{print "- **" $2 "** : " $1 " commits"}'
    echo ""
    echo "### Top 10 fichiers les plus modifiés"
    echo ""
    git log --since="$SINCE" --no-merges --name-only --pretty="format:" -- "$PATH_FILTER" \
      | grep -v "^$" \
      | sort | uniq -c | sort -rn \
      | head -10 \
      | awk '{print "- `" $2 "` (" $1 " modifs)"}'
    echo ""
    echo "### Liste des commits"
    echo ""
    git log --since="$SINCE" --no-merges --pretty="format:- \`%h\` %s (%an, %ad)" --date=short -- "$PATH_FILTER"
    echo ""
    ;;
  json)
    cat <<EOF
{
  "since": "$SINCE",
  "path": "$PATH_FILTER",
  "summary": {
    "commits": $NUM_COMMITS,
    "lines_added": $LINES_ADDED,
    "lines_deleted": $LINES_DELETED,
    "files_touched": $FILES_TOUCHED
  },
  "commits": [
EOF
    git log --since="$SINCE" --no-merges --pretty='format:    {"hash":"%h","author":"%an","date":"%ad","subject":"%s"}' --date=short -- "$PATH_FILTER" \
      | paste -sd, -
    cat <<EOF

  ]
}
EOF
    ;;
  *)
    echo "Format inconnu : $FORMAT (md|json)" >&2
    exit 2
    ;;
esac
