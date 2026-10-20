<?php

namespace App\Support;

final class IndicatorHistory
{
    /** Prepare chart geometry only; economic metrics remain backend responsibilities. */
    public static function from(mixed $trend): array
    {
        $empty = ['rows' => [], 'segments' => [], 'invalid' => false, 'unit' => null,
            'title' => 'Tren historis', 'min' => null, 'max' => null];
        if ($trend === null || $trend === []) {
            return $empty;
        }
        if (! is_array($trend)) {
            return [...$empty, 'invalid' => true];
        }
        $labels = $trend['labels'] ?? [];
        $values = $trend['values'] ?? [];
        if (! is_array($labels) || ! is_array($values) || ! array_is_list($labels)
            || ! array_is_list($values) || count($labels) !== count($values)) {
            return [...$empty, 'invalid' => true];
        }
        $unit = $trend['unit_label'] ?? null;
        if ($values !== [] && (! is_string($unit) || trim($unit) === '')) {
            return [...$empty, 'invalid' => true];
        }
        foreach ($labels as $i => $label) {
            $value = $values[$i];
            if (! is_string($label) || trim($label) === '' || ($value !== null
                && ((! is_int($value) && ! is_float($value)) || ! is_finite((float) $value)))) {
                return [...$empty, 'invalid' => true];
            }
        }
        $numeric = array_values(array_filter($values, fn ($value) => $value !== null));
        $min = $numeric === [] ? null : min($numeric);
        $max = $numeric === [] ? null : max($numeric);
        // Scale first to keep visual coordinates finite even for extreme valid numbers.
        $scale = max(abs($min ?? 0), abs($max ?? 0), 1);
        $range = ($max ?? 0) / $scale - ($min ?? 0) / $scale;
        $rows = $segments = $segment = [];
        foreach ($labels as $i => $label) {
            $value = $values[$i];
            $x = round(60 + (count($labels) === 1 ? 345 : $i / (count($labels) - 1) * 690), 2);
            $y = $value === null ? null : round(36 + (1 - ($range == 0 ? 0.5
                : ($value / $scale - $min / $scale) / $range)) * 170, 2);
            $rows[] = ['period' => $label, 'value' => $value, 'x' => $x, 'y' => $y];
            if ($y === null) {
                if ($segment !== []) {
                    $segments[] = implode(' ', $segment);
                    $segment = [];
                }
            } else {
                $segment[] = $x.','.$y;
            }
        }
        if ($segment !== []) {
            $segments[] = implode(' ', $segment);
        }

        return ['rows' => $rows, 'segments' => $segments, 'invalid' => false, 'unit' => $unit,
            'title' => is_string($trend['judul_seri'] ?? null) ? $trend['judul_seri'] : 'Tren historis',
            'min' => $min, 'max' => $max];
    }
}
