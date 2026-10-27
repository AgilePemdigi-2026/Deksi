@extends('layouts.app')

@section('title', 'Dashboard Ekonomi')
@section('meta_description', 'Dashboard indikator ekonomi Indonesia: PDB, inflasi, fiskal, moneter, investasi, dan tenaga kerja.')

@section('content')
<div class="min-h-screen bg-[#0B0F1A]">

    {{-- Ambient background --}}
    <div class="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div class="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl"></div>
        <div class="absolute bottom-1/4 right-0 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div class="absolute inset-0 opacity-[0.03]"
             style="background-image: linear-gradient(#4f6ef7 1px, transparent 1px), linear-gradient(90deg, #4f6ef7 1px, transparent 1px); background-size: 40px 40px;"></div>
    </div>

    <div class="relative z-10">

        {{-- ── Navbar ─────────────────────────────────────────────────────── --}}
        <nav class="border-b border-white/5 backdrop-blur-md bg-[#0B0F1A]/80 sticky top-0 z-20">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center">
                        <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                        </svg>
                    </div>
                    <span class="font-bold text-white text-lg tracking-tight">DEKSI</span>
                    <span class="hidden sm:inline text-slate-500 text-sm">· Deteksi Ekonomi Indonesia</span>
                </div>
                <div class="flex items-center gap-3">
                    <a href="{{ route('feedback') }}"
                       class="text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5">
                        Umpan Balik
                    </a>
                    <a href="{{ route('admin.login') }}"
                       class="text-sm text-slate-300 hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-white/10 hover:border-white/20">
                        Admin
                    </a>
                </div>
            </div>
        </nav>

        <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

            {{-- ── Header ──────────────────────────────────────────────────── --}}
            <div class="mb-8">
                <h1 class="text-2xl sm:text-3xl font-bold text-white mb-2">Dashboard Ekonomi Indonesia</h1>
                <p class="text-slate-400 text-sm" id="last-updated">Memuat data...</p>
            </div>

            {{-- ── Filter Bar ──────────────────────────────────────────────── --}}
            <div class="backdrop-blur-md bg-white/5 border border-white/10 rounded-xl p-4 mb-6">
                <div class="flex flex-col sm:flex-row gap-3 items-start sm:items-center">

                    {{-- Filter Kategori --}}
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-xs text-slate-500 font-medium uppercase tracking-wider shrink-0">Kategori:</span>
                        <div id="filter-categories" class="flex flex-wrap gap-2">
                            <button data-category=""
                                    class="filter-btn active px-3 py-1 rounded-full text-xs font-medium transition-all
                                           bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                Semua
                            </button>
                            {{-- Kategori lain akan diisi JS --}}
                        </div>
                    </div>

                    <div class="sm:ml-auto flex items-center gap-2">
                        {{-- Filter Tahun --}}
                        <select id="filter-year"
                                class="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-slate-300 text-xs
                                       focus:outline-none focus:ring-2 focus:ring-indigo-500/50 cursor-pointer">
                            <option value="">Semua Tahun</option>
                        </select>

                        {{-- Reset Filter --}}
                        <button id="btn-reset-filter"
                                class="hidden px-3 py-1.5 text-xs text-slate-400 hover:text-white border border-white/10
                                       hover:border-white/20 rounded-lg transition-all flex items-center gap-1">
                            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                            Reset
                        </button>
                    </div>
                </div>
            </div>

            {{-- ── Notifikasi data kosong / error ──────────────────────────── --}}
            <div id="notif-no-data" class="hidden mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm flex items-center gap-3">
                <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span id="notif-no-data-text">Data tidak tersedia untuk filter yang dipilih.</span>
            </div>
            <div id="notif-error" class="hidden mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm flex items-center gap-3">
                <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span id="notif-error-text">Gagal memuat data. Periksa koneksi Anda.</span>
            </div>

            {{-- ── Loading Skeleton ────────────────────────────────────────── --}}
            <div id="grid-skeleton" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                @for ($i = 0; $i < 6; $i++)
                <div class="backdrop-blur-md bg-white/5 border border-white/10 rounded-xl p-5 animate-pulse">
                    <div class="h-3 w-1/3 bg-white/10 rounded mb-3"></div>
                    <div class="h-6 w-2/3 bg-white/10 rounded mb-2"></div>
                    <div class="h-3 w-1/2 bg-white/10 rounded mb-4"></div>
                    <div class="h-8 w-1/3 bg-white/10 rounded"></div>
                </div>
                @endfor
            </div>

            {{-- ── Grid Kartu Indikator ─────────────────────────────────────── --}}
            <div id="indicator-grid" class="hidden grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>

        </main>
    </div>
</div>
@endsection

