export type IndicatorId =
  | "pdb"
  | "inflasi"
  | "fiskal"
  | "investasi"
  | "birate"
  | "tpt";

export type Direction = "up" | "down" | "flat";

export interface IndicatorMeta {
  id: IndicatorId;
  category: string;
  name: string;
  value: string;
  unit: string;
  period: string;
  delta: string;
  deltaDirection: Direction;
  deltaPositive: boolean;
  note: string;
  source: string;
  sourceDate: string;
  sparkline: number[];
  sparklineColor: string;
}

export interface TrendPoint {
  label: string;
  value: number;
}

export interface IndicatorTrend {
  id: IndicatorId;
  name: string;
  unitSuffix: string;
  color: string;
  quarterly: TrendPoint[];
  description: string;
  footnote: string;
  yDomain?: [number, number];
  targetBand?: [number, number];
}

/*jumlah kuarter: mulai 2010 Q1 sampai 2025 Q2 => 61 titik, statis dan deterministik*/
const mulberry32 = (seed: number) => () => {
  seed |= 0;
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

const buildTrend = (
  seed: number,
  start: number,
  drift: number,
  waveAmp: number,
  waveFreq: number,
  noise: number,
  count = 61,
  round = 2,
): TrendPoint[] => {
  const rand = mulberry32(seed);
  const labels: string[] = [];
  for (let i = 0; i < count; i += 1) {
    const year = 2010 + Math.floor(i / 4);
    const quarter = (i % 4) + 1;
    if (year > 2025 || (year === 2025 && quarter > 2)) break;
    labels.push(`Q${quarter} ${year}`);
  }
  return labels.map((label, i) => {
    const wave = Math.sin(i * waveFreq) * waveAmp;
    const wobble = (rand() - 0.5) * 2 * noise;
    const value = start + drift * (i / count) + wave + wobble;
    return { label, value: Number(value.toFixed(round)) };
  });
};

export const indicatorTrends: Record<IndicatorId, IndicatorTrend> = {
  pdb: {
    id: "pdb",
    name: "Pertumbuhan PDB",
    unitSuffix: "% YoY",
    color: "#2563eb",
    quarterly: buildTrend(11, 2.07, 4.2, 2.1, 0.34, 0.4, 61, 2),
    yDomain: [0, 10],
    targetBand: [5, 5.5],
    description:
      "Analisis deret waktu historis, komparasi indikator kuartalan, dan trayektori pertumbuhan ekonomi.",
    footnote: "Catatan: Data PDB disajikan secara year-on-year (YoY) atas dasar harga konstan 2010.",
  },
  inflasi: {
    id: "inflasi",
    name: "Inflasi IHK",
    unitSuffix: "% YoY",
    color: "#16a34a",
    quarterly: buildTrend(29, 4.6, -1.6, 0.9, 0.42, 0.35, 61, 2),
    yDomain: [0, 6],
    description:
      "Trayektori inflasi year-on-year menunjukkan peluruhan dari tekanan harga 2022 menuju titik kendali.",
    footnote: "Catatan: Inflasi diukur dari perubahan Indeks Harga Konsumen terhadap periode yang sama tahun lalu.",
  },
  fiskal: {
    id: "fiskal",
    name: "Defisit APBN",
    unitSuffix: "% PDB",
    color: "#0f172a",
    quarterly: buildTrend(47, -3.4, 2.2, 0.5, 0.31, 0.18, 61, 2),
    yDomain: [-5, 1],
    description:
      "Posisi fiskal terhadap PDB dipantau kuartalan untuk menilai keberlanjutan ruang belanja negara.",
    footnote: "Catatan: Defisit disajikan sebagai persentase terhadap Produk Domestik Bruto nominal.",
  },
  investasi: {
    id: "investasi",
    name: "Realisasi Investasi",
    unitSuffix: "Rp Triliun",
    color: "#0891b2",
    quarterly: buildTrend(73, 210, 220, 28, 0.27, 12, 61, 1),
    yDomain: [100, 520],
    description:
      "Realisasi investasi PMA dan PMDN tiap triwulan menunjukkan ekspansi modal yang konsisten.",
    footnote: "Catatan: Nilai merupakan penjumlahan triwulanan PMA dan PMDN dalam triliun rupiah.",
  },
  birate: {
    id: "birate",
    name: "BI-Rate",
    unitSuffix: "%",
    color: "#7c3aed",
    quarterly: buildTrend(91, 4.5, 0.4, 1.1, 0.21, 0.15, 61, 2),
    yDomain: [3, 7],
    description:
      "Kebijakan suku bunga acuan Bank Indonesia merespons dinamika inflasi dan nilai tukar.",
    footnote: "Catatan: BI-Rate merupakan suku bunga acuan kebijakan moneter Bank Indonesia.",
  },
  tpt: {
    id: "tpt",
    name: "Tingkat Pengangguran Terbuka",
    unitSuffix: "%",
    color: "#ea580c",
    quarterly: buildTrend(113, 6.4, -1.6, 0.4, 0.24, 0.14, 61, 2),
    yDomain: [3, 8],
    description:
      "Tingkat pengangguran terbuka per triwulan menyusut seiring pemulihan lapangan kerja.",
    footnote: "Catatan: TPT merupakan persentase angkatan kerja yang terbuka menganggur (Sakernas).",
  },
};

export const indicatorCards: IndicatorMeta[] = [
  {
    id: "pdb",
    category: "Aktivitas Riil",
    name: "Pertumbuhan PDB",
    value: "5,05",
    unit: "%",
    period: "YoY Q2 2024",
    delta: "+0,11% vs Q1",
    deltaDirection: "up",
    deltaPositive: true,
    note: "Ditopang peningkatan sektor transportasi, pengolangan, dan industri pengolahan dengan kontribusi 0,64% terhadap…",
    source: "BPS",
    sourceDate: "05 Agu 2024",
    sparkline: [2.9, 5.4, 5.0, 4.9, 5.0, 5.01, 5.05],
    sparklineColor: "#2563eb",
  },
  {
    id: "inflasi",
    category: "Stabilisasi Harga",
    name: "Inflasi IHK",
    value: "2,58",
    unit: "%",
    period: "YoY Juli 2024",
    delta: "-0,25% MoM",
    deltaDirection: "down",
    deltaPositive: true,
    note: "Penurunan didorong penurunan telakaran harga volatile food (bawang merah & cabai rawit), seling masuknya musiman…",
    source: "BPS",
    sourceDate: "01 Agu 2024",
    sparkline: [2.9, 2.7, 2.6, 2.75, 2.85, 2.84, 2.58],
    sparklineColor: "#16a34a",
  },
  {
    id: "fiskal",
    category: "Fiskal & Keuangan Negara",
    name: "APBN / Fiskal",
    value: "0,34",
    unit: "%",
    period: "Defisit Thd PDB",
    delta: "Rp77,3 T",
    deltaDirection: "flat",
    deltaPositive: false,
    note: "Kinerja pemasukan pajak dan PBNBP solid, sementara belanja negara tetap terjaga untuk akselerasi belanja perlindungan…",
    source: "Kemenkeu",
    sourceDate: "25 Jul 2024",
    sparkline: [2.2, 1.8, 1.5, 1.1, 0.9, 0.6, 0.34],
    sparklineColor: "#0f172a",
  },
  {
    id: "investasi",
    category: "Rencana Modal",
    name: "Realisasi Investasi",
    value: "Rp428,4",
    unit: "T",
    period: "Q2 2024",
    delta: "+22,5% YoY",
    deltaDirection: "up",
    deltaPositive: true,
    note: "Porsi investasi luar negeri mencapai 24%; domestik diwilayahkan nikmel, tenaga, serta industri manufakturan kelistrikan…",
    source: "BKPM",
    sourceDate: "29 Jul 2024",
    sparkline: [322, 340, 353, 369, 381, 402, 428.4],
    sparklineColor: "#0891b2",
  },
  {
    id: "birate",
    category: "Kebijakan Moneter",
    name: "BI-Rate (Suku Bunga)",
    value: "6,25",
    unit: "%",
    period: "Per Juli 2024",
    delta: "Tetap (Netral)",
    deltaDirection: "flat",
    deltaPositive: false,
    note: "Suku bunga dipertahankan guna memperkuat efektivitas penyampaian instrumen SSR/ SVBI yang nengendoripasi suku…",
    source: "Bank Indonesia",
    sourceDate: "17 Jul 2024",
    sparkline: [6, 5.75, 5.75, 6, 6.25, 6.25, 6.25],
    sparklineColor: "#7c3aed",
  },
  {
    id: "tpt",
    category: "Pasar Kerja",
    name: "Tenaga Kerja (TPT)",
    value: "4,82",
    unit: "%",
    period: "Februari 2024",
    delta: "-0,63% YoY",
    deltaDirection: "down",
    deltaPositive: true,
    note: "Jumlah angkatan kerja bekerja bertambahkan 2,56 juta orang, mayoritas terserap di sektor perdagangan dan pertanian…",
    source: "BPS",
    sourceDate: "06 Mei 2024",
    sparkline: [5.4, 5.3, 5.1, 5.05, 4.9, 4.86, 4.82],
    sparklineColor: "#ea580c",
  },
];

export interface InsightItem {
  statusTag: string;
  statusTone: "green" | "blue" | "orange";
  index: string;
  title: string;
  subtitle: string;
  body: string;
  badgeTitle: string;
  badgeBody: string;
  footerSource: string;
  footerAction: string;
}

export const insightItems: InsightItem[] = [
  {
    statusTag: "Pola Terkonfirmasi — Positif",
    statusTone: "green",
    index: "D-01",
    title: "Broad-Based Growth",
    subtitle: "Pertumbuhan Multisektoral Tanpa Ketergantungan Tunggal",
    body:
      "Pertumbuhan tidak hanya bertumpu pada satu komponen eksternal; mekanisme mentasi di latar manufaktur (4,63%), perdagangan (4,88%), dan transportasi (9,13% pada paremikan) menyentuh ispa. Fenomena ini menunjukkan bantalan terhadap guncangan rilis harga komoditas global yang mengalami normalisasi siklus.",
    badgeTitle: "Indikator Pendukung",
    badgeBody:
      "7 dari 19 sektor lapangan usaha mencatatkan ekspansi tahunan di atas 4,0%.",
    footerSource: "Sumber: BPS (PDB Sektoral)",
    footerAction: "Pelajari Pola Analisis →",
  },
  {
    statusTag: "Pola Ponpungkit — Aktif",
    statusTone: "blue",
    index: "D-02",
    title: "Government-Led & Public Investment",
    subtitle: "Domoplan Belanja Strategis & Pengadaan Infrastruktur",
    body:
      "Percepatan realisasi belanja modal APBN dan kelayakan proyek strategis infrastruktur menunjukkan konevitansi logistik antarwilayah. Stimulus ini melefit mengompensasi pengentasan likuiditas global dan mengondiring spillover ke penguntaan tenaga kerja konstruksi.",
    badgeTitle: "Investasi",
    badgeBody:
      "48,2% realisasi belanja modal kementerian terserap pada paruh pertama tahun berjalan.",
    footerSource: "Sumber: Kemenkeu & BKPM",
    footerAction: "Pelajari Pola Analisis →",
  },
  {
    statusTag: "Pola Perhatian — Moderat",
    statusTone: "orange",
    index: "D-03",
    title: "Private Demand Resilience",
    subtitle: "Dramatika Daya Beli & Pengeluaran Konsumen",
    body:
      "Konsumsi rumah tangga menopang normalisasi pasca-siklus Ramadan—diutilis. Perpandalan inflasi pangan berangkat yangang sukses memberi ruang pemulihan daya beli kecil, kental arus kilas pada belanja non-makanan menumukan ketaati-hati-an.",
    badgeTitle: "Indikator Pendukung",
    badgeBody:
      "INK 123,4. Pola tetap berada di zona optimis (>100) menurut survei berkelitok konsumen Bank Indonesia.",
    footerSource: "Sumber: Survei Konsumen BI",
    footerAction: "Pelajari Pola Analisis →",
  },
];
