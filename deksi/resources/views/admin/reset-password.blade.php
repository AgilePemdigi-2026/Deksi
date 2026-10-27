@extends('layouts.app')

@section('title', 'Reset Kata Sandi')
@section('meta_description', 'Buat kata sandi baru untuk akun Admin DEKSI.')

@section('content')
<div class="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#0B0F1A]">

    {{-- Ambient background --}}
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
        <div class="absolute -top-40 right-0 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl animate-pulse"></div>
        <div class="absolute bottom-0 -left-20 w-72 h-72 bg-indigo-500/15 rounded-full blur-3xl animate-pulse delay-500"></div>
        <div class="absolute inset-0 opacity-5"
             style="background-image: linear-gradient(#4f6ef7 1px, transparent 1px), linear-gradient(90deg, #4f6ef7 1px, transparent 1px); background-size: 40px 40px;"></div>
    </div>

    <div class="relative w-full max-w-md mx-auto px-4 py-8">

        {{-- Logo --}}
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg shadow-indigo-500/30 mb-4">
                <svg class="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
            </div>
            <h1 class="text-2xl font-bold text-white tracking-tight">DEKSI</h1>
            <p class="text-sm text-slate-400 mt-1">Buat Kata Sandi Baru</p>
        </div>

        {{-- Token Invalid State --}}
        <div id="state-invalid" class="hidden backdrop-blur-xl bg-white/5 border border-red-500/20 rounded-2xl shadow-2xl p-8 text-center">
            <div class="w-14 h-14 rounded-2xl bg-red-500/20 flex items-center justify-center mx-auto mb-4">
                <svg class="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
            </div>
            <h2 class="text-lg font-semibold text-white mb-2">Token Tidak Valid</h2>
            <p id="invalid-msg" class="text-sm text-slate-400 mb-6">
                Tautan reset sudah tidak berlaku atau telah digunakan.
            </p>
            <a href="{{ route('admin.forgot-password') }}"
               class="inline-block py-2.5 px-6 bg-gradient-to-r from-indigo-600 to-blue-600 text-white font-semibold rounded-lg text-sm transition-all hover:opacity-90">
                Minta Tautan Baru
            </a>
        </div>

        {{-- Loading token check --}}
        <div id="state-loading" class="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl p-8 text-center">
            <svg class="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-3" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <p class="text-sm text-slate-400">Memvalidasi tautan reset...</p>
        </div>

        {{-- Form Reset Password --}}
        <div id="state-form" class="hidden backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl shadow-black/40 p-8">
            <div class="flex items-center gap-3 mb-6">
                <div class="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center shrink-0">
                    <svg class="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
                    </svg>
                </div>
                <div>
                    <h2 class="text-lg font-semibold text-white">Buat Kata Sandi Baru</h2>
                    <p class="text-xs text-slate-400">Minimal 8 karakter.</p>
                </div>
            </div>

            {{-- Alert error --}}
            <div id="alert-error" class="hidden mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm flex items-start gap-2">
                <svg class="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span id="alert-error-text"></span>
            </div>

            <form id="form-reset" novalidate>

                {{-- Kata sandi baru --}}
                <div class="mb-4">
                    <label for="new_password" class="block text-sm font-medium text-slate-300 mb-1.5">Kata Sandi Baru</label>
                    <div class="relative">
                        <input type="password" id="new_password" name="new_password"
                               placeholder="••••••••" required minlength="8"
                               class="w-full px-4 py-2.5 pr-10 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500
                                      text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all">
                        <button type="button" class="toggle-pw absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors" data-target="new_password">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                        </button>
                    </div>
                    {{-- Strength bar --}}
                    <div class="mt-2 h-1 rounded-full bg-white/10 overflow-hidden">
                        <div id="strength-bar" class="h-full rounded-full transition-all duration-300 w-0 bg-red-500"></div>
                    </div>
                    <p id="new_password-error" class="hidden text-xs text-red-400 mt-1"></p>
                </div>

                {{-- Konfirmasi kata sandi --}}
                <div class="mb-6">
                    <label for="confirm_password" class="block text-sm font-medium text-slate-300 mb-1.5">Konfirmasi Kata Sandi</label>
                    <div class="relative">
                        <input type="password" id="confirm_password" name="confirm_password"
                               placeholder="••••••••" required
                               class="w-full px-4 py-2.5 pr-10 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500
                                      text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all">
                        <button type="button" class="toggle-pw absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors" data-target="confirm_password">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                        </button>
                    </div>
                    <p id="confirm_password-error" class="hidden text-xs text-red-400 mt-1"></p>
                </div>

                <button type="submit" id="btn-reset"
                    class="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500
                           text-white font-semibold rounded-lg text-sm shadow-lg shadow-indigo-500/25
                           transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center justify-center gap-2">
                    <svg id="reset-spinner" class="hidden w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                    </svg>
                    <span id="btn-reset-text">Simpan Kata Sandi Baru</span>
                </button>
            </form>
        </div>

        {{-- Success state --}}
        <div id="state-success" class="hidden backdrop-blur-xl bg-white/5 border border-emerald-500/20 rounded-2xl shadow-2xl p-8 text-center">
            <div class="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
            </div>
            <h2 class="text-lg font-semibold text-white mb-2">Kata Sandi Berhasil Diubah!</h2>
            <p class="text-sm text-slate-400 mb-6">Silakan login dengan kata sandi baru Anda.</p>
            <a href="{{ route('admin.login') }}"
               class="inline-block py-2.5 px-6 bg-gradient-to-r from-indigo-600 to-blue-600 text-white font-semibold rounded-lg text-sm hover:opacity-90 transition-opacity">
                Ke Halaman Login →
            </a>
        </div>

    </div>
