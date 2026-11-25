# Fondasi narasi AI dan pilot Gemini Economic Engine

> Update main: kedua feature sudah dipadukan dengan main terbaru. Lihat [ENGINE_AI_MAIN_INTEGRATION.md](ENGINE_AI_MAIN_INTEGRATION.md) untuk pemeriksaan gabungan dan merge migration. Keterangan branch terpisah di bawah merupakan konteks publication awal; workflow generasi publik/cache/review untuk fakta engine tetap belum terintegrasi dan key tetap hanya lokal/environment server.

## Yang diimplementasikan

- Paket fakta PDB YoY terikat observasi, pembanding, sumber/RAW, review status dan digest; versi prompt/validator tersimpan bersama draft.
- Draft append-only, request idempotency, satu slot aktif per konteks, antrean/worker, output validation, hasil tidak pasti tanpa blind retry, review terpisah dari publikasi angka, riwayat review dan optimistic concurrency.
- API dan panel Admin narasi dengan permission/CSRF dan state gagal/queued/unknown yang eksplisit. Fitur default nonaktif.
- Adapter/pilot terpisah `ai_engine_pilot.py` untuk porsi PMTB/PDB dan konsumsi rumah tangga/PDB; **bukan** menyamarkan porsi menjadi laju pertumbuhan.
- CLI `backend/tools/run_engine_gemini_pilot.py` untuk prepare offline, lalu maksimal satu dispatch pada directory yang sama setelah persetujuan hash request dan quota/billing. Respons asli disimpan sebelum interpretasi, tidak diperbaiki otomatis, dan tidak dipublikasikan otomatis.

## Batas provider yang penting

Jalur draft Admin existing memakai provider OpenAI-compatible dengan base path `/v1`; konfigurasi Aorus existing dipertahankan. Gemini memakai adapter pilot tersendiri dengan host HTTPS terikat `generativelanguage.googleapis.com` dan path `/v1beta/openai`. **Jangan sekadar mengisi URL Gemini pada konfigurasi Admin lama dan menganggap seluruh workflow produksi sudah terintegrasi.**

Satu pilot Gemini nyata berhasil pada 25 November 2026 memakai `gemini-3.5-flash-lite`, finish reason `stop`, kontrak valid. Itu sampel historis Q1 2025 dengan workflow review/publikasi input simulasi, bukan persetujuan manusia. Ketersediaan model, lifecycle dan kuota harus diverifikasi kembali untuk akun/waktu eksekusi berikutnya; tidak ada fallback model atau retry otomatis.

Dashboard Economic Engine dan preview respons tersimpan berada pada branch `feat/economic-engine-bps`. Publication dua branch ini belum merupakan merge antarbranch, deploy, atau implementasi publik “klik → generate jika belum ada → shared cache → review → publikasi”. Publik tidak memperoleh endpoint generate anonim atau API key dari branch ini.

## Konfigurasi tanpa key dalam Git

Template `backend/.env.gemini-pilot.example` sengaja kosong. Gunakan environment **server-side** `GEMINI_API_KEY` saat dispatch pilot. Jangan memakai `VITE_GEMINI_API_KEY`, memasukkan key ke browser, menuliskannya ke argumen CLI, commit file populated, atau mengirim key di chat. CLI tidak otomatis membaca file key; bila key disimpan di file lokal, load assignment secara aman ke environment proses, tanpa mencetaknya.

