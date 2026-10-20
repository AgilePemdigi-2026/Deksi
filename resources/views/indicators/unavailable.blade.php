@extends('layouts.app')

@section('judul', 'Data belum tersedia | DEKSI')

@section('content')
    <section aria-labelledby="judul-gangguan" class="kartu-indikator p-6 sm:p-10">
        <p class="font-mono text-xs font-semibold uppercase tracking-wider text-aksen">Detail Indikator</p>
        <h1 id="judul-gangguan" class="mt-3 text-2xl font-bold text-navy-900">Data indikator belum dapat dimuat</h1>
        <p role="status" class="mt-4 max-w-xl text-sm leading-relaxed text-teks">Dataset belum tersedia atau formatnya belum valid. Halaman tidak menampilkan angka pengganti. Silakan coba lagi atau kembali ke dashboard.</p>
        <div class="mt-6 flex flex-wrap gap-3">
            <a href="{{ url()->current() }}" class="rounded-lg bg-navy-900 px-4 py-3 text-sm font-semibold text-white">Coba lagi</a>
            <a href="{{ route('dashboard') }}" class="rounded-lg border border-pinggir px-4 py-3 text-sm font-semibold text-navy-900">Kembali ke dashboard</a>
        </div>
    </section>
@endsection
