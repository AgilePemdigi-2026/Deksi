@extends('layouts.app')

@section('judul', 'Dashboard Ekonomi DEKSI')

@section('content')
    {{-- ================================================================
         HERO DASHBOARD
         ================================================================ --}}
    <section aria-labelledby="judul-halaman">
        <p class="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-navy-900">
            Platform Data &amp; Analisis Ekonomi
            <span class="text-aksen">&bull; Data dari Kementerian &amp; Lembaga Resmi</span>
        </p>
        <h1 id="judul-halaman" class="mt-2 text-3xl font-extrabold tracking-tight text-navy-900 sm:text-4xl lg:text-[40px]">
            Kondisi Ekonomi Indonesia
        </h1>
        <p class="mt-3 max-w-2xl text-[15px] leading-relaxed text-teks">
            Ringkasan indikator ekonomi makro terbaru berdasarkan data resmi kementerian dan lembaga negara
            yang diverifikasi secara berkala.
        </p>

        <div class="mt-6 flex flex-wrap items-center gap-3">
            <p class="chip-status">
                <svg class="h-4 w-4 text-samarsekali" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M4 6h16M4 12h16M4 18h16M6 4l-2 2 2 2M18 16l2 2-2 2M6 20l-2-2 2-2"/>
                </svg>
                <span>Terakhir diperbarui: <span class="nilai">{{ $global['terakhir_diperbarui'] ?? '-' }}</span></span>
            </p>
            <p class="chip-status">
                <svg class="h-4 w-4 text-samarsekali" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>
                </svg>
                <span>Periode Analisis: <span class="nilai">{{ $global['periode_analisis'] ?? '-' }}</span></span>
            </p>
            <p class="chip-status ml-auto border-badge-naik-border [--tw-bg-opacity:1] bg-[#eaf6ef] text-badge-naik-text max-sm:ml-0">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 2.5 2.5 5-5.5"/>
                </svg>
                <span class="font-mono text-[12px] font-semibold">Sumber Terverifikasi: {{ implode(' &bull; ', $global['sumber_terverifikasi'] ?? []) }}</span>
            </p>
        </div>
    </section>

    {{-- ================================================================
         SLOT: Blok "Ikhtisar Makroekonomi" + panel Insight ringkas
         (di luar lingkup Sprint 1 - Azka; diserahkan kepada anggota lain)
         ================================================================ --}}
    <section aria-label="Blok ikhtisar makroekonomi" class="mt-10">
        <div class="rounded-2xl border-2 border-dashed border-pinggir bg-white/70 px-6 py-10 text-center">
            <p class="font-mono text-xs uppercase tracking-widest text-samar">Slot: Ikhtisar Makroekonomi</p>
            <p class="mt-1 text-sm text-samar">Blok ini milik fitur lain dan akan diintegrasikan pada penggabungan tim.</p>
        </div>
    </section>

    {{-- ================================================================
         INDIKATOR EKONOMI UTAMA (Sprint 1 - Azka: Fitur 3)
         ================================================================ --}}
    <section aria-labelledby="judul-indikator" class="mt-12">
        <div class="flex flex-wrap items-end justify-between gap-2">
            <div>
                <h2 id="judul-indikator" class="text-[22px] font-bold tracking-tight text-navy-900">Indikator Ekonomi Utama</h2>
                <p class="mt-0.5 text-[13px] text-samar">Metrik fundamental makroekonomi terkini dengan pembaruan otomatis</p>
            </div>
            <a href="#" class="flex items-center gap-1.5 text-[13px] font-semibold text-aksen" title="Tautan placeholder (fitur sinkronisasi bukan lingkup Sprint 1 - Azka)">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M9 3a6 6 0 0 1 11.6 2.2M15 21a6 6 0 0 1-11.6-2.2M3 9h6V3m12 12h-6v6"/>
                </svg>
                Sinkronisasi API Resmi
            </a>
        </div>

        <ul class="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3" id="daftar-indikator">
            @forelse ($indikator as $item)
                <x-indicator-card :indicator="$item" />
            @empty
                <li class="rounded-2xl border border-pinggir bg-white p-8 text-center text-sm text-samar md:col-span-2 xl:col-span-3">
                    Data indikator belum tersedia.
                </li>
            @endforelse
        </ul>
    </section>

    {{-- ================================================================
         TREN EKONOMI INDONESIA (Sprint 1 - Azka: Fitur 4)
         ================================================================ --}}
    <section aria-labelledby="judul-tren" class="mt-12">
        <x-trend-chart
            :indikator="$indikator"
            :gagal="$grafikGagal"
            :kosong="$grafikKosong"
        />
    </section>

    {{-- ================================================================
         SLOT: Blok "Insight Utama" dan "Transparansi & Provenance"
         (di luar lingkup Sprint 1 - Azka)
         ================================================================ --}}
    <section aria-label="Blok insight utama dan transparansi" class="mt-12 space-y-6">
        <div class="rounded-2xl border-2 border-dashed border-pinggir bg-white/70 px-6 py-10 text-center">
            <p class="font-mono text-xs uppercase tracking-widest text-samar">Slot: Insight Utama</p>
            <p class="mt-1 text-sm text-samar">Blok ini milik fitur lain dan akan diintegrasikan pada penggabungan tim.</p>
        </div>
        <div class="rounded-2xl border-2 border-dashed border-pinggir bg-white/70 px-6 py-10 text-center">
            <p class="font-mono text-xs uppercase tracking-widest text-samar">Slot: Transparansi &amp; Provenance</p>
            <p class="mt-1 text-sm text-samar">Blok ini milik fitur lain dan akan diintegrasikan pada penggabungan tim.</p>
        </div>
    </section>
@endsection
