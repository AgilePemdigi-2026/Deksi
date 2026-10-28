# Backend fitur 6 — kontrak Detail Indikator

> **Navigasi status terbaru:** dokumen ini adalah baseline rancangan Batch 1. Implementasi Batch 2 dan batas runtime saat ini dijelaskan pada [IMPLEMENTATION.md](IMPLEMENTATION.md); status PROPOSAL/NOT RUN di bawah merekam tahap rancangan, bukan hasil tes kode yang ditambahkan kemudian.

**Status: PROPOSAL; endpoint belum diimplementasikan.** Batch 1, 27 Oktober 2026 (UTC+07). Pengguna mengizinkan kontrak dan assessment fondasi, bukan model, migrasi, database atau publikasi. Snapshot sumber: `main` / `21a065d3f145364a758aeec07571768a0ed29768`. Worktree lokal `E:/Deksi-feature-6-api`, branch `feat/6-indicator-detail-api`. Base lokal ini belum merupakan keputusan target PR backend. Instruksi **tidak push** tetap berlaku.

## 1. Tujuan dan otoritas

Fitur 6 / UC-02 menyediakan satu halaman Detail Indikator publik. Bukan pembangunan ringkasan dashboard fitur 3 atau grafik utama fitur 4 milik anggota lain. Histori di sini adalah deret satu indikator untuk grafik/tabel detail, bukan filter dashboard fitur 5 atau histori revisi fitur 7.

Paket ini:
- [contract.json](contract.json): kontrak terstruktur untuk review, **bukan OpenAPI, konfigurasi runtime atau contoh respons aktual**.
- [FOUNDATION.md](FOUNDATION.md): skema existing, shared revision, perubahan minimum dan gate keputusan.
- [ACCEPTANCE.md](ACCEPTANCE.md): requirement dan skenario, seluruh tes API/database **NOT RUN**.

Otoritas produk: keputusan pengguna terbaru dan PRD lokal F6-01..F6-07/Q-03..Q-05. Baseline dokumentasi 20 Oktober masih menyebut frontend-only; izin baru backend menggantikan batas scope lama hanya untuk pekerjaan ini. Tidak menyalin atau mengesahkan seluruh proposal baseline. Persetujuan Batch 1 bukan persetujuan skema/publikasi atau bukti angka resmi.

## 2. Fakta kode yang dipakai

| Sumber | Bukti statik |
|---|---|
| [requirements](../../requirements.txt) | Django/DRF tercantum; tidak memasang atau mengimpor pada batch ini |
| [root router](../../backend/urls.py) | Prefix `/api/v1/indicators/` terdaftar |
| [indicator router](../../apps/indicators/urls.py) | `urlpatterns = []`; belum ada endpoint detail/histori |
| [models](../../apps/indicators/models.py) | EconomicIndicator, IndicatorDataPoint, SourceTrace, DataSource tersedia; decimal nullable, periode, status publikasi |
| [migration](../../apps/indicators/migrations/0001_initial.py) | Skema awal, bukan bukti migrasi telah diterapkan |
| [Admin](../../apps/indicators/admin.py) | Working value/master/trace dapat diedit; belum revision-bound review |
| [settings](../../backend/settings.py) | Global DRF IsAuthenticated, JSON, pagination 20, anonymous throttle 20/minute |

Frontend pada branch `fe` dibaca terpisah: `app/Support/IndicatorRepository.php` masih JSON lokal; `IndicatorHistory.php` hanya menerima int/float/null untuk geometri. API decimal string kelak membutuhkan adapter teruji: pertahankan string asli untuk tabel/nilai, konversi terkontrol hanya untuk koordinat SVG, bukan perhitungan metrik. Fitur 6 yang merged ke fe belum otomatis tersedia pada main; jangan memindahkan frontend ke backend worktree ini.

Rancangan fitur 7 existing tersedia **lokal, untracked, belum diimplementasikan** pada `E:/Deksi-Team/.hermes/worktrees/source-trace-api/backend/docs/source-trace/{README.md,VERSIONING.md,ACCEPTANCE.md,contract.json}`, berbasis be `03052e3`. Tidak dibundel/disalin ke paket ini. Referensi kompatibilitas ada di FOUNDATION dan contract; bila paket dipindah, reviewer perlu menerima sumber F7 tersebut secara terpisah. Ketiadaan paket itu bukan bukti F7 sudah diimplementasikan.

## 3. Endpoint baca yang diusulkan

| ID | GET path | Makna |
|---|---|---|
| current | `/api/v1/indicators/{code}/detail/` | Observasi terbaru **menurut periode** dalam satu seri/frekuensi, memakai revisi publik terakhir per observasi |
| history | `/api/v1/indicators/{code}/history/` | Nilai antarperiode, bukan daftar revisi; `period_type` dan `page` sesuai aturan berikut |
| revision | `/api/v1/indicators/{code}/data-points/{data_point_id}/revisions/{revision_id}/` | Detail tepat satu revisi publik; tidak fallback ke current |

