<?php

namespace App\Http\Controllers;

use App\Support\IndicatorRepository;
use App\Support\IndicatorHistory;
use Illuminate\Contracts\View\View;

class IndicatorController extends Controller
{
    public function __construct(private IndicatorRepository $indikator)
    {
    }

    public function show(string $kode): View|\Illuminate\Http\Response
    {
        try {
            $indicator = $this->indikator->temukan($kode);
        } catch (\RuntimeException|\JsonException $exception) {
            report($exception);

            return response()->view('indicators.unavailable', [], 503);
        }
        if ($indicator === null) {
            return response()->view('indicators.not-found', [], 404);
        }

        $history = IndicatorHistory::from($indicator['tren'] ?? null);
        // Legacy example badges and causal descriptions are not validated evidence.
        $fields = ['kode', 'nama', 'kategori', 'nilai', 'satuan_label', 'satuan', 'periode',
            'sumber_lengkap', 'sumber', 'rilis', 'pembaruan', 'definisi', 'frekuensi'];
        $safe = [];
        foreach ($fields as $field) {
            $value = $indicator[$field] ?? null;
            $safe[$field] = (is_string($value) && trim($value) !== '') || is_int($value) || is_float($value)
                ? (string) $value : null;
        }

        return view('indicators.show', ['indicator' => $safe, 'history' => $history]);
    }
}
