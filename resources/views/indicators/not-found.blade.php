@extends('layouts.app')

@section('judul', 'Indikator tidak ditemukan | DEKSI')

@section('content')
    <section aria-labelledby="judul-tidak-ditemukan" class="kartu-indikator p-6 sm:p-10">
        <p class="font-mono text-xs font-semibold text-aksen">404 · Detail Indikator</p>
        <h1 id="judul-tidak-ditemukan" class="mt-3 text-2xl font-bold text-navy-900">Indikator tidak ditemukan</h1>
        <p class="mt-4 max-w-xl text-sm leading-relaxed text-teks">Kode indikator tidak tersedia pada dataset ini. Halaman tidak menggantinya dengan angka indikator lain.</p>
        <a href="{{ route('dashboard') }}" class="mt-6 inline-block rounded-lg bg-navy-900 px-4 py-3 text-sm font-semibold text-white">Kembali ke dashboard</a>
    </section>
@endsection
