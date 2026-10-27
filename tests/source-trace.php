<?php

use Illuminate\Contracts\Http\Kernel;
use Illuminate\Http\Request;
use App\Support\SourceTraceRepository;
use App\Support\IndicatorRepository;

require __DIR__.'/../vendor/autoload.php';
putenv('APP_ENV=testing');
putenv('APP_DEBUG=false');
putenv('APP_KEY=base64:'.base64_encode(str_repeat('t', 32)));
putenv('SESSION_DRIVER=array');
putenv('CACHE_STORE=array');

$passed = $failed = 0;
$fixtureHashes = [];
foreach (['indicators.json', 'source-traces.json'] as $file) {
    $fixtureHashes[$file] = hash_file('sha256', __DIR__.'/../resources/data/'.$file);
}
$temporaryPaths = [];
function check(bool $condition, string $message): void
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
function requestTrace(string $uri, array $options = []): array
{
    $paths = [];
    try {
        $app = require __DIR__.'/../bootstrap/app.php';
        foreach (['trace_json' => SourceTraceRepository::class, 'indicator_json' => IndicatorRepository::class] as $key => $class) {
            if (! array_key_exists($key, $options)) {
                continue;
            }
            $scratch = getenv('DEKSI_TEST_SCRATCH') ?: getenv('TMPDIR');
            check(is_string($scratch) && is_dir($scratch), 'set DEKSI_TEST_SCRATCH to an existing owned scratch directory');
            $path = tempnam($scratch, 'deksi-trace-test-');
            check($path !== false, 'cannot allocate scratch fixture');
            $paths[] = $path;
            $GLOBALS['temporaryPaths'][] = $path;
            if ($options[$key] === null) {
                unlink($path);
            } else {
                file_put_contents($path, $options[$key]);
            }
            $app->instance($class, new $class($path));
        }
        $kernel = $app->make(Kernel::class);
        $request = Request::create($uri, 'GET');
        $response = $kernel->handle($request);
        $result = [$response->getStatusCode(), $response->getContent()];
        $kernel->terminate($request, $response);

        return $result;
    } finally {
        foreach ($paths as $path) {
            if (is_file($path)) {
                unlink($path);
            }
        }
    }
}
function sourceFixture(callable $edit): string
{
    $data = json_decode(file_get_contents(__DIR__.'/../resources/data/source-traces.json'), true, 512, JSON_THROW_ON_ERROR);
    $edit($data);

    return json_encode($data, JSON_THROW_ON_ERROR);
}

scenario('source trace is public and visibly demo', function () {
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1');
    check($status === 200, 'expected HTTP 200, got '.$status);
    check(str_contains($html, 'Source Trace Data') && str_contains($html, 'Data demo'), 'page and disclosure required');
    check(str_contains($html, 'Q2 2024') && str_contains($html, '5,05%'), 'must preserve existing indicator context');
    check(! str_contains($html, 'Terverifikasi Resmi'), 'demo cannot claim official verification');
});

scenario('detail links to the same pinned demo snapshot', function () {
    [$status, $html] = requestTrace('/indikator/pdb');
    check($status === 200 && str_contains($html, '/indikator/pdb/sumber/demo-pdb-v1'), 'detail must link to its matching trace');
});

