"""Book catalog for the canonical (KJV + KJV-Apocrypha) spine.

Canonical IDs use OSIS-style book codes, matching the existing Contabulate
Bible instances (Gen, Exod, Ps, Matt, ...). TVTMS uses SIL/Paratext codes
(Gen, Exo, Psa, Mat, ...); `SIL` maps between them.
"""

# (osis, sil, section, English, Latin (Vulgate), Greek (LXX/NT), Hebrew, German)
BOOKS = [
    ("Gen", "Gen", "OT", "Genesis", "Genesis", "Γένεσις", "בראשית", "1. Mose"),
    ("Exod", "Exo", "OT", "Exodus", "Exodus", "Ἔξοδος", "שמות", "2. Mose"),
    ("Lev", "Lev", "OT", "Leviticus", "Leviticus", "Λευιτικόν", "ויקרא", "3. Mose"),
    ("Num", "Num", "OT", "Numbers", "Numeri", "Ἀριθμοί", "במדבר", "4. Mose"),
    ("Deut", "Deu", "OT", "Deuteronomy", "Deuteronomium", "Δευτερονόμιον", "דברים", "5. Mose"),
    ("Josh", "Jos", "OT", "Joshua", "Josue", "Ἰησοῦς", "יהושע", "Josua"),
    ("Judg", "Jdg", "OT", "Judges", "Judicum", "Κριταί", "שופטים", "Richter"),
    ("Ruth", "Rut", "OT", "Ruth", "Ruth", "Ῥούθ", "רות", "Rut"),
    ("1Sam", "1Sa", "OT", "1 Samuel", "1 Regum", "1 Βασιλειῶν", "שמואל א", "1. Samuel"),
    ("2Sam", "2Sa", "OT", "2 Samuel", "2 Regum", "2 Βασιλειῶν", "שמואל ב", "2. Samuel"),
    ("1Kgs", "1Ki", "OT", "1 Kings", "3 Regum", "3 Βασιλειῶν", "מלכים א", "1. Könige"),
    ("2Kgs", "2Ki", "OT", "2 Kings", "4 Regum", "4 Βασιλειῶν", "מלכים ב", "2. Könige"),
    ("1Chr", "1Ch", "OT", "1 Chronicles", "1 Paralipomenon", "1 Παραλειπομένων", "דברי הימים א", "1. Chronik"),
    ("2Chr", "2Ch", "OT", "2 Chronicles", "2 Paralipomenon", "2 Παραλειπομένων", "דברי הימים ב", "2. Chronik"),
    ("Ezra", "Ezr", "OT", "Ezra", "1 Esdræ", "Ἔσδρας Β (1–10)", "עזרא", "Esra"),
    ("Neh", "Neh", "OT", "Nehemiah", "2 Esdræ (Nehemiæ)", "Ἔσδρας Β (11–23)", "נחמיה", "Nehemia"),
    ("Esth", "Est", "OT", "Esther", "Esther", "Ἐσθήρ", "אסתר", "Esther"),
    ("Job", "Job", "OT", "Job", "Job", "Ἰώβ", "איוב", "Hiob"),
    ("Ps", "Psa", "OT", "Psalms", "Psalmi", "Ψαλμοί", "תהלים", "Psalmen"),
    ("Prov", "Pro", "OT", "Proverbs", "Proverbia", "Παροιμίαι", "משלי", "Sprüche"),
    ("Eccl", "Ecc", "OT", "Ecclesiastes", "Ecclesiastes", "Ἐκκλησιαστής", "קהלת", "Prediger"),
    ("Song", "Sng", "OT", "Song of Solomon", "Canticum Canticorum", "Ἆσμα", "שיר השירים", "Hohelied"),
    ("Isa", "Isa", "OT", "Isaiah", "Isaias", "Ἠσαΐας", "ישעיהו", "Jesaja"),
    ("Jer", "Jer", "OT", "Jeremiah", "Jeremias", "Ἱερεμίας", "ירמיהו", "Jeremia"),
    ("Lam", "Lam", "OT", "Lamentations", "Lamentationes", "Θρῆνοι", "איכה", "Klagelieder"),
    ("Ezek", "Ezk", "OT", "Ezekiel", "Ezechiel", "Ἰεζεκιήλ", "יחזקאל", "Hesekiel"),
    ("Dan", "Dan", "OT", "Daniel", "Daniel", "Δανιήλ", "דניאל", "Daniel"),
    ("Hos", "Hos", "OT", "Hosea", "Osee", "Ὡσηέ", "הושע", "Hosea"),
    ("Joel", "Jol", "OT", "Joel", "Joël", "Ἰωήλ", "יואל", "Joel"),
    ("Amos", "Amo", "OT", "Amos", "Amos", "Ἀμώς", "עמוס", "Amos"),
    ("Obad", "Oba", "OT", "Obadiah", "Abdias", "Ἀβδιού", "עובדיה", "Obadja"),
    ("Jonah", "Jon", "OT", "Jonah", "Jonas", "Ἰωνᾶς", "יונה", "Jona"),
    ("Mic", "Mic", "OT", "Micah", "Michæas", "Μιχαίας", "מיכה", "Micha"),
    ("Nah", "Nam", "OT", "Nahum", "Nahum", "Ναούμ", "נחום", "Nahum"),
    ("Hab", "Hab", "OT", "Habakkuk", "Habacuc", "Ἀμβακούμ", "חבקוק", "Habakuk"),
    ("Zeph", "Zep", "OT", "Zephaniah", "Sophonias", "Σοφονίας", "צפניה", "Zephanja"),
    ("Hag", "Hag", "OT", "Haggai", "Aggæus", "Ἀγγαῖος", "חגי", "Haggai"),
    ("Zech", "Zec", "OT", "Zechariah", "Zacharias", "Ζαχαρίας", "זכריה", "Sacharja"),
    ("Mal", "Mal", "OT", "Malachi", "Malachias", "Μαλαχίας", "מלאכי", "Maleachi"),
    # Deuterocanon / Apocrypha, KJV-Apocrypha (KJVA) standard numbering as in TVTMS
    ("Tob", "Tob", "DC", "Tobit", "Tobiæ", "Τωβίτ", "", "Tobias"),
    ("Jdt", "Jdt", "DC", "Judith", "Judith", "Ἰουδίθ", "", "Judith"),
    ("Wis", "Wis", "DC", "Wisdom", "Sapientia", "Σοφία Σαλωμῶνος", "", "Weisheit"),
    ("Sir", "Sir", "DC", "Sirach", "Ecclesiasticus", "Σοφία Σειράχ", "", "Jesus Sirach"),
    ("Bar", "Bar", "DC", "Baruch (6 = Ep. Jeremiah)", "Baruch", "Βαρούχ", "", "Baruch"),
    ("1Macc", "1Ma", "DC", "1 Maccabees", "1 Machabæorum", "1 Μακκαβαίων", "", "1. Makkabäer"),
    ("2Macc", "2Ma", "DC", "2 Maccabees", "2 Machabæorum", "2 Μακκαβαίων", "", "2. Makkabäer"),
    ("1Esd", "1Es", "DC", "1 Esdras", "3 Esdræ", "Ἔσδρας Α", "", "3. Esra"),
    ("3Macc", "3Ma", "DC", "3 Maccabees", "", "3 Μακκαβαίων", "", "3. Makkabäer"),
    ("4Macc", "4Ma", "DC", "4 Maccabees", "", "4 Μακκαβαίων", "", "4. Makkabäer"),
    ("PrAzar", "S3Y", "DC", "Prayer of Azariah & Song of the Three", "Daniel 3:24–90", "Δανιήλ 3:24–90", "", "Gebet Asarjas"),
    ("Sus", "Sus", "DC", "Susanna", "Daniel 13", "Σουσάννα", "", "Susanna"),
    ("Bel", "Bel", "DC", "Bel and the Dragon", "Daniel 14", "Βὴλ καὶ Δράκων", "", "Bel und Drache"),
    ("PrMan", "Man", "DC", "Prayer of Manasseh", "Oratio Manassæ", "Προσευχὴ Μανασσῆ", "", "Gebet Manasses"),
    ("AddPs", "Ps2", "DC", "Psalm 151", "", "Ψαλμός 151", "", "Psalm 151"),
    ("Odes", "Ode", "DC", "Odes", "", "Ὠδαί", "", "Oden"),
    ("PssSol", "Pss", "DC", "Psalms of Solomon", "", "Ψαλμοὶ Σολομῶντος", "", "Psalmen Salomos"),
    # New Testament
    ("Matt", "Mat", "NT", "Matthew", "Matthæus", "Κατὰ Μαθθαῖον", "", "Matthäus"),
    ("Mark", "Mrk", "NT", "Mark", "Marcus", "Κατὰ Μᾶρκον", "", "Markus"),
    ("Luke", "Luk", "NT", "Luke", "Lucas", "Κατὰ Λουκᾶν", "", "Lukas"),
    ("John", "Jhn", "NT", "John", "Joannes", "Κατὰ Ἰωάννην", "", "Johannes"),
    ("Acts", "Act", "NT", "Acts", "Actus Apostolorum", "Πράξεις", "", "Apostelgeschichte"),
    ("Rom", "Rom", "NT", "Romans", "ad Romanos", "Πρὸς Ῥωμαίους", "", "Römer"),
    ("1Cor", "1Co", "NT", "1 Corinthians", "1 ad Corinthios", "Πρὸς Κορινθίους Α", "", "1. Korinther"),
    ("2Cor", "2Co", "NT", "2 Corinthians", "2 ad Corinthios", "Πρὸς Κορινθίους Β", "", "2. Korinther"),
    ("Gal", "Gal", "NT", "Galatians", "ad Galatas", "Πρὸς Γαλάτας", "", "Galater"),
    ("Eph", "Eph", "NT", "Ephesians", "ad Ephesios", "Πρὸς Ἐφεσίους", "", "Epheser"),
    ("Phil", "Php", "NT", "Philippians", "ad Philippenses", "Πρὸς Φιλιππησίους", "", "Philipper"),
    ("Col", "Col", "NT", "Colossians", "ad Colossenses", "Πρὸς Κολοσσαεῖς", "", "Kolosser"),
    ("1Thess", "1Th", "NT", "1 Thessalonians", "1 ad Thessalonicenses", "Πρὸς Θεσσαλονικεῖς Α", "", "1. Thessalonicher"),
    ("2Thess", "2Th", "NT", "2 Thessalonians", "2 ad Thessalonicenses", "Πρὸς Θεσσαλονικεῖς Β", "", "2. Thessalonicher"),
    ("1Tim", "1Ti", "NT", "1 Timothy", "1 ad Timotheum", "Πρὸς Τιμόθεον Α", "", "1. Timotheus"),
    ("2Tim", "2Ti", "NT", "2 Timothy", "2 ad Timotheum", "Πρὸς Τιμόθεον Β", "", "2. Timotheus"),
    ("Titus", "Tit", "NT", "Titus", "ad Titum", "Πρὸς Τίτον", "", "Titus"),
    ("Phlm", "Phm", "NT", "Philemon", "ad Philemonem", "Πρὸς Φιλήμονα", "", "Philemon"),
    ("Heb", "Heb", "NT", "Hebrews", "ad Hebræos", "Πρὸς Ἑβραίους", "", "Hebräer"),
    ("Jas", "Jas", "NT", "James", "Jacobi", "Ἰακώβου", "", "Jakobus"),
    ("1Pet", "1Pe", "NT", "1 Peter", "1 Petri", "Πέτρου Α", "", "1. Petrus"),
    ("2Pet", "2Pe", "NT", "2 Peter", "2 Petri", "Πέτρου Β", "", "2. Petrus"),
    ("1John", "1Jn", "NT", "1 John", "1 Joannis", "Ἰωάννου Α", "", "1. Johannes"),
    ("2John", "2Jn", "NT", "2 John", "2 Joannis", "Ἰωάννου Β", "", "2. Johannes"),
    ("3John", "3Jn", "NT", "3 John", "3 Joannis", "Ἰωάννου Γ", "", "3. Johannes"),
    ("Jude", "Jud", "NT", "Jude", "Judæ", "Ἰούδα", "", "Judas"),
    ("Rev", "Rev", "NT", "Revelation", "Apocalypsis", "Ἀποκάλυψις", "", "Offenbarung"),
]

