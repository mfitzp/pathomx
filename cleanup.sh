#!/bin/bash
# Locale setting for unicode
export LC_ALL='C'

echo "Metabolites..."
/usr/local/Cellar/dos2unix/6.0/bin/mac2unix ./db/metabolites
sort -u -d ./db/metabolites -o ./db/metabolites

echo "Reactions..."
/usr/local/Cellar/dos2unix/6.0/bin/mac2unix ./db/reactions
sort -u -d ./db/reactions -o ./db/reactions

echo "Pathways..."
/usr/local/Cellar/dos2unix/6.0/bin/mac2unix ./db/pathways
sort -u -d ./db/pathways -o ./db/pathways

echo "Synonyms..."
/usr/local/Cellar/dos2unix/6.0/bin/mac2unix ./db/synonyms
sort -u -d ./db/synonyms -o ./db/synonyms

echo "Done."

unset LC_ALL