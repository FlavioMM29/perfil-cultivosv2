"""Utilidades compartidas: normalización de nombres de cultivo y mapeos entre fuentes."""
import re, unicodedata

def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c) or c == "\u0303" and False)
    return s

def norm(s: str) -> str:
    s = str(s).upper().strip()
    # conservar la Ñ
    s = s.replace("Ñ", "\u0001")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u0001", "Ñ")
    return re.sub(r"\s+", " ", s).strip()

# (prefijo, familia). Se evalúa en orden; gana el primer prefijo que coincide.
PREFIJOS = [
    ("CAÑA DE AZUCAR (PARA AZUCAR)", "CAÑA DE AZUCAR (AZUCAR)"),
    ("CAÑA DE AZUCAR (PARA ETANOL)", "CAÑA DE AZUCAR (ETANOL)"),
    ("CAÑA DE AZUCAR (PARA ALCOHOL)", "CAÑA DE AZUCAR (ALCOHOL)"),
    ("CAÑA DE AZUCAR (PARA CHANCACA)", "CAÑA DE AZUCAR (CHANCACA)"),
    ("CAÑA DE AZUCAR (PARA FRUTA)", "CAÑA DE AZUCAR (FRUTA)"),
    ("PAPAYA", "PAPAYA"), ("PAPAYUELA", "PAPAYUELA"), ("PAPRIKA", "PAPRIKA"),
    ("PAPA", "PAPA"),
    ("ARROZ", "ARROZ"), ("ALGODON", "ALGODON"),
    ("MAIZ AMARILLO", "MAIZ AMARILLO DURO"), ("MAIZ AMILACEO", "MAIZ AMILACEO"),
    ("MAIZ CHOCLO", "MAIZ CHOCLO"), ("MAIZ MORADO", "MAIZ MORADO"), ("MAIZ CHALA", "MAIZ CHALA"),
    ("FRIJOL CAUPI", "FRIJOL CAUPI"), ("FRIJOL DE PALO", "FRIJOL DE PALO"),
    ("FRIJOL CAPSULA", "FRIJOL CAPSULA"), ("FRIJOL VAINITA", "FRIJOL VAINITA"),
    ("FRIJOL GRANO VERDE", "FRIJOL GRANO VERDE"), ("FRIJOL GRANO SECO", "FRIJOL GRANO SECO"),
    ("FRIJOL LOCTAO", "FRIJOL LOCTAO"),
    ("MANGO", "MANGO"), ("PALTA", "PALTA"), ("PALTO", "PALTA"),
    ("UVA", "UVA"), ("VID", "UVA"),
    ("LIMON DULCE", "LIMON DULCE"), ("LIMON", "LIMON"),
    ("MANDARIN", "MANDARINA"), ("TANGELO", "MANDARINA"),
    ("MANZAN", "MANZANA"), ("MELOCOTON", "MELOCOTON"),
    ("NARANJ", "NARANJA"), ("BANANO", "BANANO"), ("PLATANO", "PLATANO"),
    ("AJI", "AJI"), ("AJONJOLI", "AJONJOLI"), ("AJO", "AJO"),
    ("CEBOLLA CHINA", "CEBOLLA CHINA"), ("CEBOLLA", "CEBOLLA"),
    ("CEBADA FORRAJERA", "CEBADA FORRAJERA"), ("CEBADA", "CEBADA"),
    ("CAMOTE", "CAMOTE"), ("CAFETO", "CAFE"), ("CAFE", "CAFE"),
    ("CIROLERO", "CIRUELA"), ("CIRUELO", "CIRUELA"), ("CIRUELA", "CIRUELA"),
    ("CHIRIMOY", "CHIRIMOYA"), ("COCOTERO", "COCO"), ("GUANABANO", "GUANABANA"),
    ("GUAYABO", "GUAYABA"), ("HIGUERA", "HIGO"), ("OLIVO", "ACEITUNA"),
    ("LUCUMA", "LUCUMA"), ("LUCUMO", "LUCUMA"), ("MEMBRILL", "MEMBRILLO"),
    ("PERAL", "PERA"), ("PERA ", "PERA"), ("TORONJ", "TORONJA"), ("GRANADILLA", "GRANADILLA"),
    ("GRANADO", "GRANADA"), ("PECANO", "PECANA"), ("AGUAYMANTO", "AGUAYMANTO"),
    ("ALBAHACA", "ALBAHACA"), ("BERENJENA", "BERENJENA"), ("CAIGUA", "CAIGUA"),
    ("CULANTRO", "CULANTRO"), ("ESPINACA", "ESPINACA"), ("HIERBA LUISA", "HIERBA LUISA"),
    ("PEREJIL", "PEREJIL"), ("FLORES DE CORTE", "FLORES DE CORTE"),
    ("FRESA", "FRESA"), ("JENGIBRE", "JENGIBRE"), ("JENJIBRE", "JENGIBRE"),
    ("MANI", "MANI"), ("PALILLO", "PALILLO"), ("PIJUAYO", "PIJUAYO"),
    ("PIMIENTO", "PIMIENTO"), ("QUINUA", "QUINUA"), ("ROCOTO", "ROCOTO"),
    ("RYE GRASS", "RYE GRASS"), ("TARA", "TARA"), ("TOMATE", "TOMATE"),
    ("TREBOL", "TREBOL"), ("TUNA", "TUNA"), ("YACON", "YACON"),
    ("ZANAHORIA", "ZANAHORIA"), ("LECHUGA", "LECHUGA"), ("COLIFLOR", "COLIFLOR"), ("ZAPALLO", "ZAPALLO"), ("ZARANDAJA", "ZARANDAJA"),
    ("PASTO", "PASTOS"), ("CHOCHO", "TARHUI"), ("TARHUI", "TARHUI"),
    ("BETERRAGA", "BETARRAGA"), ("BETARRAGA", "BETARRAGA"), ("AVENAS", "AVENA GRANO"),
    ("MARAÑON", "MARAÑON"), ("CAÑAHUA", "CAÑIHUA"), ("CAÑIHUA", "CAÑIHUA"),
    ("CAPULI", "CAPULI"), ("PIQUILLO", "PIQUILLO"), ("GARBANZO", "GARBANZO"),
    ("DATIL", "DATIL"), ("ARANDANO", "ARANDANO"), ("PALMA ACEITERA", "PALMA ACEITERA"),
    ("PIÑON", "PIÑON BLANCO"), ("NISPERO", "NISPERO"), ("SORGO", "SORGO"),
    ("KIWICHA", "KIWICHA"), ("ACHITA", "KIWICHA"),
]

