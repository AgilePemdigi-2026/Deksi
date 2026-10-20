@props(['indicator' => null])

@php
    /**
     * Komponen kartu Ringkasan Indikator Ekonomi (Fitur 3, Sprint 1, Azka).
     * Wajib menampilkan label sumber, periode, dan satuan.
     * Sumber data: resources/data/indicators.json (baseline contoh).
     */
    $warnaSpark = match ($indicator['sparkline']['warna'] ?? 'biru') {
        'hijau' => '#157a46',
        'navy' => '#0b2545',
        default => '#2b6fc0',
    };

    $warnaBadge = match ($indicator['badge']['jenis'] ?? 'netral') {
        'naik' => 'badge-naik',
        'turun' => 'badge-naik',
        default => 'badge-netral',
    };

    // Angka gelap kecil (titik) seperti di mockup: awal, akhir, dan tiap awal tahun.
    $sparkNilai = $indicator['sparkline']['nilai'] ?? [];

    if (count($sparkNilai) >= 2) {
        $min = min($sparkNilai);
        $max = max($sparkNilai);
        $rentang = ($max - $min) ?: 1;
        $puncak = count($sparkNilai) - 1;

        $points = [];
        foreach ($sparkNilai as $i => $v) {
            $x = $puncak > 0 ? round($i / $puncak * 100, 2) : 0;
            $y = round(24 - (($v - $min) / $rentang * 20), 2);
            $points[] = [$x, $y];
        }

        $polyline = implode(' ', array_map(fn ($p) => $p[0].','.$p[1], $points));
        $area = '0,26 '.$polyline.' 100,26';

        $acuan = $indicator['sparkline']['garis_acuan'] ?? null;
        $acuanY = ($acuan !== null && count($sparkNilai) > 0)
            ? round(24 - (($acuan - $min) / $rentang * 20), 2)
            : null;
        $acuanY = ($acuanY !== null && $acuanY >= 1 && $acuanY <= 25) ? $acuanY : null;

        $panahBadge = match ($indicator['badge']['jenis'] ?? 'netral') {
            'naik' => '<svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/></svg>',
            'turun' => '<svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/></svg>',
            default => '',
        };
    }
@endphp

<article
    class="kartu-indikator flex flex-col p-5"
    data-kode="{{ $indicator['kode'] }}"
    aria-labelledby="judul-indikator-{{ $indicator['kode'] }}"
    title="Kartu data baseline contoh; ganti dengan data resmi terverifikasi.">
    <div class="flex items-start justify-between gap-3">
        <div>
            <p class="font-mono text-[10.5px] font-semibold uppercase tracking-[0.13em] text-aksen">
                {{ $indicator['kategori'] }}
            </p>
            <h3 id="judul-indikator-{{ $indicator['kode'] }}" class="mt-1 text-[17px] font-bold tracking-tight text-navy-900">
                {{ $indicator['nama'] }}
            </h3>
        </div>
        <span class="badge {{ $warnaBadge }} shrink-0">
            {!! $panahBadge ?? '' !!}{{ $indicator['badge']['label'] }}
        </span>
    </div>

    {{-- Nilai besar: monospace, dengan satuan dan periode --}}
    <div class="mt-3 flex flex-wrap items-baseline gap-2">
        <span class="font-mono text-[30px] font-bold leading-none tracking-tight text-navy-900">
            {{ $indicator['nilai'] }}
        </span>
        <span class="text-[12.5px] text-samarsekali">{{ $indicator['satuan_label'] }}</span>
    </div>

    {{-- Sparkline mini --}}
    @if (count($sparkNilai) >= 2)
        <div class="panel-spark relative mt-3 h-[74px] overflow-hidden px-2 pt-2" aria-hidden="true">
            <svg class="h-[52px] w-full" viewBox="0 0 100 28" preserveAspectRatio="none" role="presentation">
                <defs>
                    <linearGradient id="sp-{{ $indicator['kode'] }}" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="{{ $warnaSpark }}" stop-opacity="0.28" />
                        <stop offset="100%" stop-color="{{ $warnaSpark }}" stop-opacity="0.02" />
                    </linearGradient>
                </defs>
                @if ($acuanY !== null)
                    <line x1="0" y1="{{ $acuanY }}" x2="100" y2="{{ $acuanY }}"
                          stroke="{{ $warnaSpark }}" stroke-opacity="0.5" stroke-width="0.5"
                          stroke-dasharray="2.4 2.2" vector-effect="non-scaling-stroke" />
                @endif
                <polygon points="{{ $area }}" fill="url(#sp-{{ $indicator['kode'] }})" />
                <polyline points="{{ $polyline }}" fill="none" stroke="{{ $warnaSpark }}"
                          stroke-width="2" vector-effect="non-scaling-stroke"
                          stroke-linecap="round" stroke-linejoin="round" />
                @foreach ($points as $i => $p)
                    @if ($i === 0 || $i === count($points) - 1)
                        <circle cx="{{ $p[0] }}" cy="{{ $p[1] }}" r="1.6" fill="{{ $warnaSpark }}" />
                    @endif
                @endforeach
            </svg>
            <span class="spark-caption absolute bottom-1 right-2">{{ $indicator['sparkline']['caption'] }}</span>
        </div>
    @else
        <div class="panel-spark relative mt-3 flex h-[74px] items-center justify-center">
            <span class="spark-caption">Data sparkline tidak tersedia</span>
        </div>
    @endif

    {{-- Deskripsi singkat (dua baris, dipotong seperti mockup) --}}
    <p class="mt-3 line-clamp-2 text-[12.5px] leading-relaxed text-samarsekali">
        {{ $indicator['deskripsi'] }}
    </p>

    {{-- Footer: sumber, tanggal rilis, dan waktu pembaruan --}}
    <div class="mt-auto flex items-center justify-between gap-2 pt-4">
        <p class="font-mono text-[10.5px] text-samar">
            {{ $indicator['sumber'] }} &bull; Rilis: {{ $indicator['rilis'] }}
            <span class="sr-only">Waktu pembaruan: {{ $indicator['pembaruan'] }}</span>
        </p>
        {{-- Placeholder: halaman Detail Indikator milik anggota lain --}}
        <a href="#" class="flex items-center gap-1 text-[12px] font-semibold text-aksen"
           title="Lihat Detail (placeholder, fitur anggota lain)">
            Lihat Detail
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true">
                <path d="M4 12h15m0 0-5-5m5 5-5 5"/>
            </svg>
        </a>
    </div>
</article>
