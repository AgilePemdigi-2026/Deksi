@extends('layouts.app')

@section('judul', ($indicator['nama'] ?? 'Detail Indikator').' | DEKSI')

@section('content')
    <nav aria-label="Breadcrumb" class="mb-6 text-sm text-teks">
        <a href="{{ route('dashboard') }}" class="font-semibold text-aksen">Dashboard</a>
        <span aria-hidden="true" class="mx-2">/</span>
        <span aria-current="page">Detail Indikator</span>
    </nav>

    <aside role="note" class="mb-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        <strong>Data demo, belum diverifikasi sebagai data resmi.</strong>
        Halaman ini memakai dataset contoh frontend. Angka dan tanggal bukan hasil sinkronisasi terbaru.
    </aside>

    <header class="mb-8">
        <p class="font-mono text-xs font-semibold uppercase tracking-wider text-aksen">Detail Indikator Ekonomi</p>
        <h1 class="mt-2 text-3xl font-extrabold tracking-tight text-navy-900 sm:text-4xl">{{ $indicator['nama'] ?? 'Indikator ekonomi' }}</h1>
        <p class="mt-3 text-sm text-teks">{{ $indicator['kategori'] ?? 'Kategori belum tersedia' }}</p>
    </header>

    <div class="grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
    <div class="min-w-0 space-y-6">
    <section aria-labelledby="nilai-utama" class="kartu-indikator p-6 sm:p-8">
        <h2 id="nilai-utama" class="text-sm font-semibold text-teks">Nilai pada dataset contoh</h2>
        <p class="mt-3 break-words font-mono text-4xl font-bold tracking-tight text-navy-900">{{ $indicator['nilai'] ?? 'Belum tersedia' }}</p>
        <p class="mt-2 text-sm text-teks">{{ $indicator['satuan_label'] ?? 'Satuan belum tersedia' }}</p>
        <dl class="mt-6 grid gap-4 border-t border-pinggir pt-5 sm:grid-cols-2">
            <div><dt class="text-xs text-teks">Periode observasi</dt><dd class="mt-1 font-semibold text-navy-900">{{ $indicator['periode'] ?? 'Belum tersedia' }}</dd></div>
            <div><dt class="text-xs text-teks">Satuan</dt><dd class="mt-1 text-sm text-navy-900">{{ $indicator['satuan'] ?? 'Belum tersedia' }}</dd></div>
        </dl>
        <div class="mt-5 rounded-lg bg-spark p-4 text-sm leading-relaxed text-teks">
            <h3 class="font-semibold text-navy-900">Perubahan dan pembanding</h3>
            <p class="mt-1">Perubahan terverifikasi belum tersedia. Badge perubahan pada dataset contoh tidak digunakan sebagai hasil perhitungan.</p>
        </div>
    </section>

    <x-indicator-history :history="$history" />

    <section aria-labelledby="tentang-indikator" class="kartu-indikator p-5 sm:p-7">
        <h2 id="tentang-indikator" class="text-xl font-bold text-navy-900">Memahami indikator</h2>
        <p class="mt-3 text-sm leading-relaxed text-teks">{{ $indicator['definisi'] ?? 'Definisi rinci belum tersedia dalam dataset. Penjelasan khusus indikator akan ditampilkan setelah metadata tervalidasi tersedia.' }}</p>
        <div class="mt-5 border-t border-pinggir pt-5">
            <h3 class="text-sm font-semibold text-navy-900">Batas interpretasi</h3>
            <p class="mt-2 text-sm leading-relaxed text-teks">Angka naik atau turun tidak otomatis menunjukkan kondisi baik atau buruk. Data pada halaman ini belum cukup untuk menyimpulkan penyebab perubahan. Rincian komponen dan kontribusi belum tersedia.</p>
        </div>
    </section>
    </div>

    <aside aria-label="Konteks dan ketersediaan data" class="min-w-0 space-y-6">
        <section aria-labelledby="konteks-data" class="kartu-indikator p-5 sm:p-6">
            <h2 id="konteks-data" class="text-lg font-bold text-navy-900">Konteks data</h2>
            <dl class="mt-5 space-y-5 text-sm">
                <div><dt class="text-xs text-teks">Institusi yang dicantumkan dalam contoh</dt><dd class="mt-1 break-words font-semibold text-navy-900">{{ $indicator['sumber_lengkap'] ?? $indicator['sumber'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt class="text-xs text-teks">Rilis pada dataset contoh</dt><dd class="mt-1 text-navy-900">{{ $indicator['rilis'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt class="text-xs text-teks">Pembaruan yang dicatat pada contoh</dt><dd class="mt-1 text-navy-900">{{ $indicator['pembaruan'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt class="text-xs text-teks">Frekuensi</dt><dd class="mt-1 text-navy-900">{{ $indicator['frekuensi'] ?? 'Belum tersedia' }}</dd></div>
                <div><dt class="text-xs text-teks">Jenis nilai dan versi rilis resmi</dt><dd class="mt-1 text-navy-900">Belum diklasifikasikan dan diverifikasi</dd></div>
            </dl>
            <p class="mt-5 border-t border-pinggir pt-4 text-xs leading-relaxed text-teks">Tanggal observasi, rilis, dan pengambilan data adalah hal berbeda. Waktu pengambilan sumber resmi belum tersedia.</p>
        </section>

        <section aria-labelledby="penelusuran" class="kartu-indikator p-5 sm:p-6">
            <h2 id="penelusuran" class="text-lg font-bold text-navy-900">Transparansi dan sumber</h2>
            @if ($sourceTrace !== null)
                <p class="mt-3 text-sm leading-relaxed text-teks">Telusuri metadata sumber untuk indikator, periode, dan snapshot demo yang sama. Metadata resmi masih parsial.</p>
                <a href="{{ route('indikator.source-trace', ['kode' => $indicator['kode'], 'trace' => $sourceTrace['id']]) }}" class="mt-4 inline-block rounded border border-pinggir px-4 py-2 text-sm font-semibold text-aksen">Lihat Sumber Data →</a>
                <p class="mt-3 text-xs leading-relaxed text-teks">Versi {{ $sourceTrace['version'] }}. Nama institusi saja bukan bukti angka sudah diverifikasi.</p>
            @else
                <p class="mt-3 text-sm leading-relaxed text-teks">Source Trace untuk snapshot ini belum tersedia atau tidak cocok. Tautan tidak diaktifkan agar angka dan provenance tidak tertukar.</p>
            @endif
        </section>

        <section aria-labelledby="analisis" class="kartu-indikator p-5 sm:p-6">
            <h2 id="analisis" class="text-lg font-bold text-navy-900">Penjelasan analisis</h2>
            <p class="mt-3 text-sm leading-relaxed text-teks">Narasi Grounded AI belum tersedia untuk dataset ini. Nilai dan tabel tetap dapat dibaca tanpa layanan AI.</p>
        </section>
    </aside>
    </div>
@endsection
