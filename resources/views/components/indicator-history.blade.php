@props(['history'])

<section aria-labelledby="judul-histori" class="kartu-indikator p-5 sm:p-7">
    <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
            <h2 id="judul-histori" class="text-xl font-bold text-navy-900">{{ $history['title'] }}</h2>
            <p class="mt-1 text-sm text-teks">{{ $history['unit'] ?? 'Satuan deret belum tersedia' }}</p>
        </div>
        <span class="badge badge-netral">Deret contoh</span>
    </div>

    @if ($history['invalid'])
        <p role="status" class="mt-6 rounded-lg bg-amber-50 p-4 text-sm text-amber-950">Format deret belum konsisten. Grafik tidak ditampilkan agar periode dan angka tidak tertukar.</p>
    @elseif ($history['segments'] === [])
        <p role="status" class="mt-6 rounded-lg bg-spark p-6 text-sm text-teks">Data tren belum tersedia. Nilai kosong tidak dianggap nol.</p>
    @else
        <figure class="mt-6">
            <svg class="block w-full" viewBox="0 0 800 250" role="img" aria-labelledby="grafik-judul grafik-deskripsi">
                <title id="grafik-judul">{{ $history['title'] }}</title>
                <desc id="grafik-deskripsi">Visualisasi dataset contoh. Titik kosong memutus garis. Angka setiap periode tersedia pada tabel Data historis di bawah grafik.</desc>
                <line x1="60" y1="36" x2="750" y2="36" stroke="#e3eaf3" />
                <line x1="60" y1="121" x2="750" y2="121" stroke="#e3eaf3" />
                <line x1="60" y1="206" x2="750" y2="206" stroke="#64748b" />
                <text x="50" y="31" text-anchor="end" fill="#475569" font-size="12">{{ number_format($history['max'], 2, ',', '.') }}</text>
                @if ($history['min'] !== $history['max'])
                    <text x="50" y="221" text-anchor="end" fill="#475569" font-size="12">{{ number_format($history['min'], 2, ',', '.') }}</text>
                @endif
                @foreach ($history['segments'] as $segment)
                    <polyline data-history-segment points="{{ $segment }}" fill="none" stroke="#2b6fc0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
                @endforeach
                @foreach ($history['rows'] as $row)
                    @if ($row['y'] !== null)
                        <circle cx="{{ $row['x'] }}" cy="{{ $row['y'] }}" r="3" fill="#1b5ebf"><title>{{ $row['period'] }}: {{ number_format($row['value'], 2, ',', '.') }}</title></circle>
                    @endif
                @endforeach
                <text x="60" y="242" fill="#475569" font-size="12">{{ $history['rows'][0]['period'] }}</text>
                <text x="750" y="242" text-anchor="end" fill="#475569" font-size="12">{{ $history['rows'][count($history['rows']) - 1]['period'] }}</text>
            </svg>
            <figcaption class="mt-2 text-xs leading-relaxed text-teks">Grafik mempertahankan urutan periode dataset. Titik kosong tidak diinterpolasi. Buka tabel untuk nilai lengkap dan akses tanpa grafik.</figcaption>
        </figure>
    @endif

    <details class="mt-6 border-t border-pinggir pt-4" @if ($history['segments'] === []) open @endif>
        <summary class="cursor-pointer rounded py-2 text-sm font-semibold text-aksen">Data historis</summary>
        <div class="mt-3 overflow-x-auto rounded-lg border border-pinggir" tabindex="0" role="region" aria-label="Tabel data historis">
            <table class="w-full text-left text-sm">
                <caption class="sr-only">Data historis {{ $history['title'] }}. Satuan: {{ $history['unit'] ?? 'belum tersedia' }}. Dataset contoh.</caption>
                <thead class="bg-spark text-navy-900"><tr><th scope="col" class="px-4 py-3">Periode</th><th scope="col" class="px-4 py-3 text-right">Nilai</th></tr></thead>
                <tbody class="divide-y divide-pinggir">
                    @forelse ($history['rows'] as $row)
                        <tr><th scope="row" class="px-4 py-3 font-medium text-navy-900">{{ $row['period'] }}</th><td class="px-4 py-3 text-right font-mono text-teks">{{ $row['value'] === null ? 'Belum tersedia' : number_format($row['value'], 2, ',', '.') }}</td></tr>
                    @empty
                        <tr><td colspan="2" class="px-4 py-5 text-teks">Belum ada deret yang dapat ditampilkan.</td></tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </details>
</section>
