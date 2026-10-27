<?php

namespace App\Http\Controllers;

use App\Support\IndicatorRepository;
use App\Support\SourceTraceRepository;
use Illuminate\Contracts\View\View;
use Illuminate\Http\Response;

class SourceTraceController extends Controller
{
    public function __construct(private SourceTraceRepository $traces, private IndicatorRepository $indicators)
    {
    }

    public function show(string $kode, string $trace): View|Response
    {
        try {
            $record = $this->traces->find($kode, $trace);
        } catch (\RuntimeException|\JsonException $exception) {
            report($exception);

            return response()->view('source-trace.state', ['unavailable' => true], 503);
        }
        if ($record === null) {
            return response()->view('source-trace.state', ['unavailable' => false], 404);
        }
        try {
            $current = $this->indicators->temukan($kode);
            $matchesDetail = $current !== null && $this->traces->matches($record, $current);
        } catch (\RuntimeException|\JsonException $exception) {
            report($exception);
            $matchesDetail = false;
        }

        return view('source-trace.show', ['trace' => $record, 'matchesDetail' => $matchesDetail]);
    }
}
