<?php

namespace App\Support;

class SourceTraceRepository
{
    public function __construct(private ?string $dataPath = null)
    {
    }

    private function records(): array
    {
        $path = $this->dataPath ?? resource_path('data/source-traces.json');
        if (! is_file($path)) {
            throw new \RuntimeException('Dataset Source Trace belum tersedia.');
        }
        $data = json_decode(file_get_contents($path), true, 512, JSON_THROW_ON_ERROR);
        if (! is_array($data) || ($data['status_data'] ?? null) !== 'demo'
            || ! isset($data['traces']) || ! is_array($data['traces']) || ! array_is_list($data['traces'])) {
            throw new \RuntimeException('Format dataset Source Trace tidak valid.');
        }
        $ids = [];
        foreach ($data['traces'] as $trace) {
            if (! is_array($trace) || ! is_string($trace['id'] ?? null)
                || preg_match('/\A[a-z0-9_-]+\z/D', $trace['id']) !== 1
                || isset($ids[$trace['id']]) || ! is_string($trace['indicator_code'] ?? null)
                || ! is_string($trace['version'] ?? null) || trim($trace['version']) === ''
                || ! is_array($trace['snapshot'] ?? null)
                || ($trace['snapshot']['kode'] ?? null) !== $trace['indicator_code']) {
                throw new \RuntimeException('Identitas Source Trace tidak valid atau duplikat.');
            }
            $ids[$trace['id']] = true;
        }

        return $data['traces'];
    }

    public function find(string $code, string $id): ?array
    {
        foreach ($this->records() as $record) {
            if ($record['indicator_code'] === $code && $record['id'] === $id) {
                return $this->present($record);
            }
        }

        return null;
    }

    public function forIndicator(array $indicator): ?array
    {
        $matches = array_values(array_filter($this->records(), fn ($record) => $this->matches($record, $indicator)));

        return count($matches) === 1 ? $this->present($matches[0]) : null;
    }

    public function matches(array $trace, array $indicator): bool
    {
        foreach (['kode', 'periode', 'nilai', 'satuan'] as $field) {
            $expected = self::text($trace['snapshot'][$field] ?? null);
            if ($expected === null || $expected !== self::text($indicator[$field] ?? null)) {
                return false;
            }
        }

        // A revised release can keep the same number but have different provenance.
        foreach (['rilis', 'sumber', 'sumber_lengkap'] as $field) {
            if (self::text($trace['snapshot'][$field] ?? null) !== self::text($indicator[$field] ?? null)) {
                return false;
            }
        }

        return true;
    }

    private static function text(mixed $value): ?string
    {
        if (is_string($value) && trim($value) !== '') {
            return trim($value);
        }
        if (is_int($value) || (is_float($value) && is_finite($value))) {
            return (string) $value;
        }

        return null;
    }

    private static function safeUrl(mixed $value): ?string
    {
        if (! is_string($value) || preg_match('/[\x00-\x20\x7f]/', $value)
            || ! filter_var($value, FILTER_VALIDATE_URL)) {
            return null;
        }
        $parts = parse_url($value);
        if (! is_array($parts) || ! in_array(strtolower($parts['scheme'] ?? ''), ['http', 'https'], true)
            || empty($parts['host']) || isset($parts['user']) || isset($parts['pass'])) {
            return null;
        }

        return $value;
    }

    private function present(array $record): array
    {
        $snapshot = [];
        foreach (['kode', 'nama', 'nilai', 'satuan', 'satuan_label', 'periode', 'sumber', 'sumber_lengkap', 'rilis'] as $field) {
            $snapshot[$field] = self::text($record['snapshot'][$field] ?? null);
        }
        $result = ['id' => $record['id'], 'indicator_code' => $record['indicator_code'],
            'version' => $record['version'], 'snapshot' => $snapshot];
        foreach (['publication_name', 'fetched_at', 'formula_id', 'formula_version', 'formula_expression'] as $field) {
            $result[$field] = self::text($record[$field] ?? null);
        }
        $result['data_type'] = in_array($record['data_type'] ?? null, ['official', 'derived'], true)
            ? $record['data_type'] : null;
        $result['publication_url'] = self::safeUrl($record['publication_url'] ?? null);
        $result['formula_is_example'] = ($record['formula_is_example'] ?? null) === true;
        foreach (['inputs' => ['parameter', 'period', 'value', 'unit', 'source'],
            'references' => ['title', 'url'], 'revisions' => ['timestamp', 'type', 'value', 'note']] as $key => $fields) {
            $result[$key] = [];
            $items = $record[$key] ?? [];
            if (! is_array($items) || ! array_is_list($items)) {
                continue;
            }
            foreach ($items as $item) {
                if (! is_array($item)) {
                    continue;
                }
                $row = [];
                foreach ($fields as $field) {
                    $row[$field] = $field === 'url' ? self::safeUrl($item[$field] ?? null) : self::text($item[$field] ?? null);
                }
                $result[$key][] = $row;
            }
        }

        return $result;
    }
}
