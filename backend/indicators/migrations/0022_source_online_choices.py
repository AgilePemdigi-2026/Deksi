from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar = [('indicators', '0021_source_archived')]

    # Choices only: never enable online acquisition or rewrite an existing source here.
    operations: ClassVar = [
        migrations.AlterField(model_name='source', name='acquisition_method',
            field=models.CharField(blank=True, db_default='', default='', max_length=32, choices=[
                ('api_bps', 'API resmi (WebAPI BPS)'),
                ('pdf_kita', 'PDF resmi (APBN KiTa Kemenkeu)'),
                ('file_xlsx', 'File resmi (XLSX dataset)'),
                ('file_zip_csv', 'File resmi (ZIP berisi CSV)'),
                ('web_bi', 'Sinkronisasi online (tabel resmi BI)'),
                ('web_bkpm', 'Sinkronisasi online (pratinjau publik BKPM)'),
            ])),
        migrations.AlterField(model_name='source', name='data_format',
            field=models.CharField(blank=True, db_default='', default='', max_length=16, choices=[
                ('json', 'JSON'), ('html', 'HTML'), ('pdf', 'PDF'), ('xlsx', 'XLSX'), ('zip_csv', 'ZIP-CSV'),
            ])),
    ]
