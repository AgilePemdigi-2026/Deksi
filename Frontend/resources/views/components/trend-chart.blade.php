@props([
    'indikator' => null,
    'gagal' => false,
    'kosong' => false,
])

@php
    /**
     * Komponen Grafik Tren Ekonomi (Fitur 4, Sprint 1, Azka).
     * Tab pemilih indikator fungsional (bagian dari fitur ini).
     * Tab periode (Kuartalan/Bulanan/Tahunan dan 3/5/10 Tahun, Semua)
     * hanya visual: kontrol filter milik anggota lain, tidak fungsional.
     */
    $pakeTren = $indikator->filter(fn ($i) => ! empty($i['tren']))->values();

    $payload = $pakeTren->map(fn ($i) => [
        'kode' => $i['kode'],
        'judul_seri' => $i['tren']['judul_seri'],
        'unit_label' => $i['tren']['unit_label'],
        'persen' => str_contains($i['tren']['unit_label'], 'Persentase'),
        'labels' => $i['tren']['labels'],
        'values' => $i['tren']['values'],
        'titik_tekan' => $i['tren']['titik_tekan'],
        'rata_rata' => $i['tren']['rata_rata'],
        'rentang' => $i['tren']['rentang'],
        'tooltip' => $i['tren']['tooltip'],
        'aria' => 'Grafik tren '.$i['tren']['judul_seri'].', deret waktu '
            .$i['tren']['labels'][0].' sampai end('.$i['tren']['labels'][count($i['tren']['labels']) - 1].').',
    ])->all();

    $aktif = $payload[0] ?? null;
@endphp