</div>
@endsection

@push('scripts')
<script>
(function () {
    const BACKEND = '{{ env("VITE_BACKEND_URL", "http://127.0.0.1:8000") }}';

    // Ambil token dari query string
    const params = new URLSearchParams(window.location.search);
    const token  = params.get('token') || '';

    function setState(id) {
        ['state-loading','state-invalid','state-form','state-success'].forEach(s => {
            document.getElementById(s).classList.toggle('hidden', s !== id);
        });
    }

    // ── Validasi token saat halaman load ──────────────────────────────────
    async function validateToken() {
        if (!token) {
            document.getElementById('invalid-msg').textContent = 'Tautan reset tidak lengkap.';
            setState('state-invalid');
            return;
        }
        try {
            const res  = await fetch(`${BACKEND}/api/v1/auth/reset-password/validate/?token=${encodeURIComponent(token)}`);
            const data = await res.json();
            if (res.ok && data.valid) {
                setState('state-form');
            } else {
                document.getElementById('invalid-msg').textContent =
                    data.message || 'Token tidak valid atau sudah kedaluwarsa.';
                setState('state-invalid');
            }
        } catch {
            document.getElementById('invalid-msg').textContent = 'Tidak dapat menghubungi server.';
            setState('state-invalid');
        }
    }
    validateToken();

    // ── Toggle show/hide password ─────────────────────────────────────────
    document.querySelectorAll('.toggle-pw').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = document.getElementById(btn.dataset.target);
            input.type = input.type === 'password' ? 'text' : 'password';
        });
    });

    // ── Password strength bar ─────────────────────────────────────────────
    document.getElementById('new_password').addEventListener('input', function () {
        const val = this.value;
        const bar = document.getElementById('strength-bar');
        let score = 0;
        if (val.length >= 8)  score++;
        if (/[A-Z]/.test(val)) score++;
        if (/[0-9]/.test(val)) score++;
        if (/[^A-Za-z0-9]/.test(val)) score++;
        const colors = ['bg-red-500','bg-orange-400','bg-yellow-400','bg-emerald-500'];
        const widths = ['w-1/4','w-2/4','w-3/4','w-full'];
        bar.className = `h-full rounded-full transition-all duration-300 ${widths[score-1] || 'w-0'} ${colors[score-1] || 'bg-red-500'}`;
    });

    // ── Helper ────────────────────────────────────────────────────────────
    function showError(msg) {
        const el = document.getElementById('alert-error');
        document.getElementById('alert-error-text').textContent = msg;
        el.classList.remove('hidden');
    }
    function setFieldErr(id, msg) {
        const el = document.getElementById(`${id}-error`);
        el.textContent = msg;
        el.classList.toggle('hidden', !msg);
    }
    function setLoading(on) {
        const btn = document.getElementById('btn-reset');
        btn.disabled = on;
        document.getElementById('reset-spinner').classList.toggle('hidden', !on);
        document.getElementById('btn-reset-text').textContent = on ? 'Menyimpan...' : 'Simpan Kata Sandi Baru';
    }

    // ── Form submit ───────────────────────────────────────────────────────
    document.getElementById('form-reset').addEventListener('submit', async (e) => {
        e.preventDefault();
        document.getElementById('alert-error').classList.add('hidden');
        setFieldErr('new_password', '');
        setFieldErr('confirm_password', '');

        const newPw  = document.getElementById('new_password').value;
        const confPw = document.getElementById('confirm_password').value;

        if (newPw.length < 8)      { setFieldErr('new_password', 'Minimal 8 karakter.'); return; }
        if (newPw !== confPw)       { setFieldErr('confirm_password', 'Kata sandi tidak cocok.'); return; }

        setLoading(true);
        try {
            const res  = await fetch(`${BACKEND}/api/v1/auth/reset-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, new_password: newPw, confirm_password: confPw }),
            });
            const data = await res.json();

            if (res.ok && data.success) {
                setState('state-success');
            } else {
                const errors = data.errors || {};
                const msg = errors.token?.[0]
                         || errors.new_password?.[0]
                         || errors.confirm_password?.[0]
                         || data.message
                         || 'Terjadi kesalahan.';
                showError(msg);
            }
        } catch {
            showError('Tidak dapat menghubungi server.');
        } finally {
            setLoading(false);
        }
    });
})();
</script>
@endpush