`code` adalah kode tersimpan persis (max 50 karakter), tidak case-fold, alias otomatis, atau diasumsikan sama dengan `pdb` fixture FE. UUID path harus valid dan parent indicator/point/revision harus cocok. Karakter path yang tidak didukung tidak diperbaiki menjadi kode lain.

GET/HEAD/OPTIONS saja; HEAD body kosong, OPTIONS tidak membuka field Admin. Metode mutasi 405 tanpa write. Tidak menambah endpoint list dashboard, write publik, ingest, AI, login atau Source Trace di batch implementasi fitur 6.

### Seleksi current dan histori

1. Mulai dari **snapshot revisi yang publikasi/review-nya sah**, bukan live join working rows. Status published pada data point lama bukan bukti review revisi. RAW tetap internal meskipun legacy statusnya published. Official hanya layer clean; derived hanya derived. Jangan menyatukan dua layer atau menganggap official=verified.
2. Untuk setiap point pilih sequence tertinggi di antara revisi publik yang sah; draft/pending/rejected baru tidak menyingkirkan revisi publik sebelumnya. Default produksi tidak menyajikan origin demo; profil demo terpisah perlu izin. Origin unknown tetap diberi warning, bukan dinaikkan menjadi official_source.
3. `period_type` opsional hanya bila satu frekuensi publik tersedia. Jika beberapa tersedia, tanpa pilihan menghasilkan 400 `series_selection_required`, bukan memilih bulanan/tahunan sembarang. Nilai query hanya annual/quarterly/monthly. Parameter unknown, duplikat atau query tak didukung ditolak 400; revision tidak menerima query current/history.
4. Periode memakai struktur nyata, bukan urutan alfabet label atau fetched_at. Annual: month/quarter null; quarterly: quarter 1..4, month null; monthly: month 1..12, quarter null. Label semester tidak dipaksa menjadi annual/quarterly. Semantik semester/konsep harga/base year yang tidak dimodelkan adalah batas kontrak, bukan nilai tebakan.
5. Dalam satu seri, unit dan jenis nilai frozen harus konsisten. Dua UUID point berbeda pada periode yang sama atau unit/konsep yang bertentangan menghasilkan 503 `ambiguous_series`/`inconsistent_series`; UUID tie-break bukan penyelesaian konflik ekonomi. Model belum mempunyai identitas konsep harga/base year terstruktur: tidak menjanjikan bisa mendeteksi perbedaan semantik yang tidak pernah direkam. Pengelola harus memakai kode indikator terpisah untuk seri berbeda dan mereview maknanya.
6. Current memilih periode terbesar dalam frekuensi yang sudah jelas; nilai terbaru null tetap null, tidak mundur diam-diam ke angka nonnull. No public revision = generic 404, walau working master ada. Keberadaan master belum merupakan otorisasi publikasi identitas.
7. History: page positif, ukuran tetap 20, urutan periode ascending. Satu hasil per point dan setiap hasil membawa revision_id; count/next/previous mengacu hanya proyeksi publik terpilih. Jika indikator memiliki publikasi sah tetapi frekuensi valid yang dipilih belum punya baris, page 1 menghasilkan 200 dengan results []; page selanjutnya 404. Current untuk pilihan tanpa observasi menghasilkan generic 404.
8. Metadata `view=current_published_per_observation` berarti konteks publik saat request, **bukan as-of historis** dan bukan snapshot seluruh seri lintas halaman. Respons dibuat konsisten dalam satu request; perpindahan page bisa melihat publikasi baru. Jangan menjanjikan reproducible whole-series snapshot tanpa storage/query tambahan yang disepakati.
9. Baris supplied bernilai null tetap disertakan. Periode di antara dua observasi yang tidak disediakan tidak boleh tersambung sebagai observasi kontinu; kontrak `gap_policy=break_on_null_or_missing_period` mengharuskan adapter grafik memutus garis pada jarak kalender yang hilang, tanpa menciptakan row database atau nilai nol. Histori konsisten pada satu period_type sehingga adjacency bisa diuji deterministik.

### Pinned detail dan histori

Pinned detail mengembalikan konten revisi itu, bukan master/value/source terbaru. `links.history` adalah konteks histori publik **saat ini**, bukan histori sebagaimana diketahui pada revisi lama. Jika konteks unit/jenis/period_type pinned sudah berbeda dari seri current, link history null dan warning `history_context_changed`; jangan menggabungkan seri baru ke angka lama. Link source hanya menunjuk revision yang sama melalui contract F7 dan hanya bila snapshot memiliki trace serta endpoint F7 sudah tersedia secara nyata. Sebelum itu link null dengan warning. Jangan membuat URL yang kelihatannya berfungsi hanya karena route telah dirancang.

## 4. Respons dan mapping

