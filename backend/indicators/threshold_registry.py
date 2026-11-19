"""Feature 24: registry parameter threshold diagnostik yang didukung.

Hanya parameter di sini yang dapat dikonfigurasi Admin. Formula inti
Economic Engine tidak terdaftar di sini dan tidak dapat diubah lewat API
threshold. Nilai ekonomi resmi dihitung di indicators/views.py dan tidak
membaca registry ini kecuali untuk evaluasi status diagnostik.
"""
from decimal import Decimal

# indicator_code -> daftar parameter diagnostik yang configurable.
SUPPORTED_THRESHOLDS: dict[str, list[dict]] = {
    "pdb": [
        {
            "param_key": "batas_pdb_yoy",
            "label": "Batas PDB YoY",
            "category": "PDB",
            "unit": "%",
            "min_allowed": Decimal("0"),
            "max_allowed": Decimal("15"),
            "default_value": Decimal("5"),
            "description": "Ambang peringatan laju PDB YoY. Status melebihi bila nilai terbaru di atas batas.",
        },
    ],
    "inflasi": [
        {
            "param_key": "batas_inflasi_yoy",
            "label": "Batas Inflasi YoY",
            "category": "Inflasi",
            "unit": "%",
            "min_allowed": Decimal("0"),
            "max_allowed": Decimal("20"),
            "default_value": Decimal("4"),
            "description": "Ambang peringatan inflasi YoY. Nilai negatif tidak valid.",
        },
    ],
    "fiskal": [
        {
            "param_key": "batas_fiskal_level",
            "label": "Batas Fiskal Level",
            "category": "Fiskal",
            "unit": "Rp triliun",
            "min_allowed": Decimal("0"),
            "max_allowed": Decimal("1000"),
            "default_value": Decimal("200"),
            "description": "Ambang level fiskal dalam Rp triliun.",
        },
    ],
    "investasi": [
        {
            "param_key": "batas_investasi_level",
            "label": "Batas Investasi Level",
            "category": "Investasi",
            "unit": "Rp triliun",
            "min_allowed": Decimal("0"),
            "max_allowed": Decimal("1000"),
            "default_value": Decimal("130"),
            "description": "Ambang level investasi dalam Rp triliun.",
        },
    ],
    "birate": [
        {
            "param_key": "batas_birate_level",
            "label": "Batas BI-Rate",
            "category": "Moneter",
            "unit": "%",
            "min_allowed": Decimal("0"),
            "max_allowed": Decimal("20"),
            "default_value": Decimal("6"),
            "description": "Ambang level BI-Rate dalam persen.",
        },
    ],
    "tpt": [
        {
            "param_key": "batas_tpt_level",
            "label": "Batas Pengangguran (TPT)",
            "category": "Tenaga Kerja",
            "unit": "%",
            "min_allowed": Decimal("0"),
            "max_allowed": Decimal("20"),
            "default_value": Decimal("6"),
            "description": "Ambang tingkat pengangguran terbuka dalam persen.",
        },
    ],
}


def get_supported(indicator_code: str, param_key: str) -> dict | None:
    for entry in SUPPORTED_THRESHOLDS.get(indicator_code, []):
        if entry["param_key"] == param_key:
            return entry
    return None


def all_supported() -> list[dict]:
    out = []
    for code, params in SUPPORTED_THRESHOLDS.items():
        for entry in params:
            out.append({"indicatorCode": code, **entry})
    return out