ORDER = {b[0]: i for i, b in enumerate(BOOKS)}
SIL_TO_OSIS = {b[1]: b[0] for b in BOOKS}
OSIS_TO_SIL = {b[0]: b[1] for b in BOOKS}
# TVTMS also uses these aliases in a few places
SIL_TO_OSIS.update({"Esg": "Esth", "Ade": "Esth", "Lje": "Bar"})
SECTION = {b[0]: b[2] for b in BOOKS}
NAME = {b[0]: b[3] for b in BOOKS}

# USFM (Vulgate USFX) -> OSIS
USFM_TO_OSIS = {
    "GEN": "Gen", "EXO": "Exod", "LEV": "Lev", "NUM": "Num", "DEU": "Deut", "JOS": "Josh",
    "JDG": "Judg", "RUT": "Ruth", "1SA": "1Sam", "2SA": "2Sam", "1KI": "1Kgs", "2KI": "2Kgs",
    "1CH": "1Chr", "2CH": "2Chr", "EZR": "Ezra", "NEH": "Neh", "TOB": "Tob", "JDT": "Jdt",
    "EST": "Esth", "JOB": "Job", "PSA": "Ps", "PRO": "Prov", "ECC": "Eccl", "SNG": "Song",
    "WIS": "Wis", "SIR": "Sir", "ISA": "Isa", "JER": "Jer", "LAM": "Lam", "BAR": "Bar",
    "EZK": "Ezek", "DAN": "Dan", "HOS": "Hos", "JOL": "Joel", "AMO": "Amos", "OBA": "Obad",
    "JON": "Jonah", "MIC": "Mic", "NAM": "Nah", "HAB": "Hab", "ZEP": "Zeph", "HAG": "Hag",
    "ZEC": "Zech", "MAL": "Mal", "1MA": "1Macc", "2MA": "2Macc", "MAT": "Matt", "MRK": "Mark",
    "LUK": "Luke", "JHN": "John", "ACT": "Acts", "ROM": "Rom", "1CO": "1Cor", "2CO": "2Cor",
    "GAL": "Gal", "EPH": "Eph", "PHP": "Phil", "COL": "Col", "1TH": "1Thess", "2TH": "2Thess",
    "1TI": "1Tim", "2TI": "2Tim", "TIT": "Titus", "PHM": "Phlm", "HEB": "Heb", "JAS": "Jas",
    "1PE": "1Pet", "2PE": "2Pet", "1JN": "1John", "2JN": "2John", "3JN": "3John", "JUD": "Jude",
    "REV": "Rev",
}

# Native book labels, shown when a text's own reference differs from the spine.
VULGATE_LABEL = {
    "1Sam": "1 Reg", "2Sam": "2 Reg", "1Kgs": "3 Reg", "2Kgs": "4 Reg",
    "1Chr": "1 Par", "2Chr": "2 Par", "Ezra": "1 Esd", "Neh": "2 Esd",
    "Tob": "Tob", "Sir": "Eccli", "Song": "Cant", "Hos": "Os", "Obad": "Abd",
    "Zeph": "Soph", "Hag": "Agg", "Rev": "Apoc",
}
LXX_LABEL = {
    "1Sam": "1 Kgdms", "2Sam": "2 Kgdms", "1Kgs": "3 Kgdms", "2Kgs": "4 Kgdms",
    "1Chr": "1 Para", "2Chr": "2 Para", "Ezra": "2 Esdr", "Neh": "2 Esdr", "1Esd": "1 Esdr",
    "Sus": "Sus θ", "Bel": "Bel θ", "Dan": "Dan θ", "Bar": "EpJer",
}
