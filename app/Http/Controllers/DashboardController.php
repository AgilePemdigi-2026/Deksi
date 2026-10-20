<?php

namespace App\Http\Controllers;

use App\Support\IndicatorRepository;
use Illuminate\Http\Request;

class DashboardController extends Controller
{
    public function __construct(private IndicatorRepository $indikator)
    {
    }

    public function index(Request $request)
    {
        $demo = $request->string('demo')->toString();

        $indikator = $this->indikator->semua();

        if ($demo === 'kosong') {
            foreach ($indikator as $i => $data) {
                if ($data['kode'] === 'pdb') {
                    $data['tren']['values'] = [];
                }
                if ($data['kode'] === 'inflasi') {
                    $data['tren']['values'] = [];
                }
                if ($data['kode'] === 'investasi') {
                    $data['tren']['values'] = [];
                }
                if ($data['kode'] === 'bi_rate') {
                    $data['tren']['values'] = [];
                }
                $indikator[$i] = $data;
            }
        }

        return view('dashboard.index', [
            'indikator' => $indikator,
            'global' => $this->indikator->global(),
            'grafikGagal' => $demo === 'gagal',
            'grafikKosong' => $demo === 'kosong',
        ]);
    }
}
