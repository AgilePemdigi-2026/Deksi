@extends('layouts.app')
@section('judul', 'Source Trace | DEKSI')
@section('body-class', 'source-trace-page')
@section('content')
<section class="trace-panel trace-state" aria-labelledby="trace-state-title">
    <span class="trace-badge">Source Trace</span>
    <h1 id="trace-state-title">{{ $unavailable ? 'Source Trace belum dapat dimuat' : 'Source Trace tidak ditemukan' }}</h1>
    <p>{{ $unavailable ? 'Terjadi masalah saat membaca metadata. Angka pada halaman lain tidak diubah. Silakan coba lagi.' : 'Identitas sumber dan indikator tidak cocok atau snapshot tersebut belum tersedia. Tidak ada sumber pengganti yang dipilih otomatis.' }}</p>
    <div class="trace-state-actions">
        @if ($unavailable)<a class="trace-link" href="{{ request()->url() }}">Coba lagi</a>@endif
        <a class="trace-link" href="{{ route('dashboard') }}">Kembali ke Dashboard</a>
    </div>
</section>
@endsection
