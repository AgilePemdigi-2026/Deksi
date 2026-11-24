from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar = [('indicators', '0023_bis_source_choices')]

    operations: ClassVar = [
        migrations.AlterField(model_name='source', name='acquisition_method',
            field=models.CharField(blank=True, db_default='', default='', max_length=32, choices=[
                ('api_bps', 'API resmi (WebAPI BPS)'),
                ('api_bis', 'API BIS (suku bunga Indonesia)'),
                ('pdf_kita', 'PDF resmi (APBN KiTa Kemenkeu)'),
                ('file_xlsx', 'File resmi (XLSX dataset)'),
                ('file_zip_csv', 'File resmi (ZIP berisi CSV)'),
                ('web_bi', 'Sinkronisasi online (tabel resmi BI)'),
                ('web_bkpm', 'Sinkronisasi online (pratinjau publik BKPM)'),
                ('web_kemenkeu', 'Sinkronisasi online (arsip APBN KiTa)'),
            ])),
    ]
