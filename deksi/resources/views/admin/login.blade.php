@extends('layouts.app')

@section('title', 'Login Admin')
@section('meta_description', 'Halaman login untuk administrator DEKSI.')

@section('content')
<div class="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#0B0F1A]">

    {{-- Ambient background blobs --}}
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
        <div class="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl animate-pulse"></div>
        <div class="absolute top-1/2 -right-32 w-80 h-80 bg-blue-500/15 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div class="absolute -bottom-32 left-1/3 w-72 h-72 bg-violet-600/15 rounded-full blur-3xl animate-pulse delay-500"></div>
        {{-- Grid overlay --}}
        <div class="absolute inset-0 opacity-5"
             style="background-image: linear-gradient(#4f6ef7 1px, transparent 1px), linear-gradient(90deg, #4f6ef7 1px, transparent 1px); background-size: 40px 40px;"></div>
    </div>

    <div class="relative w-full max-w-md mx-auto px-4 py-8">

        {{-- Logo + Brand --}}
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg shadow-indigo-500/30 mb-4">
                <svg class="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
            </div>
            <h1 class="text-2xl font-bold text-white tracking-tight">DEKSI</h1>
            <p class="text-sm text-slate-400 mt-1">Deteksi Ekonomi Indonesia</p>
        </div>

        {{-- Login Card (Glassmorphism) --}}
        <div class="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl shadow-black/40 p-8">
            <h2 class="text-lg font-semibold text-white mb-1">Masuk ke Panel Admin</h2>
            <p class="text-sm text-slate-400 mb-6">Masukkan kredensial Anda untuk melanjutkan.</p>

            {{-- Alert Error --}}
            <div id="alert-error"
                 class="hidden mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm flex items-start gap-2">
                <svg class="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span id="alert-error-text"></span>
            </div>

            {{-- Form Login --}}
            <form id="form-login" novalidate>
                @csrf

                {{-- Email --}}
                <div class="mb-4">
                    <label for="email" class="block text-sm font-medium text-slate-300 mb-1.5">
                        Email
                    </label>
                    <input
                        type="email"
                        id="email"
                        name="email"
                        placeholder="admin@deksi.id"
                        autocomplete="email"
                        required
                        class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500
                               text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50
                               transition-all duration-200"
                    >
                    <p id="email-error" class="hidden text-xs text-red-400 mt-1"></p>
                </div>

                {{-- Password --}}
                <div class="mb-6">
                    <div class="flex items-center justify-between mb-1.5">
                        <label for="password" class="block text-sm font-medium text-slate-300">
                            Kata Sandi
                        </label>
                        <a href="{{ route('admin.forgot-password') }}"
                           class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                            Lupa kata sandi?
                        </a>
                    </div>
                    <div class="relative">
                        <input
                            type="password"
                            id="password"
                            name="password"
                            placeholder="••••••••"
                            autocomplete="current-password"
                            required
                            class="w-full px-4 py-2.5 pr-10 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500
                                   text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50
                                   transition-all duration-200"
                        >
                        {{-- Toggle password visibility --}}
                        <button type="button" id="toggle-password"
                                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                            <svg id="icon-eye" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                            <svg id="icon-eye-off" class="w-4 h-4 hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                            </svg>
                        </button>
                    </div>
                    <p id="password-error" class="hidden text-xs text-red-400 mt-1"></p>
                </div>

                {{-- Submit Button --}}
                <button
                    type="submit"
                    id="btn-login"
                    class="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-blue-600
                           hover:from-indigo-500 hover:to-blue-500
                           text-white font-semibold rounded-lg text-sm
                           shadow-lg shadow-indigo-500/25
                           transition-all duration-200
                           focus:outline-none focus:ring-2 focus:ring-indigo-500/50
                           disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center justify-center gap-2"
                >
                    <svg id="btn-spinner" class="hidden w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                    </svg>
                    <span id="btn-login-text">Masuk</span>
                </button>
            </form>

            {{-- Divider --}}
            <div class="mt-6 pt-5 border-t border-white/10">
                <p class="text-xs text-center text-slate-500">
                    Hanya admin terdaftar yang dapat mengakses panel ini.
                    <br>
                    <a href="{{ route('home') }}" class="text-indigo-400 hover:text-indigo-300 transition-colors">
                        ← Kembali ke Dashboard Publik
                    </a>
                </p>
            </div>
        </div>

        <p class="text-center text-xs text-slate-600 mt-6">
            © {{ date('Y') }} DEKSI · Deteksi Ekonomi Indonesia
        </p>
    </div>
</div>
@endsection

@push('scripts')
<script>
(function () {
    const BACKEND = '{{ env("VITE_BACKEND_URL", "http://127.0.0.1:8000") }}';

    // ── Toggle show/hide password ──────────────────────────────────────────
    const toggleBtn  = document.getElementById('toggle-password');
    const passInput  = document.getElementById('password');
    const iconEye    = document.getElementById('icon-eye');
    const iconEyeOff = document.getElementById('icon-eye-off');

    toggleBtn.addEventListener('click', () => {
        const isPassword = passInput.type === 'password';
        passInput.type   = isPassword ? 'text' : 'password';
        iconEye.classList.toggle('hidden',  isPassword);
        iconEyeOff.classList.toggle('hidden', !isPassword);
    });

    // ── Helper UI ──────────────────────────────────────────────────────────
    function showError(msg) {
        const el = document.getElementById('alert-error');
        document.getElementById('alert-error-text').textContent = msg;
        el.classList.remove('hidden');
    }

    function hideError() {
        document.getElementById('alert-error').classList.add('hidden');
    }

    function setFieldError(id, msg) {
        const el = document.getElementById(id);
        el.textContent = msg;
        el.classList.toggle('hidden', !msg);
    }

    function setLoading(loading) {
        const btn     = document.getElementById('btn-login');
        const spinner = document.getElementById('btn-spinner');
        const text    = document.getElementById('btn-login-text');
        btn.disabled = loading;
        spinner.classList.toggle('hidden', !loading);
        text.textContent = loading ? 'Memproses...' : 'Masuk';
    }

    // ── Form submit ────────────────────────────────────────────────────────
    document.getElementById('form-login').addEventListener('submit', async function(e) {
        e.preventDefault();
        hideError();
        setFieldError('email-error', '');
        setFieldError('password-error', '');

        const email    = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        // Validasi client-side
        if (!email) { setFieldError('email-error', 'Email wajib diisi.'); return; }
        if (!password) { setFieldError('password-error', 'Kata sandi wajib diisi.'); return; }

        setLoading(true);

        try {
            const res = await fetch(`${BACKEND}/api/v1/auth/login/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ email, password }),
            });

            const data = await res.json();

            if (res.ok && data.success) {
                // Simpan token di localStorage
                localStorage.setItem('deksi_token', data.data.token);
                localStorage.setItem('deksi_user',  JSON.stringify(data.data.user));
                // Redirect ke dashboard admin
                window.location.href = '{{ route("dashboard") }}';
            } else {
                const errors = data.errors || {};
                const msg = errors.non_field_errors?.[0]
                         || errors.email?.[0]
                         || errors.password?.[0]
                         || data.message
                         || 'Terjadi kesalahan. Silakan coba lagi.';
                showError(msg);
            }
        } catch (err) {
            showError('Tidak dapat menghubungi server. Periksa koneksi Anda.');
        } finally {
            setLoading(false);
        }
    });
})();
</script>
@endpush
