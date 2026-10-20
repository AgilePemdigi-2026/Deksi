<?php

namespace App\Support;

use Illuminate\Support\Collection;

class IndicatorRepository
{
    private ?array $cache = null;

    private function muat(): array
    {
        if ($this->cache !== null) {
            return $this->cache;
        }

        $path = resource_path('data/indicators.json');

        if (! is_file($path)) {
            throw new \RuntimeException('File data indikator tidak ditemukan: resources/data/indicators.json');
        }

        $json = json_decode((string) file_get_contents($path), true);

        if (! is_array($json) || ! isset($json['indikator'])) {
            throw new \RuntimeException('Format resources/data/indicators.json tidak valid.');
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