Envelope sukses mengikuti pola accounts: `success`, `message`, `data`. Detail data berisi `snapshot`, `publication`, `metadata`, `links`; history berisi `series`, `view`, `gap_policy`, `count`, `next`, `previous`, `results`. Semua field stabil hadir, unavailable=null, lists kosong=[]; tidak mengirim HTML display string sebagai sumber angka. Daftar field dan mapping persis ada pada contract.json.

- Decimal string sesuai skala penyimpanan `(20,4)`; zero `"0.0000"`, missing null. Jangan float/round ulang atau mengklaim digit sumber di luar yang disimpan.
- Unit/name/type/category/definition/metodologi dibekukan bersama nilai, bukan ditarik ulang dari master mutable ketika GET. `description` dipakai sebagai calon definisi hanya setelah review isi, bukan otomatis disahkan sebagai teks publik.
- Period, rilis date-only, akuisisi point, akuisisi trace, dan publikasi DEKSI memiliki label terpisah. updated_at/render time bukan rilis, freshness atau sinkronisasi sukses.
- `snapshot.change` tetap null pada baseline ini: kolom trend_value/trend_percent/trend_direction belum menyimpan comparison_period, jenis unit, formula ID/versi dan binding revisi input. Warning `change_evidence_unavailable`. Fitur 6 read API tidak membuat engine atau mengevaluasi string formula. Perubahan baru dapat disajikan setelah evidence terstruktur disepakati, disimpan dan direview bersama snapshot; delta lengkap di FOUNDATION.
- Tidak mengirim narasi AI, causal explanation, diagnostic JSON internal atau angka kontribusi. `metadata.verification_status=unassessed` tanpa model evidence verifikasi; complete metadata, published, official dan origin adalah konsep berbeda.
- `metadata.status=partial` untuk field opsional yang missing; missing_fields dihitung dari proyeksi sah (nilai/unit, definisi/metodologi, sumber, tanggal/akuisisi dan source version), warnings berkode untuk change/binding/origin. Core identity, struktur periode, enum/layer dan decimal invalid bukan partial biasa: gagalkan secara aman 503. Model tidak menyimpan skala/konsep harga/base year; jangan mengarang metadata tersebut.

## 5. Public boundary dan kegagalan

View baca harus explicit AllowAny dan authentication_classes kosong khusus view supaya token/session Admin tidak diperlukan dan malformed token tidak memblokir route publik. Jangan mengubah default global accounts. Allowlist serializer; jangan expose raw_value, notes, raw formula input JSON, reviewer/email, last_fetch_message, secret atau exception. Teks sumber adalah data; URL divalidasi HTTP(S), host, tanpa userinfo/control/backslash dan tidak di-fetch oleh server. URL/institusi bukan bukti kebenaran angka.

Throttle global tetap berlaku; desain tidak menonaktifkannya. Laravel server-side bisa berbagi anonymous IP; kebijakan cache/rate perlu dibahas sebelum integrasi, bukan melewati guard dengan header IP palsu. Response awal `Cache-Control: no-store`; belum menjanjikan ETag atau immutable HTTP cache karena akses publikasi bisa berubah.

| HTTP | Situasi / error.code |
|---|---|
| 200 | Detail publik lengkap/partial; history publik atau page 1 kosong sesuai aturan |
| 400 | invalid_request / series_selection_required; parameter/frekuensi/page invalid |
| 404 | not_found untuk unknown, invalid UUID, cross-parent, nonpublic, unavailable pinned atau page lewat akhir; pesan generik sama agar draft tidak terungkap |
| 405 | method_not_allowed, tanpa mutasi |
| 429 | throttled, Retry-After bila tersedia |
| 503 | indicator_detail_unavailable untuk storage/invariant failure; ambiguous_series atau inconsistent_series bila seleksi tidak aman |

Envelope error proposal: `success:false`, `message` generik, `data:null`, `error.code`. Exception adapter perlu scoped fitur indikator dan diuji; bukan perilaku default yang sudah ada. 500 tak terantisipasi tetap error server, bukan sukses/empty/demo. Jangan mengubah error global accounts. `current` dapat mempertahankan revisi publik lama saat draft baru/fetch gagal karena storage publication selection, tetapi DB tidak dapat dibaca bukan alasan mengklaim last-valid response cache tersedia.

## 6. Gate lanjut

Batch 1 menyelesaikan rancangan untuk direview, bukan mengunci kesepakatan tim secara sepihak. **D1 pending:** shared snapshot dan delta F6/F7 pada FOUNDATION. **D2 pending:** owner/policy review serta batas immutability. **D3 pending:** database test/runtime dan perintah setup yang disetujui. Kontrak FE–BE dan target branch publikasi juga perlu review; no push tetap berlaku.

Setelah keputusan dan izin Batch 2: tes RED→model/service minimum→GREEN pada DB test, lalu serializer/query/view/URL/API tests. Integrasi Laravel adalah batch berikut; jangan menyatakan API dan database hidup dari validasi kontrak ini.