<div class="rounded-2xl border border-pinggir bg-white p-5 shadow-sm sm:p-6"
     id="grafik-tren-ekonomi"
     data-testid="grafik-tren-ekonomi"
     data-deksi-tren="{{ @json(['seri' => $payload, 'gagal' => $gagal]) }}">

    {{-- Kepala kartu --}}
    <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
            <div class="flex items-center gap-2">
                <svg class="h-5 w-5 text-aksen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true">
                    <path d="M3 8l6 6 4-4 8 8"/><path d="M3 16l6-6 4 4 8-8"/>
                </svg>
                <h2 id="judul-tren" class="text-[20px] font-bold tracking-tight text-navy-900">Tren Ekonomi Indonesia</h2>
            </div>
            <p class="mt-1 text-[13px] text-samar">
                Analisis deret waktu historis, komparasi indikator kuartalan, dan trayektori sesaran makro.
            </p>
        </div>
        <div class="flex flex-col items-end gap-2">
            <div class="tab-dock" role="group" aria-label="Pilih indikator tren">
                @foreach ($pakeTren as $i)
                    <button type="button" data-seri="{{ $i['kode'] }}" aria-pressed="{{ $loop->first ? 'true' : 'false' }}">
                        {{ $i['nama'] }}
                    </button>
                @endforeach
            </div>
            <div class="tab-dock" role="group" aria-label="Rentang waktu (fitur filter anggota lain, tidak fungsional)">
                @foreach (['3 Tahun', '5 Tahun', '10 Tahun', 'Semua'] as $rentang)
                    <button type="button" aria-disabled="true" tabindex="-1"
                            title="Kontrol filter milik fitur lain, tidak fungsional pada Sprint 1 (Azka)">{{ $rentang }}</button>
                @endforeach
            </div>
        </div>
        <div class="tab-dock sm:hidden" role="group" aria-label="Granularitas (fitur anggota lain, tidak fungsional)">
            @foreach (['Kuartalan', 'Bulanan', 'Tahunan'] as $grp)
                <button type="button" aria-disabled="true" tabindex="-1"
                        title="Kontrol filter milik fitur lain, tidak fungsional pada Sprint 1 (Azka)">{{ $grp }}</button>
            @endforeach
        </div>
    </div>

    {{-- Baris legenda + unit + unduh --}}
    <div class="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-pinggir pt-4">
        <span class="flex items-center gap-2 font-mono text-[11px] font-semibold text-navy-800" id="leg-seri">
            <span class="h-[3px] w-5 rounded bg-garis-grafik" aria-hidden="true"></span>
            {{ $aktif['judul_seri'] ?? 'Data tren tidak tersedia' }}
        </span>
        <span class="flex items-center gap-2 font-mono text-[11px] text-samarsekali" id="leg-rata" @unless($aktif['rata_rata'] ?? false) style="display:none" @endunless>
            <span class="h-0 w-5 border-t-[2.5px] border-dashed border-samarsekali" aria-hidden="true"></span>
            {{ $aktif['rata_rata']['label'] ?? '' }}
        </span>
        <span class="flex items-center gap-2 font-mono text-[11px] text-samarsekali" id="leg-rentang" @unless($aktif['rentang'] ?? false) style="display:none" @endunless>
            <span class="h-2.5 w-5 rounded-sm bg-garis-grafik/15" aria-hidden="true"></span>
            {{ $aktif['rentang']['label'] ?? '' }}
        </span>
        <span class="ml-auto flex items-center gap-3">
            <span class="font-mono text-[10px] uppercase tracking-wide text-samar" id="leg-unit">
                {{ $aktif['unit_label'] ?? '' }}
            </span>
            <a href="#" class="flex h-8 w-8 items-center justify-center rounded-lg border border-pinggir text-aksen"
               aria-label="Unduh grafik (placeholder)" title="Unduh grafik (placeholder)">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M12 4v11m0 0 4-4m-4 4-4-4M5 20h14"/>
                </svg>
            </a>
        </span>
    </div>

    {{-- Panel kanvas + state --}}
    <div class="relative mt-4 rounded-xl border border-pinggir bg-white p-2" id="shell-grafik">
        @if ($gagal)
            <div class="flex h-[340px] flex-col items-center justify-center gap-2 text-center" role="alert">
                <svg class="h-8 w-8 text-samarsekali" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M12 9v4m0 4h.01M10.3 3.9 2.4 17a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>
                </svg>
                <p class="text-sm font-semibold text-navy-900">Gagal memuat grafik tren.</p>
                <p class="max-w-md text-[13px] text-samarsekali">
                    Data grafik tidak dapat diambil saat ini. Data valid terakhir tetap tersedia di kartu indikator.
                </p>
                <a href="{{ route('dashboard') }}" class="mt-1 rounded-lg border border-pinggir bg-white px-4 py-2 text-[13px] font-semibold text-navy-900 shadow-sm">
                    Coba Muat Ulang
                </a>
            </div>
        @else
            <div class="relative h-[340px]">
                <canvas id="canvas-tren-ekonomi" role="img"
                        aria-label="{{ $aktif['aria'] ?? 'Grafik tren tidak tersedia.' }}"></canvas>

                <div class="panel-state" id="panel-kosong" role="status">
                    <svg class="h-8 w-8 text-samarsekali" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
                    </svg>
                    <p class="text-sm font-semibold text-navy-900">Data tren tidak tersedia.</p>
                    <p class="max-w-sm text-[13px] text-samarsekali">
                        Deret waktu untuk indikator ini belum tersedia. Silakan pilih indikator lain di daftar tab di atas.
                    </p>
                </div>
            </div>
        @endif
        <div class="tooltip-grafik" id="tooltip-grafik" aria-hidden="true"></div>
    </div>

    {{-- Catatan kaki kartu grafik --}}
    <div class="mt-4 flex flex-wrap items-center justify-between gap-2 text-[12.5px]">
        <p class="text-samarsekali" id="catatan-grafik">
            Catatan: Data disajikan sesuai satuan dan periode masing-masing indikator.
        </p>
        <a href="#" class="flex items-center gap-1 font-semibold text-aksen"
           title="Buka Panel Analisis Multidimensi (placeholder, fitur anggota lain)">
            Buka Panel Analisis Multidimensi
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true">
                <path d="M14 4h6v6m0-6-8 8M11 5H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-5"/>
            </svg>
        </a>
    </div>
</div>
