<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| DEKSI Web Routes
|--------------------------------------------------------------------------
*/

// Halaman publik
Route::get('/', function () {
    return view('welcome');
})->name('home');

// Fitur 1: Login Admin
Route::get('/admin/login', fn() => view('admin.login'))->name('admin.login');

// Fitur 2: Lupa & Reset Password
Route::get('/admin/forgot-password', fn() => view('admin.forgot-password'))->name('admin.forgot-password');
Route::get('/admin/reset-password', fn() => view('admin.reset-password'))->name('admin.reset-password');

// Fitur 5: Dashboard (dengan filter)
Route::get('/dashboard', fn() => view('dashboard.index'))->name('dashboard');

// Fitur 8: Umpan Balik
Route::get('/feedback', fn() => view('feedback.index'))->name('feedback');
