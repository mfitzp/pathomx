from .db import DatabaseManager
from mplstyler import StylesManager, MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, \
                    MATCH_REGEXP, MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES, \
                    StyleDefinition, ClassMatchDefinition

db = DatabaseManager()

styles = StylesManager()