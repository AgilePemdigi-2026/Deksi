@extends('layouts.app')
@section('judul', 'Source Trace Data | DEKSI')
@section('body-class', 'source-trace-page')

@section('content')
@php
    $snapshot = $trace['snapshot'];
    $institution = $snapshot['sumber_lengkap'] ?? $snapshot['sumber'] ?? 'Belum tersedia';
    $typeLabel = match ($trace['data_type']) {
        'official' => 'Nilai resmi (klasifikasi demo)',
        'derived' => 'DEKSI-Derived Metric (demo)',
        default => 'Belum diklasifikasikan',
    };
    $steps = [
        ['Institusi', 'Institusi Resmi', $institution, 'Nama pada dataset contoh'],
        ['Sumber', 'Sumber Data', $trace['publication_name'] ?? 'Publikasi spesifik belum tersedia.', 'Metadata publikasi'],
        ['Rilis', 'Rilis Data', $snapshot['rilis'] ?? 'Tanggal rilis belum tersedia.', 'Tanggal dari dataset contoh'],
        ['Nilai', 'Nilai Sumber', $snapshot['nilai'] ?? 'Nilai belum tersedia.', 'Belum diverifikasi resmi'],
        ['Kalkulasi', 'Perhitungan DEKSI', $trace['formula_is_example'] ? 'Ilustrasi metode, bukan bukti kalkulasi angka ini.' : 'Bukti perhitungan belum tersedia.', 'Angka dihitung backend'],
        ['Analisis', 'Analisis', 'Hasil diagnostik dan narasi analisis belum tersedia untuk snapshot ini.', 'Tidak menghalangi akses data'],
    ];
@endphp
<nav aria-label="Breadcrumb" class="trace-breadcrumb">
    <a href="{{ route('dashboard') }}">Dashboard</a><span aria-hidden="true">›</span>
    @if ($matchesDetail)
        <a href="{{ route('indikator.show', ['kode' => $trace['indicator_code']]) }}">Detail Indikator</a><span aria-hidden="true">›</span>
    @endif
    <span aria-current="page">Source Trace Data</span>
</nav>

<header class="trace-panel trace-heading">
    <span class="trace-badge trace-badge-dark">Keterlacakan Data</span>
    <h1>Source Trace Data</h1>
    <p>Pelacakan asal angka, publikasi sumber, dan metode perhitungan untuk memahami dasar data ekonomi yang ditampilkan.</p>
    <aside class="trace-demo" role="note"><strong>Data demo, belum diverifikasi sebagai data resmi.</strong> Metadata ini mengikuti dataset contoh frontend, bukan hasil sinkronisasi atau review publikasi. Angka dan tanggal tidak menunjukkan pembaruan terbaru.</aside>
</header>

@if (! $matchesDetail)
    <aside class="trace-warning" role="note">Snapshot ini tidak cocok dengan detail indikator saat ini. Konteks lama tetap ditampilkan; tautan kembali ke detail dinonaktifkan agar periode atau angka tidak tertukar.</aside>
@endif

<section class="trace-summary" aria-label="Ringkasan sumber data">
    <div class="trace-panel"><h2>Indikator Terpilih</h2><p class="trace-summary-value">{{ $snapshot['nama'] ?? 'Belum tersedia' }}</p><p class="trace-accent">{{ $snapshot['satuan_label'] ?? $snapshot['periode'] ?? 'Periode belum tersedia' }}</p></div>
    <div class="trace-panel"><h2>Nilai pada Dataset Contoh</h2><p class="trace-metric">{{ $snapshot['nilai'] ?? 'Belum tersedia' }}</p><p>{{ $snapshot['periode'] ?? 'Periode belum tersedia' }}</p></div>
    <div class="trace-panel"><h2>Tipe Kalkulasi</h2><p class="trace-summary-value">{{ $typeLabel }}</p><p>Tidak ditentukan dari bentuk angka</p></div>
    <div class="trace-panel"><h2>Institusi Sumber</h2><p class="trace-summary-value">{{ $snapshot['sumber'] ?? 'Belum tersedia' }}</p><p>{{ $institution }}</p></div>
    <div class="trace-panel"><h2>Status Validasi</h2><p class="trace-summary-value">Belum Terverifikasi</p><p class="trace-accent">Dataset demonstrasi</p></div>
</section>

<section class="trace-panel" aria-labelledby="trace-pipeline">
    <div class="trace-section-heading"><div><h2 id="trace-pipeline">Alur Rantai Data (Source Trace)</h2><p>Penjelasan tahapan keterlacakan, bukan bukti semua tahap sudah dijalankan.</p></div><span class="trace-badge">Ilustrasi Alur</span></div>
    <ol class="trace-pipeline">
        @foreach ($steps as $step)
            <li class="trace-step {{ $loop->last ? 'trace-step-dark' : '' }}">
                <span class="trace-step-label">{{ str_pad((string) $loop->iteration, 2, '0', STR_PAD_LEFT) }}. {{ $step[0] }}</span>
                <h3>{{ $step[1] }}</h3><p>{{ $step[2] }}</p><span class="trace-step-caption">{{ $step[3] }}</span>
            </li>
        @endforeach
    </ol>
