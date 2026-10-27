@extends('layouts.app')

@section('title', 'Lupa Kata Sandi')
@section('meta_description', 'Reset kata sandi akun Admin DEKSI.')

@section('content')
<div class="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#0B0F1A]">

    {{-- Ambient background --}}
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
        <div class="absolute -top-32 -left-32 w-80 h-80 bg-violet-600/20 rounded-full blur-3xl animate-pulse"></div>
        <div class="absolute bottom-0 right-0 w-72 h-72 bg-indigo-500/15 rounded-full blur-3xl animate-pulse delay-700"></div>
        <div class="absolute inset-0 opacity-5"
             style="background-image: linear-gradient(#4f6ef7 1px, transparent 1px), linear-gradient(90deg, #4f6ef7 1px, transparent 1px); background-size: 40px 40px;"></div>
    </div>

    <div class="relative w-full max-w-md mx-auto px-4 py-8">

        {{-- Logo --}}
        <div class="text-center mb-8">
            <a href="{{ route('admin.login') }}" class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg shadow-indigo-500/30 mb-4 hover:opacity-90 transition-opacity">
                <svg class="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
            </a>
            <h1 class="text-2xl font-bold text-white tracking-tight">DEKSI</h1>
            <p class="text-sm text-slate-400 mt-1">Reset Kata Sandi Admin</p>
        </div>

        {{-- Card --}}
        <div class="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl shadow-black/40 p-8">

            {{-- Step 1: Input email (default) --}}
            <div id="step-email">
                <div class="flex items-center gap-3 mb-5">
                    <div class="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center shrink-0">
                        <svg class="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                        </svg>
                    </div>
                    <div>
                        <h2 class="text-lg font-semibold text-white">Lupa Kata Sandi?</h2>
                        <p class="text-xs text-slate-400">Kami kirim tautan reset ke email Anda.</p>
                    </div>
                </div>

                {{-- Alert --}}
                <div id="alert-error" class="hidden mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm flex items-start gap-2">
                    <svg class="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <span id="alert-error-text"></span>
                </div>

                <form id="form-forgot" novalidate>
                    <div class="mb-5">
                        <label for="email" class="block text-sm font-medium text-slate-300 mb-1.5">
                            Alamat Email Terdaftar
                        </label>
                        <input
                            type="email" id="email" name="email"
                            placeholder="admin@deksi.id"
                            autocomplete="email" required
                            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500
                                   text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
                        >
                        <p id="email-error" class="hidden text-xs text-red-400 mt-1"></p>
                    </div>

                    <button type="submit" id="btn-send"
                        class="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500
                               text-white font-semibold rounded-lg text-sm shadow-lg shadow-indigo-500/25
                               transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50
                               disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                        <svg id="btn-spinner" class="hidden w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                        </svg>
                        <span id="btn-send-text">Kirim Tautan Reset</span>
                    </button>
                </form>
            </div>

            {{-- Step 2: Email terkirim (success state) --}}
            <div id="step-success" class="hidden text-center py-4">
                <div class="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>
                <h3 class="text-lg font-semibold text-white mb-2">Email Terkirim!</h3>
                <p class="text-sm text-slate-400 mb-1">
                    Jika email <span id="sent-email" class="text-indigo-300 font-medium"></span> terdaftar,
                </p>
                <p class="text-sm text-slate-400 mb-6">
                    tautan reset kata sandi akan dikirim dalam beberapa menit.
                </p>
                <p class="text-xs text-slate-500 mb-4">Tidak menerima email? Periksa folder spam atau</p>
                <button id="btn-resend"
                    class="text-sm text-indigo-400 hover:text-indigo-300 underline transition-colors">
                    Kirim ulang →
                </button>
            </div>

            {{-- Back to login --}}
            <div class="mt-6 pt-5 border-t border-white/10">
                <a href="{{ route('admin.login') }}"
                   class="flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white transition-colors">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
                    </svg>
                    Kembali ke halaman login
                </a>
            </div>
        </div>
    </div>
</div>
@endsection

@push('scripts')
<script>
(function () {
    const BACKEND = '{{ env("VITE_BACKEND_URL", "http://127.0.0.1:8000") }}';

    function showError(msg) {
        const el = document.getElementById('alert-error');
        document.getElementById('alert-error-text').textContent = msg;
        el.classList.remove('hidden');
    }
    function hideError() {
        document.getElementById('alert-error').classList.add('hidden');
    }
    function setLoading(on) {
        const btn = document.getElementById('btn-send');
        btn.disabled = on;
        document.getElementById('btn-spinner').classList.toggle('hidden', !on);
        document.getElementById('btn-send-text').textContent = on ? 'Mengirim...' : 'Kirim Tautan Reset';
    }

    async function sendRequest(email) {
        setLoading(true);
        hideError();
        try {
            const res  = await fetch(`${BACKEND}/api/v1/auth/forgot-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();

            if (res.ok && data.success) {
                document.getElementById('sent-email').textContent = email;
                document.getElementById('step-email').classList.add('hidden');
                document.getElementById('step-success').classList.remove('hidden');
            } else {
                const msg = data.errors?.email?.[0] || data.message || 'Terjadi kesalahan.';
                showError(msg);
            }
        } catch {
            showError('Tidak dapat menghubungi server.');
        } finally {
            setLoading(false);
        }
    }

    document.getElementById('form-forgot').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();
        const errEl = document.getElementById('email-error');
        if (!email) {
            errEl.textContent = 'Email wajib diisi.';
            errEl.classList.remove('hidden');
            return;
        }
        errEl.classList.add('hidden');
        await sendRequest(email);
    });

    document.getElementById('btn-resend').addEventListener('click', () => {
        document.getElementById('step-success').classList.add('hidden');
        document.getElementById('step-email').classList.remove('hidden');
    });
})();
</script>
@endpush