def familia(nombre: str) -> str:
    n = norm(nombre)
    for p, f in PREFIJOS:
        if n.startswith(p):
            return f
    n = re.sub(r"\s*\(.*?\)", "", n).strip()
    n = re.sub(r"\s*\(?(T|T\.|ESP|ESPECIAL|SEMIPERM\.?|PRODUCTO)\)?\.?$", "", n).strip()
    return n or norm(nombre)

# Cultivos permanentes (resto = transitorios / semipermanentes)
PERMANENTES = {
    "ACEITUNA","ACHIOTE","AGUAJE","ALCACHOFA","ALGODON","ARANDANO","BANANO","CACAO","CAFE",
    "CAÑA DE AZUCAR (AZUCAR)","CAÑA DE AZUCAR (ETANOL)","CAÑA DE AZUCAR (ALCOHOL)",
    "CAÑA DE AZUCAR (CHANCACA)","CAÑA DE AZUCAR (FRUTA)","CAMU-CAMU","CHIRIMOYA","CIRUELA",
    "COCO","ESPARRAGO","FRESA","GRANADA","GRANADILLA","GUANABANA","GUAYABA","HIGO","LIMON",
    "LIMON DULCE","LUCUMA","MACADAMIA","MANDARINA","MANGO","MANZANA","MARACUYA","MARAÑON",
    "MELOCOTON","MEMBRILLO","NARANJA","NISPERO","PALMA ACEITERA","PALTA","PAPAYA","PECANA",
    "PERA","PIJUAYO","PIÑA","PLATANO","POMAROSA","SACHA INCHI","TARA","TE","TORONJA","TUNA",
    "UVA","VID","ZAPOTE","AGUAYMANTO","ARAZA","CEREZO","DAMASCO","KAKI O CAQUI","OLIVO",
    "ALFALFA","PASTOS","KING GRASS","BRAQUEARIA","GRAMALOTE","TREBOL","RYE GRASS","DATIL",
}

# Familia de cultivo -> prefijos arancelarios (SISCOMEX, código de 10 dígitos con cero a la izquierda)
HS = {
    "ESPARRAGO": ["0709200000","0710801000","2005600000"],
    "PALTA": ["0804400000"], "MANGO": ["0804502000","0811909100"], "UVA": ["0806100000"],
    "ARANDANO": ["0810400000"], "CACAO": ["1801"], "CAFE": ["0901"], "QUINUA": ["1008"],
    "PAPA": ["0701","0710100000","2004100000","2005200000"], "CEBOLLA": ["0703"],
    "TOMATE": ["0702"], "BANANO": ["0803"], "NARANJA": ["0805100000"],
    "MANDARINA": ["08052"], "LIMON": ["080550"], "TORONJA": ["0805400000"],
    "PIÑA": ["0804300000"], "DATIL": ["0804100000"], "HIGO": ["0804200000"],
    "GUAYABA": ["0804501000"], "ARROZ": ["1006"], "MAIZ AMARILLO DURO": ["1005"],
    "ALGODON": ["5201","5202","5203"], "OREGANO": ["1211903000"], "TRIGO BLANDO": ["1001"],
    "ALCACHOFA": ["0709910000","2005991000"], "PIQUILLO": ["2005992000"],
    "FRIJOL CAUPI": ["07133"], "GARBANZO": ["0713209000"], "LENTEJA GRANO SECO": ["0713409000"],
    "MACA": ["0714901000"], "CAMOTE": ["07142"], "LECHUGA": ["0705"],
    "ZANAHORIA": ["0706100000"], "PEPINILLO": ["0707"], "APIO": ["0709400000"],
    "ESPINACA": ["0709700000"], "BROCOLI": ["0704100000","0710802000"],
    "COCO": ["0801"], "SANDIA": ["080711"], "MELON": ["080719"],
    "PAPAYA": ["0807200000","0811909600"], "MANZANA": ["0808100000"], "PERA": ["0808300000"],
    "MEMBRILLO": ["0808400000"], "DAMASCO": ["0809100000"], "CEREZO": ["0809210000"],
    "MELOCOTON": ["0809300000"], "CIRUELA": ["0809400000"], "FRESA": ["0810100000"],
    "GRANADILLA": ["0810901000"], "MARACUYA": ["0810901000","0811909400"],
    "CHIRIMOYA": ["0810902000"], "GUANABANA": ["0810902000","0811909500"],
    "CAMU-CAMU": ["0811909200"], "LUCUMA": ["0811909300"], "ANIS": ["0909610000"],
}
