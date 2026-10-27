<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title', 'DEKSI') — Deteksi Ekonomi Indonesia</title>
    <meta name="description" content="@yield('meta_description', 'Platform data dan analisis ekonomi Indonesia yang terstruktur, transparan, dan dapat ditelusuri.')">

    @vite(['resources/css/app.css', 'resources/js/app.js'])
    @stack('styles')
</head>
<body class="bg-[#0B0F1A] text-white antialiased min-h-screen">
    @yield('content')
    @stack('scripts')
</body>
</html>
