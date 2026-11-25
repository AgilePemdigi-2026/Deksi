"""Bounded configuration and shared identities; never returns credentials in a DTO."""
import hashlib
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from django.conf import settings

PROMPT_VERSION = 'pdb-plain-id.v2'
# Read/review compatibility only; generation must still match the current version exactly.
SUPPORTED_PROMPT_VERSIONS = frozenset({'pdb-plain-id.v1', 'pdb-plain-id.v2'})
VALIDATOR_VERSION = 'pdb-narrative.v1'
MESSAGES = {
    'invalid_request': 'Permintaan draft tidak valid.',
    'unconfigured': 'Koneksi AI belum diaktifkan atau dikonfigurasi oleh pengelola.',
    'unavailable_input': 'Observasi yang direview dan bukti yang sesuai belum tersedia.',
    'conflict': 'Versi atau permintaan berubah. Periksa status sebelum mencoba lagi.',
    'busy': 'Masih ada permintaan aktif atau hasil yang belum dipastikan. Periksa daftar draft.',
    'stale_input': 'Data atau bukti berubah. Buat versi baru sebelum menyetujui.',
    'invalid_snapshot': 'Paket atau versi draft tidak lagi sesuai identitas isinya.',
    'not_ready': 'Draft belum selesai atau sudah diputuskan.',
    'invalid_output': 'Jawaban AI tidak sesuai kontrak. Tidak ada draft siap review.',
    'provider_error': 'Server AI tidak menghasilkan jawaban yang dapat digunakan.',
    'outcome_unknown': 'Permintaan mungkin sudah diterima AI. Jangan mengirim ulang otomatis.',
    'config_changed': 'Konfigurasi model berubah sejak permintaan dibuat.',
}


class NarrativeError(ValueError):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(MESSAGES[code])


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout: int = 120

    @property
    def fingerprint(self):
        return digest({'baseUrl': self.base_url})


def model_config():
    url = getattr(settings, 'LLM_BASE_URL', '')
    model = getattr(settings, 'LLM_MODEL', '')
    key = getattr(settings, 'LLM_API_KEY', '')
    timeout = getattr(settings, 'DEKSI_AI_TIMEOUT_SECONDS', 120)
    try:
        if getattr(settings, 'DEKSI_AI_NARRATIVES_ENABLED', False) is not True:
            raise ValueError
        if (not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 or c == '\\' for c in url)
                or not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,159}', model)
                or not isinstance(key, str) or '\r' in key or '\n' in key
                or type(timeout) is not int or not 120 <= timeout <= 300):
            raise ValueError
        parsed = urlsplit(url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or '@' in parsed.netloc
                or parsed.path != '/v1' or parsed.query or parsed.fragment
                or (parsed.port is not None and not 1 <= parsed.port <= 65535)):
            raise ValueError
    except ValueError:
        raise NarrativeError('unconfigured', 503) from None
    return ModelConfig(url, model, key, timeout)
