<?php

use App\Http\Controllers\DashboardController;
use App\Http\Controllers\IndicatorController;
use Illuminate\Support\Facades\Route;

Route::get('/', fn () => redirect()->route('dashboard'));

Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');

Route::get('/indikator/{kode}', [IndicatorController::class, 'show'])
    ->where('kode', '[a-z0-9_]+')
    ->name('indikator.show');
