@php
    $badge = config('deksi.badge');
@endphp
<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('judul', 'Dashboard Ekonomi DEKSI')</title>
    <meta name="description" content="Ringkasan indikator ekonomi makro terbaru berdasarkan data resmi kementerian dan lembaga negara.">
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body class="min-h-screen font-sans">

    {{-- Bagian atas: pastikan sangat minimal, agar kartu dan grafik tetap fokus --}}
    <header class="sticky top-0 z-40 border-b border-pinggir bg-white/95 backdrop-blur">
        <div class="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
            <a href="{{ route('dashboard') }}" class="flex items-center gap-3" aria-label="DEKSI, kembali ke dashboard">
                <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-900 font-mono text-[13px] font-bold tracking-tight text-white">DK</span>
                <span class="leading-tight">
                    <span class="block text-[17px] font-extrabold tracking-tight text-navy-900">DEKSI</span>
                    <span class="block text-[10px] text-samar">Deteksi Ekonomi Indonesia</span>
                </span>
            </a>
            <nav class="ml-2 hidden items-center gap-1 lg:flex" aria-label="Navigasi utama">
                <a href="{{ route('dashboard') }}" aria-current="page"
                   class="flex items-center gap-2 rounded-lg border border-pinggir bg-white px-3 py-1.5 text-sm font-semibold text-navy-900 shadow-sm">
                    <span class="h-1.5 w-1.5 rounded-full bg-aksen"></span> Dashboard
                </a>
                {{-- Tautan fitur lain (placeholder, bukan lingkup Sprint 1 - Azka) --}}
                <a href="#" class="rounded-lg px-3 py-1.5 text-sm text-teks">Indikator</a>
                <a href="#" class="rounded-lg px-3 py-1.5 text-sm text-teks">Analisis</a>
                <a href="#" class="rounded-lg px-3 py-1.5 text-sm text-teks">Sumber Data</a>
                <a href="#" class="rounded-lg px-3 py-1.5 text-sm text-teks">Tentang DEKSI</a>
            </nav>
            <div class="ml-auto hidden w-64 lg:block">
                <label class="sr-only" for="pencarian-header">Cari data atau indikator</label>
                <input id="pencarian-header" type="search" disabled
                       placeholder="Cari data atau indikator..." aria-disabled="true"
                       class="w-full rounded-lg border border-transparent bg-latar px-3 py-2 text-sm placeholder-samar disabled:cursor-default">
            </div>
            <a href="#" class="flex items-center gap-2 rounded-lg border border-pinggir bg-white px-3.5 py-2 text-sm font-semibold text-navy-900 shadow-sm"
               title="Login Admin (fitur anggota lain, Sprint 1)">
                <svg class="h-4 w-4 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>
                </svg>
                Masuk
            </a>
        </div>
    </header>

    <main class="mx-auto max-w-7xl px-4 pb-16 pt-8 sm:px-6 lg:px-8">
        @yield('content')
    </main>

    <footer class="border-t border-pinggir bg-white">
        <div class="mx-auto max-w-7xl px-4 py-6 text-center text-xs text-samar sm:px-6 lg:px-8">
            <span class="font-mono">DEKSI</span> · Deteksi Ekonomi Indonesia · Data dari kementerian dan lembaga resmi
        </div>
    </footer>
</body>
</html>