Fondasi Admin mengenal `DEKSI_AI_NARRATIVES_ENABLED` (default false), `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, dan `DEKSI_AI_TIMEOUT_SECONDS`. Key kosong atau konfigurasi belum layak berarti fitur unavailable, bukan izin mengambil provider lain.

Gratis saja adalah batas izin, bukan bukti billing. Pastikan project benar-benar berada pada free tier/billing nonaktif, model mempunyai free quota, dan data yang dikirim sesuai kebijakan free tier. Saldo kosong atau metadata HTTP 200 tidak membuktikan free tier. Jangan aktifkan billing/top-up/fallback berbayar tanpa izin terpisah.

## Prepare offline

Dari root repository, memakai backend interpreter/dependency existing:

```text
<backend-python> -B backend/tools/run_engine_gemini_pilot.py --snapshot backend/indicators/tests/fixtures/engine_gdp_preview.json --output-dir <new-owned-output-directory> --model <verified-exact-model-id> --workflow-simulated
```

Prepare hanya menghasilkan facts/request/prepared tanpa request inference. Snapshot fixture berisi angka historis BPS dan review simulasi. Jangan menyebut hasil prepare sebagai jawaban Gemini.

## Dispatch hanya jika diizinkan

Gunakan kembali snapshot, directory dan model yang sama; tambahkan `--send-once --approve-request-sha256 <exact-prepared-hash> --acknowledge-api-billing`, dengan `GEMINI_API_KEY` hanya dalam environment proses. Flag billing adalah pengakuan operator atas izin/kuota, bukan pembatas tagihan atau pengecekan billing otomatis.

`dispatch-once.json` dibuat eksklusif sebelum jaringan. Jika timeout/crash atau status unknown, jangan hapus marker, membuat directory baru, mengulang atau mengganti model demi mencoba lagi. Read back result/raw/receipt dahulu. Pencegahan replay bersifat per-directory, bukan jaminan exactly-once global. Simpan output di lokasi lokal ignored, bukan ke repository bersama credential.

## Tes dan migrasi

Tes offline memakai fake transport dan SQLite memori; tidak membaca `.env` production atau menghubungi provider. Contoh:

```text
<backend-python> -B backend/indicators/tests/run_ai_narrative_sqlite.py --scratch <absolute-existing-scratch>
```

Runner tersebut mempunyai daftar suite eksplisit; tes engine pilot terpisah pada `indicators.tests.test_ai_engine_pilot`. Jalankan di harness settings terisolasi yang mendukung Django, tempdir scratch, dan fake transport, bukan menjalankan aplikasi produksi untuk menguji fixture.

Frontend: tetapkan `HERMES_TEST_SCRATCH` ke direktori scratch absolut existing, lalu jalankan `npm run test:ai-narratives` dari frontend setelah dependency existing siap. Typecheck/build/lint dan suite browser adalah bukti terpisah. Test PostgreSQL/browser disposable mempunyai runner terpisah dan prasyarat image/runtime yang sudah tersedia; keberadaan runner bukan bukti ia baru dijalankan.

Bukti pilot sebelumnya: 21 tes offline pilot/provider (10 engine baru, 11 provider lama) dan 123 tes backend terpilih lulus; ada overlap 11 provider, tidak dijumlahkan. Pemeriksaan publication pada salinan index Git menjalankan runner SQLite dengan daftar 123 kasus ditambah 10 engine pilot melalui wrapper QA lokal: **133 backend lolos**. Frontend: **7 kasus narasi lolos**, TypeScript/build serta lint target exit 0. Lint melaporkan satu warning existing set-state-in-effect di AdminAnalysisPage, bukan dianggap tanpa warning. Percobaan frontend pertama berhenti pada guard karena HERMES_TEST_SCRATCH belum diberikan; setelah environment proses ditetapkan, suite actual lolos. Tidak ada provider call, credential read, install, DB aktif atau deploy pada pemeriksaan itu. Artefak verifikasi/capture/log provider dan catatan agent tetap lokal, bukan hasil CI remote.

Migrasi `0025_ai_narrative_drafts` menambah draft/review narasi. Commit/push tidak menjalankan migrasi. Jangan menjalankannya pada database aktif atau deploy sebelum backup, pengujian dan izin yang sesuai. Raw angka, publikasi data, dan persetujuan narasi tetap identitas/lifecycle terpisah.
