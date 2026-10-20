<?php

return [

    'driver' => env('SESSION_DRIVER', 'file'),

    'lifetime' => (int) env('SESSION_LIFETIME', 120),

    'expire_on_close' => false,

    'files' => storage_path('framework/sessions'),

    'connection' => null,

    'table' => 'sessions',

    'lottery' => [2, 100],

    'cookie' => env('SESSION_COOKIE', 'deksi_session'),

    'path' => '/',

    'domain' => env('SESSION_DOMAIN'),

    'secure' => env('SESSION_SECURE_COOKIE'),

    'http_only' => true,

    'encrypted' => true,

    'same_site' => 'lax',
];
