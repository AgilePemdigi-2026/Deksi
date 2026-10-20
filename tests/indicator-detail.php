<?php

// Runs real Laravel HTTP requests without PHPUnit or a database.
use Illuminate\Contracts\Http\Kernel;
use Illuminate\Http\Request;

require __DIR__.'/../vendor/autoload.php';

putenv('APP_ENV=testing');
putenv('APP_DEBUG=false');
putenv('APP_KEY=base64:'.base64_encode(str_repeat('t', 32)));
putenv('SESSION_DRIVER=array');
putenv('CACHE_STORE=array');

$app = require __DIR__.'/../bootstrap/app.php';
$kernel = $app->make(Kernel::class);
$request = Request::create('/indikator/pdb', 'GET');
$response = $kernel->handle($request);
$status = $response->getStatusCode();
if ($status !== 200) {
    fwrite(STDERR, "FAIL detail is public: expected HTTP 200, got {$status}\n");
    exit(1);
}
if (! str_contains($response->getContent(), 'Pertumbuhan PDB')) {
    fwrite(STDERR, "FAIL detail does not render the selected indicator\n");
    exit(1);
}
if (! str_contains($response->getContent(), 'Data demo')) {
    fwrite(STDERR, "FAIL detail must visibly identify the existing example dataset as demo\n");
    exit(1);
}
if (! str_contains($response->getContent(), 'YoY (Q2 2024)')) {
    fwrite(STDERR, "FAIL detail must show the supplied unit and observation period\n");
    exit(1);
}
if (! str_contains($response->getContent(), 'Data historis') || ! str_contains($response->getContent(), '<svg')) {
    fwrite(STDERR, "FAIL detail must render history as an accessible table and chart\n");
    exit(1);
}
if (str_contains($response->getContent(), '+0,11% vs Q1') || str_contains($response->getContent(), 'Didorong penguatan sektor')) {
    fwrite(STDERR, "FAIL detail must not promote unvalidated badges or causal claims from the demo dataset\n");
    exit(1);
}
echo "PASS public detail, demo disclosure, period and accessible history\n";
$kernel->terminate($request, $response);
