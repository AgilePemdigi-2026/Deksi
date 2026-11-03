import { useEffect, useRef } from 'react'
import mediaText from '../assets/editorial/credits.json?raw'
import { BrandMark } from './EditorialLanding'

const media = JSON.parse(mediaText) as { sources: { key: string; title: string; artist: string; source: string | null; license: string; license_url: string | null }[] }

export function EditorialInfo({ open, onClose }: { open: boolean; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal()
    else if (!open && dialog.current?.open) dialog.current.close()
  }, [open])
  return <dialog ref={dialog} className="presentation-dialog" aria-labelledby="presentation-title" onClose={onClose}>
    <div className="presentation-dialog-head"><h2 id="presentation-title">Sumber & konteks.</h2><button type="button" onClick={() => dialog.current?.close()} aria-label="Tutup informasi">×</button></div>
    <p>Halaman publik tidak memerlukan akun. Nilai indikator dan grafik mengikuti API DEKSI; nama institusi atau tautan portal saja tidak membuktikan sebuah angka sudah diverifikasi.</p>
    <p>Detail Indikator dan Source Trace yang terikat pada observasi/revisi akan diintegrasikan melalui branch fitur 6 dan 7. Narasi referensi yang diberi label bukan hasil analisis dari API.</p>
    <h3>Kredit visual</h3><p>Semua foto adalah ilustrasi. Perubahan: pemotongan, monokrom, kontras dan pelembutan tepi. Tidak ada dukungan atau kemitraan yang tersirat.</p>
    <p><strong>Gerbang publikasi:</strong> hak publikasi foto hero dari pengguna belum dikonfirmasi. Aset ini dipertahankan untuk porting lokal sesuai pilihan desain, bukan dinyatakan bebas lisensi.</p>
    <ul className="media-credit-list">{media.sources.map(source => <li key={source.key}><strong>{source.title}</strong><span>{source.artist} · {source.license}</span>{source.source?.startsWith('https://') && <a href={source.source} target="_blank" rel="noopener noreferrer">Halaman sumber ↗</a>}{source.license_url?.startsWith('https://') && <a href={source.license_url} target="_blank" rel="noopener noreferrer">Lisensi ↗</a>}</li>)}</ul>
  </dialog>
}

export function EditorialFooter({ onInfo }: { onInfo: () => void }) {
  return <footer className="editorial-footer" id="tentang">
    <div><a className="footer-wordmark" href="#dashboard" aria-label="DEKSI, kembali ke awal"><BrandMark />DEKSI</a><p>Deteksi Ekonomi Indonesia.<br />Data, konteks, dan sumber dibaca bersama.</p><p className="footer-fine">Publik tanpa akun. Metadata sumber<br />bukan klaim kemitraan atau verifikasi.</p></div>
    <div><h2>PORTAL INSTITUSI</h2><a href="https://www.bps.go.id/" target="_blank" rel="noopener noreferrer">Badan Pusat Statistik ↗</a><a href="https://www.bi.go.id/" target="_blank" rel="noopener noreferrer">Bank Indonesia ↗</a><a href="https://www.kemenkeu.go.id/" target="_blank" rel="noopener noreferrer">Kementerian Keuangan ↗</a><a href="https://www.bkpm.go.id/" target="_blank" rel="noopener noreferrer">Kementerian Investasi / BKPM ↗</a></div>
    <div><h2>TRANSPARANSI</h2><button type="button" onClick={onInfo}>Cara membaca data ↗</button><button type="button" onClick={onInfo}>Sumber & kredit visual ↗</button><a href="#/admin/sumber">Admin · Kelola Sumber ↗</a></div>
  </footer>
}
