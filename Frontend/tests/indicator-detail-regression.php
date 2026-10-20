<?php

use App\Support\IndicatorHistory;
use App\Support\IndicatorRepository;
use Illuminate\Contracts\Http\Kernel;
use Illuminate\Http\Request;

require __DIR__.'/../vendor/autoload.php';
putenv('APP_ENV=testing');
putenv('APP_DEBUG=false');
putenv('APP_KEY=base64:'.base64_encode(str_repeat('t', 32)));
putenv('SESSION_DRIVER=array');
putenv('CACHE_STORE=array');

$passed = $failed = 0;
$initialFixtureHash = hash_file('sha256', __DIR__.'/../resources/data/indicators.json');
function verify(bool $condition, string $message): void
{
    if (! $condition) {
        throw new RuntimeException($message);
    }
}
function scenario(string $name, callable $run): void
{
    global $passed, $failed;
    try {
        $run();
        $passed++;
        echo "PASS {$name}\n";
    } catch (Throwable $exception) {
        $failed++;
        echo "FAIL {$name}: {$exception->getMessage()}\n";
    }
}
function responseFor(string $uri, ?string $data = null, bool $missing = false): array
{
    $path = null;
    if ($data !== null || $missing) {
        $scratch = getenv('DEKSI_TEST_SCRATCH') ?: __DIR__.'/../storage/framework/testing';
        if (! is_dir($scratch)) {
            mkdir($scratch, 0777, true);
        }
        $path = tempnam($scratch, 'deksi-fixture-');
        if ($missing) {
            unlink($path);
        } else {
            file_put_contents($path, $data);
        }
    }
    try {
        $app = require __DIR__.'/../bootstrap/app.php';
        if ($path !== null) {
            $app->instance(IndicatorRepository::class, new IndicatorRepository($path));
        }
        $kernel = $app->make(Kernel::class);
        $request = Request::create($uri, 'GET');
        $response = $kernel->handle($request);
        $result = [$response->getStatusCode(), $response->getContent()];
        $kernel->terminate($request, $response);

        return $result;
    } finally {
        if ($path !== null && is_file($path)) {
            unlink($path);
        }
    }
}
function fixture(array $overrides = []): string
{
    $item = array_replace(['kode' => 'uji', 'nama' => 'Indikator uji sintetis', 'nilai' => 0,
        'satuan' => 'Unit uji', 'periode' => 'Periode uji', 'tren' => null], $overrides);

    return json_encode(['status_data' => 'baseline-contoh', 'indikator' => [$item]], JSON_THROW_ON_ERROR);
}