foreach (['pdb', 'inflasi', 'fiskal', 'investasi', 'bi_rate', 'tpt'] as $code) {
    scenario('public trace and matching navigation '.$code, function () use ($code) {
        [$status, $html] = requestTrace('/indikator/'.$code.'/sumber/demo-'.$code.'-v1');
        check($status === 200 && str_contains($html, 'Data demo'), 'trace must render without authentication');
        check(str_contains($html, 'href="http://localhost/indikator/'.$code.'"'), 'back link must retain indicator');
        check(! str_contains($html, 'href="#"'), 'source page must not have dead controls');
    });
}
scenario('unknown trace is a recoverable 404', function () {
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v2');
    check($status === 404 && str_contains($html, 'Source Trace tidak ditemukan') && str_contains($html, '/dashboard'), 'must not select latest snapshot silently');
});
scenario('cross-indicator trace is rejected', function () {
    [$status] = requestTrace('/indikator/inflasi/sumber/demo-pdb-v1');
    check($status === 404, 'trace identity must bind indicator');
});
scenario('malformed JSON is a recoverable 503', function () {
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => '{bad']);
    check($status === 503 && str_contains($html, 'Coba lagi'), 'bad source is not a missing trace');
});
scenario('missing trace dataset is a recoverable 503', function () {
    [$status] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => null]);
    check($status === 503, 'missing source needs unavailable state');
});
scenario('malformed list is rejected', function () {
    [$status] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => '{"status_data":"demo","traces":"bad"}']);
    check($status === 503, 'list must be validated');
});
scenario('duplicate trace identity is rejected', function () {
    $json = sourceFixture(function (&$data) { $data['traces'][] = $data['traces'][0]; });
    [$status] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 503, 'duplicate ID must not resolve arbitrarily');
});
scenario('snapshot with mismatched indicator is rejected', function () {
    $json = sourceFixture(function (&$data) { $data['traces'][0]['snapshot']['kode'] = 'inflasi'; });
    [$status] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 503, 'snapshot binding must be validated');
});
scenario('partial metadata is readable without fabricated values', function () {
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1');
    check($status === 200 && str_contains($html, 'Publikasi spesifik belum tersedia')
        && str_contains($html, 'Riwayat revisi belum tersedia'), 'missing evidence needs explicit disclosure');
    check(! str_contains($html, '58/08/Th.') && ! str_contains($html, 'SNA 2008'), 'mockup publication/certification must not be promoted');
});
scenario('null value is not zero', function () {
    $json = sourceFixture(function (&$data) { $data['traces'][0]['snapshot']['nilai'] = null; });
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 200 && str_contains($html, 'class="trace-metric">Belum tersedia'), 'null must remain unavailable');
});
scenario('zero value remains zero', function () {
    $json = sourceFixture(function (&$data) { $data['traces'][0]['snapshot']['nilai'] = 0; });
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 200 && str_contains($html, 'class="trace-metric">0</p>'), 'zero must not disappear');
});
scenario('unexpected optional types render as partial metadata', function () {
    $json = sourceFixture(function (&$data) {
        foreach (['publication_name', 'publication_url', 'fetched_at', 'formula_expression'] as $key) { $data['traces'][0][$key] = ['bad']; }
        $data['traces'][0]['snapshot']['sumber'] = ['bad'];
        $data['traces'][0]['references'] = 'bad';
        $data['traces'][0]['inputs'] = [['value' => ['bad']]];
    });
    [$status] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 200, 'optional malformed data must not crash escaping');
});
scenario('untrusted text is escaped in every metadata section', function () {
    $attack = '<script>bad-source-trace</script>';
    $json = sourceFixture(function (&$data) use ($attack) {
        $trace = &$data['traces'][0];
        $trace['snapshot']['nama'] = $attack;
        $trace['publication_name'] = $attack;
        $trace['formula_id'] = $attack;
        $trace['formula_expression'] = $attack;
        $trace['inputs'] = [['parameter' => $attack, 'value' => $attack]];
        $trace['revisions'] = [['note' => $attack]];
    });
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 200 && ! str_contains($html, $attack)
        && str_contains($html, '&lt;script&gt;bad-source-trace&lt;/script&gt;'), 'source text must never become HTML');
});
foreach (['javascript:alert(1)', 'data:text/html,bad', '//example.test/path', 'https://user:password@example.test/', "https://example.test/\npath"] as $index => $url) {
    scenario('unsafe source URL rejected '.$index, function () use ($url) {
        $json = sourceFixture(function (&$data) use ($url) {
            $data['traces'][0]['publication_url'] = $url;
            $data['traces'][0]['references'] = [['title' => 'Synthetic reference', 'url' => $url]];
        });
        [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
        check($status === 200 && ! str_contains($html, 'href="'.htmlspecialchars($url, ENT_QUOTES).'"'), 'unsafe URL must not become link');
        check(str_contains($html, 'tautan belum tersedia atau tidak valid'), 'rejected URL must have readable state');
    });
}
scenario('valid source link is protected and not fetched by server', function () {
    $url = 'https://example.test/synthetic-publication';
    $json = sourceFixture(function (&$data) use ($url) { $data['traces'][0]['publication_url'] = $url; });
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 200 && str_contains($html, 'href="'.$url.'" target="_blank" rel="noopener noreferrer"'), 'valid metadata link must render safely without needing remote availability');
});
scenario('official classification does not show internal formula', function () {
    $json = sourceFixture(function (&$data) { $data['traces'][0]['data_type'] = 'official'; });
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 200 && str_contains($html, 'Formula internal DEKSI tidak berlaku') && ! str_contains($html, 'trace-fraction'), 'official value must not inherit derived formula');
});
scenario('derived classification with absent formula reports incomplete provenance', function () {
    $json = sourceFixture(function (&$data) {
        $data['traces'][0]['data_type'] = 'derived';
        $data['traces'][0]['formula_expression'] = null;
    });
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['trace_json' => $json]);
    check($status === 200 && str_contains($html, 'Keterlacakan belum lengkap'), 'missing derived inputs must be visible');
});
scenario('unknown classification never guesses a formula', function () {
    [$status, $html] = requestTrace('/indikator/inflasi/sumber/demo-inflasi-v1');
    check($status === 200 && str_contains($html, 'Jenis nilai belum diklasifikasikan'), 'no formula inferred from indicator name');
});
scenario('example formula is not evidence that a value was calculated', function () {
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1');
    check($status === 200 && str_contains($html, 'Ilustrasi Metode') && str_contains($html, 'Hasil kalkulasi backend</th><td colspan="2">Belum tersedia'), 'frontend must not calculate missing inputs');
});
scenario('changed detail does not link an old snapshot', function () {
    $data = json_decode(file_get_contents(__DIR__.'/../resources/data/indicators.json'), true);
    $data['indikator'][0]['nilai'] = '999 contoh uji';
    $json = json_encode($data, JSON_THROW_ON_ERROR);
    [$status, $html] = requestTrace('/indikator/pdb', ['indicator_json' => $json]);
    check($status === 200 && ! str_contains($html, '/sumber/demo-pdb-v1'), 'updated detail must not point at stale trace');
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1', ['indicator_json' => $json]);
    check($status === 200 && str_contains($html, '5,05%') && str_contains($html, 'Snapshot ini tidak cocok')
        && ! str_contains($html, 'href="http://localhost/indikator/pdb"'), 'old trace must stay pinned and disable misleading return link');
});
scenario('ambiguous matching snapshots do not select an arbitrary version', function () {
    $json = sourceFixture(function (&$data) {
        $copy = $data['traces'][0]; $copy['id'] = 'demo-pdb-v2'; $copy['version'] = 'demo-v2'; $data['traces'][] = $copy;
    });
    [$status, $html] = requestTrace('/indikator/pdb', ['trace_json' => $json]);
    check($status === 200 && ! str_contains($html, '/sumber/demo-pdb-'), 'ambiguous versions must not auto-select latest');
});
scenario('changed release metadata cannot reuse an older provenance link', function () {
    $data = json_decode(file_get_contents(__DIR__.'/../resources/data/indicators.json'), true);
    $data['indikator'][0]['rilis'] = 'Tanggal revisi sintetis';
    [$status, $html] = requestTrace('/indikator/pdb', ['indicator_json' => json_encode($data, JSON_THROW_ON_ERROR)]);
    check($status === 200 && ! str_contains($html, '/sumber/demo-pdb-v1'), 'same number with changed release must not inherit old provenance');
});
scenario('trace failure does not remove readable indicator detail', function () {
    [$status, $html] = requestTrace('/indikator/pdb', ['trace_json' => '{bad']);
    check($status === 200 && str_contains($html, 'Data historis') && str_contains($html, 'Source Trace untuk snapshot ini belum tersedia'), 'optional source failure must not destroy valid detail');
});
scenario('release precision is preserved without inventing time', function () {
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1');
    check($status === 200 && str_contains($html, '05 Agu 2024') && str_contains($html, 'Waktu Pengambilan Data</dt><dd>Belum tersedia'), 'release date is not acquisition timestamp');
});
scenario('accessible structure and six explanatory stages', function () {
    [$status, $html] = requestTrace('/indikator/pdb/sumber/demo-pdb-v1');
    check($status === 200 && substr_count($html, 'class="trace-step ') === 6, 'pipeline has six stages, not five');
    check(str_contains($html, 'scope="col"') && str_contains($html, 'tabindex="0"') && str_contains($html, 'aria-label="Breadcrumb"'), 'tables and navigation need accessible structure');
});
scenario('fixtures remain unchanged and scratch files are cleaned', function () use ($fixtureHashes) {
    foreach ($fixtureHashes as $file => $hash) {
        check(hash_file('sha256', __DIR__.'/../resources/data/'.$file) === $hash, 'test mutated team fixture '.$file);
    }
    foreach ($GLOBALS['temporaryPaths'] as $path) { check(! file_exists($path), 'temporary fixture leaked'); }
});

echo "RESULT {$passed} passed; {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
