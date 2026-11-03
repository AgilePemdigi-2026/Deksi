from datetime import date, timedelta

from indicators.parsing import normalize_text


def validate_one(observation) -> str | None:
    """Cek: nilai ada, unit ada, periode dalam rentang wajar, nilai indikator sesuai rentang."""
    if observation.value is None:
        return "value kosong"
    if normalize_text(observation.unit) == "" and observation.indicator.code != "cad_devisa":
        return "unit kosong"
    today = date.today()
    if observation.observation_date > today + timedelta(days=180):
        return "observation_date di masa depan"
    if observation.observation_date < date(2010, 1, 1):
        return "observation_date sebelum 2010"
    if observation.indicator.code == "birate" and not (0 < observation.value <= 20):
        return "nilai birate di luar rentang wajar 0-20%"
    if observation.indicator.code == "jisdor" and not (1000 < observation.value < 100000):
        return "nilai jisdor di luar rentang wajar (Rp/USD)"
    if observation.indicator.code == "investasi" and not (0 < observation.value < 1500):
        return "nilai investasi di luar rentang wajar (Rp Triliun per triwulan)"
    if observation.indicator.code == "fiskal" and not (-100 < observation.value < 100):
        return "nilai fiskal di luar rentang wajar (% PDB)"
    if observation.indicator.code in ("pendapatan_negara", "belanja_negara", "defisit_apbn") and not (
        0 <= observation.value <= 100000
    ):
        return "nilai APBN di luar rentang wajar (Rp Triliun kumulatif)"
    return None