scenario('null values are unavailable, never synthetic zero', function () {
    [$status, $html] = responseFor('/indikator/uji', fixture(['nilai' => null]));
    verify($status === 200 && str_contains($html, 'Belum tersedia'), 'null detail must render safely');
});
scenario('zero is a supplied value, not missing', function () {
    [$status, $html] = responseFor('/indikator/uji', fixture());
    verify($status === 200 && preg_match('/font-bold[^>]*>0<\/p>/', $html) === 1, 'zero must remain visible');
});
scenario('malformed JSON returns recoverable 503', function () {
    [$status, $html] = responseFor('/indikator/uji', '{invalid');
    verify($status === 503 && str_contains($html, 'Coba lagi'), 'invalid data must not look like missing indicator');
});
scenario('missing dataset returns recoverable 503', function () {
    [$status, $html] = responseFor('/indikator/uji', null, true);
    verify($status === 503 && str_contains($html, 'Data indikator belum dapat dimuat'), 'missing dataset needs useful recovery');
});
scenario('wrong dataset shape returns 503', function () {
    [$status] = responseFor('/indikator/uji', '{"indikator":"wrong"}');
    verify($status === 503, 'malformed list must be rejected');
});
scenario('duplicate indicator identities are rejected', function () {
    $item = ['kode' => 'uji', 'nama' => 'Uji'];
    [$status] = responseFor('/indikator/uji', json_encode(['indikator' => [$item, $item]]));
    verify($status === 503, 'duplicate identity cannot resolve arbitrarily');
});
scenario('untrusted labels are escaped', function () {
    [$status, $html] = responseFor('/indikator/uji', fixture(['nama' => '<script>alert(1)</script>']));
    verify($status === 200 && ! str_contains($html, '<script>alert(1)</script>')
        && str_contains($html, '&lt;script&gt;alert(1)&lt;/script&gt;'), 'raw label HTML must not execute');
});
scenario('wrong metadata types remain partial', function () {
    [$status, $html] = responseFor('/indikator/uji', fixture(['sumber' => ['bad'], 'rilis' => ['bad']]));
    verify($status === 200 && str_contains($html, 'Belum tersedia'), 'metadata must not crash HTML escaping');
});
scenario('unknown indicator is 404', function () {
    [$status] = responseFor('/indikator/tidak_ada');
    verify($status === 404, 'unknown identifier must not select another indicator');
});
foreach (['pdb', 'inflasi', 'fiskal', 'investasi', 'bi_rate', 'tpt'] as $code) {
    scenario('public detail '.$code, function () use ($code) {
        [$status, $html] = responseFor('/indikator/'.$code);
        verify($status === 200 && str_contains($html, 'Data demo'), 'public detail must work without authentication');
        verify(! str_contains($html, 'Resmi &amp; Terverifikasi'), 'do not reuse verified claim from fixture tooltip');
    });
}
scenario('dashboard links to selected details', function () {
    [$status, $html] = responseFor('/dashboard');
    verify($status === 200, 'existing dashboard must still render');
    foreach (['pdb', 'inflasi', 'fiskal', 'investasi', 'bi_rate', 'tpt'] as $code) {
        verify(str_contains($html, '/indikator/'.$code), 'missing detail link '.$code);
    }
});
scenario('null gap splits visual segments and preserves rows', function () {
    $history = IndicatorHistory::from(['labels' => ['A', 'B', 'C'], 'values' => [0, null, 2], 'unit_label' => 'Unit uji']);
    verify(count($history['segments']) === 2 && count($history['rows']) === 3, 'must not connect across null');
    verify($history['rows'][0]['value'] === 0 && $history['rows'][1]['y'] === null, 'null is not zero');
});
scenario('empty history stays empty', function () {
    $history = IndicatorHistory::from(null);
    verify($history['segments'] === [] && $history['rows'] === [] && ! $history['invalid'], 'missing is not an error');
});
scenario('mismatched history is not aligned silently', function () {
    $history = IndicatorHistory::from(['labels' => ['A', 'B'], 'values' => [1], 'unit_label' => 'Uji']);
    verify($history['invalid'] && $history['rows'] === [], 'labels and values must match');
});
scenario('history without unit is rejected', function () {
    verify(IndicatorHistory::from(['labels' => ['A'], 'values' => [1]])['invalid'], 'unit is required');
});
scenario('nonnumeric and nonfinite values are rejected', function () {
    foreach (['bad', INF, NAN, []] as $value) {
        verify(IndicatorHistory::from(['labels' => ['A'], 'values' => [$value], 'unit_label' => 'Uji'])['invalid'], 'bad numeric value accepted');
    }
});
scenario('constant and extreme data have finite coordinates', function () {
    foreach ([[1, 1], [-1.0e308, 1.0e308]] as $values) {
        $history = IndicatorHistory::from(['labels' => ['A', 'B'], 'values' => $values, 'unit_label' => 'Uji']);
        foreach ($history['rows'] as $row) {
            verify(is_finite($row['x']) && is_finite($row['y']), 'chart produced infinite geometry');
        }
    }
});
scenario('empty history renders useful text and data alternative', function () {
    [$status, $html] = responseFor('/indikator/fiskal');
    verify($status === 200 && str_contains($html, 'Data tren belum tersedia') && str_contains($html, 'Data historis'), 'empty history state missing');
});
scenario('detail has no dead navigation', function () {
    [$status, $html] = responseFor('/indikator/pdb');
    verify($status === 200 && ! str_contains($html, 'href="#"'), 'detail must not ship placeholder links');
});
scenario('unknown indicator offers recovery', function () {
    [$status, $html] = responseFor('/indikator/tidak_ada');
    verify($status === 404 && str_contains($html, 'Indikator tidak ditemukan') && str_contains($html, '/dashboard'), '404 must explain recovery');
});
scenario('local fixture is unchanged after all requests', function () {
    $file = __DIR__.'/../resources/data/indicators.json';
        $initialFixtureHash = $GLOBALS['initialFixtureHash'];
        verify(hash_file('sha256', $file) === $initialFixtureHash, 'test must not change team fixture');
});
echo "RESULT {$passed} passed; {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