@push('scripts')
<script>
(function () {
    const BACKEND = '{{ env("VITE_BACKEND_URL", "http://127.0.0.1:8000") }}';

    // ── State ──────────────────────────────────────────────────────────────
    let activeCategory = '';
    let activeYear     = '';
    let allCategories  = [];
    const availableYears = Array.from({length: 10}, (_, i) => new Date().getFullYear() - i);

    // ── DOM refs ───────────────────────────────────────────────────────────
    const gridSkeleton    = document.getElementById('grid-skeleton');
    const indicatorGrid   = document.getElementById('indicator-grid');
    const filterCatsEl    = document.getElementById('filter-categories');
    const filterYearEl    = document.getElementById('filter-year');
    const btnReset        = document.getElementById('btn-reset-filter');
    const notifNoData     = document.getElementById('notif-no-data');
    const notifError      = document.getElementById('notif-error');
    const lastUpdatedEl   = document.getElementById('last-updated');

    // ── Populate year dropdown ─────────────────────────────────────────────
    availableYears.forEach(y => {
        const opt = document.createElement('option');
        opt.value = y; opt.textContent = y;
        filterYearEl.appendChild(opt);
    });

    // ── Category pill colors ───────────────────────────────────────────────
    const catColors = {
        pdb:          'indigo',
        inflasi:      'rose',
        fiskal:       'amber',
        moneter:      'blue',
        investasi:    'emerald',
        tenaga_kerja: 'violet',
    };
    function catStyle(code, active) {
        const c = catColors[code] || 'slate';
        return active
            ? `bg-${c}-500/20 text-${c}-300 border border-${c}-500/30`
            : `bg-white/5 text-slate-400 border border-white/10 hover:border-white/20 hover:text-slate-300`;
    }

    // ── Render kategori pills ─────────────────────────────────────────────
    function renderCategoryPills(categories) {
        filterCatsEl.innerHTML = '';
        // Pill "Semua"
        const allBtn = document.createElement('button');
        allBtn.dataset.category = '';
        allBtn.className = `filter-btn px-3 py-1 rounded-full text-xs font-medium transition-all ${catStyle('', activeCategory === '')}`;
        allBtn.textContent = 'Semua';
        filterCatsEl.appendChild(allBtn);

        categories.forEach(cat => {
            if (!cat.indicator_count) return;
            const btn = document.createElement('button');
            btn.dataset.category = cat.code;
            btn.className = `filter-btn px-3 py-1 rounded-full text-xs font-medium transition-all ${catStyle(cat.code, activeCategory === cat.code)}`;
            btn.textContent = `${cat.label} (${cat.indicator_count})`;
            filterCatsEl.appendChild(btn);
        });
    }

    // ── Trend icon ────────────────────────────────────────────────────────
    function trendIcon(direction, pct) {
        if (!direction || direction === 'stable') {
            return `<span class="text-slate-400 text-xs">→ Stabil</span>`;
        }
        const up   = direction === 'up';
        const cls  = up ? 'text-emerald-400' : 'text-red-400';
        const icon = up
            ? `<path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/>`
            : `<path stroke-linecap="round" stroke-linejoin="round" d="M13 17l5-5m0 0l-5-5m5 5H6"/>`;
        const label = pct ? `${up ? '+' : ''}${parseFloat(pct).toFixed(2)}%` : (up ? 'Naik' : 'Turun');
        return `<span class="${cls} flex items-center gap-1 text-xs">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">${icon}</svg>
            ${label}
        </span>`;
    }

    // ── Render kartu indikator ────────────────────────────────────────────
    function renderCard(ind) {
        const d    = ind.latest_data;
        const c    = catColors[ind.category] || 'slate';
        const hasData = !!d;

        const flagsHtml = (d?.diagnostic_flags || []).map(f => {
            const sev = { info: 'blue', warning: 'amber', critical: 'red' }[f.severity] || 'slate';
            return `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-${sev}-500/10 text-${sev}-400 border border-${sev}-500/20">
                ${f.flag_code}
            </span>`;
        }).join('');

        return `
        <article class="group backdrop-blur-md bg-white/5 border border-white/10 rounded-xl p-5
                        hover:border-${c}-500/30 hover:bg-white/8 transition-all duration-300 cursor-pointer"
                 data-id="${ind.id}">
            {{-- Kategori badge --}}
            <div class="flex items-start justify-between mb-3">
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium
                             bg-${c}-500/10 text-${c}-400 border border-${c}-500/20 uppercase tracking-wider">
                    ${ind.category_display}
                </span>
                ${hasData ? `<span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0 mt-1" title="Data tersedia"></span>`
                          : `<span class="w-2 h-2 rounded-full bg-slate-600 shrink-0 mt-1" title="Belum ada data"></span>`}
            </div>

            {{-- Nama indikator --}}
            <h3 class="text-sm font-semibold text-white mb-0.5 leading-snug">${ind.name}</h3>
            <p class="text-[11px] text-slate-500 mb-3">${ind.source_name || '—'}</p>

            ${hasData ? `
            {{-- Nilai utama --}}
            <div class="mb-3">
                <p class="text-2xl font-bold text-white tabular-nums">
                    ${parseFloat(d.value).toLocaleString('id-ID', {maximumFractionDigits: 2})}
                    <span class="text-xs font-normal text-slate-400 ml-1">${ind.unit}</span>
                </p>
                <p class="text-[11px] text-slate-500 mt-0.5">Periode: ${d.period_label}</p>
            </div>
            {{-- Trend --}}
            <div class="flex items-center justify-between">
                ${trendIcon(d.trend_direction, d.trend_percent)}
                <div class="flex gap-1 flex-wrap justify-end">
                    ${flagsHtml}
                </div>
            </div>
            ` : `
            <div class="py-4 text-center">
                <p class="text-xs text-slate-600">Belum ada data dipublikasikan</p>
            </div>
            `}

            {{-- Sumber --}}
            ${ind.source_name ? `<p class="text-[10px] text-slate-600 mt-3 pt-3 border-t border-white/5">Sumber: ${ind.source_name}</p>` : ''}
        </article>`;
    }

    // ── Fetch & render dashboard ──────────────────────────────────────────
    async function fetchDashboard() {
        gridSkeleton.classList.remove('hidden');
        indicatorGrid.classList.add('hidden');
        notifNoData.classList.add('hidden');
        notifError.classList.add('hidden');

        const params = new URLSearchParams();
        if (activeCategory) params.set('category', activeCategory);
        if (activeYear)     params.set('year',     activeYear);

        try {
            const res  = await fetch(`${BACKEND}/api/v1/indicators/dashboard/?${params}`);
            const json = await res.json();

            if (!res.ok) throw new Error(json.message || 'Server error');

            const { data, meta } = json;

            // Update "terakhir diperbarui"
            if (meta?.generated_at) {
                const dt = new Date(meta.generated_at);
                lastUpdatedEl.textContent = `Diperbarui: ${dt.toLocaleString('id-ID', {dateStyle:'medium', timeStyle:'short'})}`;
            }

            gridSkeleton.classList.add('hidden');
            indicatorGrid.classList.remove('hidden');

            if (!data || data.length === 0) {
                indicatorGrid.innerHTML = '';
                document.getElementById('notif-no-data-text').textContent =
                    'Tidak ada indikator untuk filter yang dipilih. Coba reset filter.';
                notifNoData.classList.remove('hidden');
                return;
            }

            const hasAnyData = data.some(d => d.latest_data);
            if (!hasAnyData) {
                document.getElementById('notif-no-data-text').textContent =
                    json.message || 'Belum ada data yang dipublikasikan untuk filter ini.';
                notifNoData.classList.remove('hidden');
            }

            indicatorGrid.innerHTML = data.map(renderCard).join('');

            // Tampilkan/sembunyikan tombol reset
            btnReset.classList.toggle('hidden', !activeCategory && !activeYear);

        } catch (err) {
            gridSkeleton.classList.add('hidden');
            indicatorGrid.innerHTML = '';
            document.getElementById('notif-error-text').textContent =
                'Gagal memuat data. ' + err.message;
            notifError.classList.remove('hidden');
        }
    }

    // ── Fetch categories untuk pills ─────────────────────────────────────
    async function fetchCategories() {
        try {
            const res  = await fetch(`${BACKEND}/api/v1/indicators/categories/`);
            const json = await res.json();
            if (json.success) {
                allCategories = json.data;
                renderCategoryPills(allCategories);
                bindCategoryEvents();
            }
        } catch {
            // Fallback: render pills statis
            renderCategoryPills([]);
            bindCategoryEvents();
        }
    }

    // ── Event: filter kategori ────────────────────────────────────────────
    function bindCategoryEvents() {
        filterCatsEl.addEventListener('click', (e) => {
            const btn = e.target.closest('.filter-btn');
            if (!btn) return;
            activeCategory = btn.dataset.category;
            renderCategoryPills(allCategories);
            bindCategoryEvents();
            fetchDashboard();
        });
    }

    // ── Event: filter tahun ───────────────────────────────────────────────
    filterYearEl.addEventListener('change', () => {
        activeYear = filterYearEl.value;
        fetchDashboard();
    });

    // ── Event: reset filter ───────────────────────────────────────────────
    btnReset.addEventListener('click', () => {
        activeCategory = '';
        activeYear     = '';
        filterYearEl.value = '';
        renderCategoryPills(allCategories);
        bindCategoryEvents();
        fetchDashboard();
    });

    // ── Init ──────────────────────────────────────────────────────────────
    fetchCategories();
    fetchDashboard();
})();
</script>
@endpush