</section>

<div class="trace-columns">
    <section class="trace-panel trace-calculation" aria-labelledby="trace-formula">
        <div><h2 id="trace-formula">Komponen Perhitungan &amp; Formula Matematika</h2><p class="trace-description">Frontend menampilkan metode yang disediakan, bukan menghitung ulang nilai ekonomi atau membuktikan status resmi.</p></div>
        @if ($trace['data_type'] === 'official')
            <div class="trace-soft"><h3>Nilai resmi dari sumber</h3><p>Formula internal DEKSI tidak berlaku untuk nilai ini. Klasifikasi pada dataset demo belum membuktikan nilai sudah diverifikasi.</p></div>
        @elseif ($trace['formula_expression'] !== null)
            <div class="trace-soft">
                <div class="trace-section-heading"><span class="trace-label">{{ $trace['formula_id'] ?? 'ID formula belum tersedia' }}</span><span class="trace-badge">{{ $trace['formula_is_example'] ? 'Ilustrasi Metode' : 'Metadata Demo' }}</span></div>
                <div class="trace-formula" aria-label="{{ $trace['formula_expression'] }}">
                    @if ($trace['formula_id'] === 'GDP_YOY_ADHK' && $trace['formula_is_example'])
                        <span aria-hidden="true">YoY<sub>t</sub> =</span><span class="trace-fraction" aria-hidden="true"><span>PDB<sub>t</sub> − PDB<sub>t−4</sub></span><span>PDB<sub>t−4</sub></span></span><span aria-hidden="true">× 100%</span>
                    @else
                        <span>{{ $trace['formula_expression'] }}</span>
                    @endif
                </div>
                <p class="trace-small">Versi formula: {{ $trace['formula_version'] ?? 'Belum tersedia' }}.</p>
                @if ($trace['formula_is_example'])
                    <p class="trace-small">Contoh formula pertumbuhan YoY untuk PDB ADHK triwulanan. Input resmi dan hasil backend belum tersedia; formula ini tidak membuktikan nilai contoh di atas telah dihitung.</p>
                @endif
            </div>
        @else
            <div class="trace-soft"><h3>Formula belum tersedia</h3><p>{{ $trace['data_type'] === 'derived' ? 'Keterlacakan belum lengkap: formula dan input backend belum tersedia.' : 'Jenis nilai belum diklasifikasikan. Formula tidak ditebak dari nama indikator.' }}</p></div>
        @endif

        @if ($trace['data_type'] !== 'official')
        <div><h3>Tabel Parameter Input Deterministik</h3>
            <div class="trace-table-scroll" role="region" aria-label="Tabel parameter input, geser horizontal bila diperlukan" tabindex="0">
                <table class="trace-table"><caption class="sr-only">Parameter input yang tersedia pada metadata demo</caption><thead><tr><th scope="col">Parameter</th><th scope="col">Periode Referensi</th><th scope="col">Nilai / Satuan</th><th scope="col">Sumber</th></tr></thead><tbody>
                @forelse ($trace['inputs'] as $input)
                    <tr><th scope="row">{{ $input['parameter'] ?? 'Belum tersedia' }}</th><td>{{ $input['period'] ?? 'Belum tersedia' }}</td><td>{{ $input['value'] ?? 'Belum tersedia' }}@if ($input['unit'] !== null)<br>{{ $input['unit'] }}@endif</td><td>{{ $input['source'] ?? 'Belum tersedia' }}</td></tr>
                @empty
                    <tr><td colspan="4">Input formula belum tersedia. Data hilang bukan nol.</td></tr>
                @endforelse
                <tr class="trace-result"><th scope="row" colspan="2">Hasil kalkulasi backend</th><td colspan="2">Belum tersedia</td></tr>
                </tbody></table>
            </div>
        </div>
        @endif
        <aside class="trace-soft" role="note"><h3>Catatan Keterlacakan</h3><p>Nama institusi dan tautan sumber bukan bukti angka sudah diverifikasi. Nilai resmi, metrik turunan, interpretasi diagnostik, dan narasi AI memiliki peran berbeda.</p></aside>
    </section>

    <aside class="trace-metadata" aria-label="Metadata dan transparansi sumber">
        <section class="trace-panel" aria-labelledby="trace-metadata-title">
            <div class="trace-section-heading"><h2 id="trace-metadata-title">Metadata Rilis &amp; Verifikasi</h2><span class="trace-badge">Demo</span></div>
            <dl class="trace-metadata-list">
                <div><dt>Dokumen Sumber Primer</dt><dd>{{ $trace['publication_name'] ?? 'Publikasi spesifik belum tersedia' }}
                    @if ($trace['publication_url'] !== null)<a class="trace-link" href="{{ $trace['publication_url'] }}" target="_blank" rel="noopener noreferrer">Buka publikasi resmi <span aria-hidden="true">↗</span><span class="sr-only"> (tab baru)</span></a>@else<span class="trace-small">Tautan publikasi belum tersedia atau tidak valid.</span>@endif
                </dd></div>
                <div><dt>Periode Observasi</dt><dd>{{ $snapshot['periode'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt>Satuan</dt><dd>{{ $snapshot['satuan'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt>Rilis pada Dataset Contoh</dt><dd>{{ $snapshot['rilis'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt>Waktu Pengambilan Data</dt><dd>{{ $trace['fetched_at'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt>Versi Snapshot Demo</dt><dd>{{ $trace['version'] }}</dd></div>
            </dl>
            <h3 class="trace-label">Referensi Rilis Lembaga Resmi</h3>
            <ul class="trace-references">
                @forelse ($trace['references'] as $reference)
                    <li>@if ($reference['url'] !== null)<a href="{{ $reference['url'] }}" target="_blank" rel="noopener noreferrer">{{ $reference['title'] ?? 'Publikasi sumber' }} <span aria-hidden="true">↗</span><span class="sr-only"> (tab baru)</span></a>@else<span>{{ $reference['title'] ?? 'Referensi' }}: tautan belum tersedia atau tidak valid.</span>@endif</li>
                @empty
                    <li>Referensi publikasi spesifik belum tersedia. Tidak ada tautan sumber yang direka.</li>
                @endforelse
            </ul>
        </section>
        <section class="trace-transparency" aria-labelledby="trace-transparency-title"><h2 id="trace-transparency-title">Transparansi Data</h2><p>Metadata masih parsial dan berstatus demo. Tidak ada klaim verifikasi resmi, tanda tangan kriptografis, atau persetujuan publikasi.</p></section>
    </aside>
</div>

<section class="trace-panel" aria-labelledby="trace-revisions">
    <div class="trace-section-heading"><div><h2 id="trace-revisions">Riwayat Pembaruan Data</h2><p>Jejak revisi hanya ditampilkan jika tersedia pada metadata.</p></div><span class="trace-badge">{{ count($trace['revisions']) }} entri demo</span></div>
    <div class="trace-table-scroll" role="region" aria-label="Riwayat pembaruan, geser horizontal bila diperlukan" tabindex="0">
        <table class="trace-table"><caption class="sr-only">Riwayat revisi snapshot data</caption><thead><tr><th scope="col">Waktu</th><th scope="col">Tipe Entri</th><th scope="col">Nilai Tercatat</th><th scope="col">Keterangan Pembaruan</th></tr></thead><tbody>
            @forelse ($trace['revisions'] as $revision)
                <tr><td>{{ $revision['timestamp'] ?? 'Belum tersedia' }}</td><td>{{ $revision['type'] ?? 'Belum tersedia' }}</td><td>{{ $revision['value'] ?? 'Belum tersedia' }}</td><td>{{ $revision['note'] ?? 'Belum tersedia' }}</td></tr>
            @empty
                <tr><td colspan="4">Riwayat revisi belum tersedia. Tidak ada perubahan atau versi resmi yang direka.</td></tr>
            @endforelse
        </tbody></table>
    </div>
</section>
<div class="trace-bottom-nav">@if ($matchesDetail)<a class="trace-link" href="{{ route('indikator.show', ['kode' => $trace['indicator_code']]) }}">← Kembali ke Detail Indikator</a>@else<a class="trace-link" href="{{ route('dashboard') }}">← Kembali ke Dashboard</a>@endif</div>
@endsection

@section('footer')
<div class="trace-footer-inner">
    <div><h2>DEKSI · Deteksi Ekonomi Indonesia</h2><p>Platform analisis dan edukasi ekonomi dengan keterlacakan sumber. Pembaruan mengikuti ketersediaan dan jadwal rilis resmi, bukan klaim real-time.</p></div>
    <div><h2>Konteks Sumber</h2><p>Institusi dan publikasi mengikuti metadata setiap angka. Halaman ini masih menggunakan data demo.</p></div>
    <div><h2>Akses Publik</h2><a href="{{ route('dashboard') }}">Dashboard Ekonomi</a>@if ($matchesDetail)<a href="{{ route('indikator.show', ['kode' => $trace['indicator_code']]) }}">Detail Indikator</a>@endif</div>
</div>
@endsection
