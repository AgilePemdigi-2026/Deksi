<?php

namespace App\Support;

use Illuminate\Support\Collection;

class IndicatorRepository
{
    private ?array $cache = null;

    public function __construct(private ?string $dataPath = null)
    {
    }

    private function muat(): array
    {
        if ($this->cache !== null) {
            return $this->cache;
        }

        $path = $this->dataPath ?? resource_path('data/indicators.json');

        if (! is_file($path)) {
            throw new \RuntimeException('File data indikator tidak ditemukan: resources/data/indicators.json');
        }

        $json = json_decode((string) file_get_contents($path), true, 512, JSON_THROW_ON_ERROR);

        if (! is_array($json) || ! isset($json['indikator']) || ! is_array($json['indikator'])
            || ! array_is_list($json['indikator'])) {
            throw new \RuntimeException('Format resources/data/indicators.json tidak valid.');
        }
        $codes = [];
        foreach ($json['indikator'] as $item) {
            $code = is_array($item) ? ($item['kode'] ?? null) : null;
            if (! is_string($code) || $code === '' || isset($codes[$code])) {
                throw new \RuntimeException('Identitas indikator tidak valid atau duplikat.');
            }
            $codes[$code] = true;
        }

        return $this->cache = $json;
    }

    public function semua(): Collection
    {
        return collect($this->muat()['indikator']);
    }

    public function temukan(string $kode): ?array
    {
        return $this->semua()->firstWhere('kode', $kode);
    }

    public function global(): array
    {
        return $this->muat()['global'] ?? [];
    }
}
