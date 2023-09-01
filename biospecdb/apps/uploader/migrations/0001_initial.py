# Generated by Django 4.2.1 on 2023-09-01 12:21

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.functions.text
import uploader.base_models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FullPatientView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'full_patient',
                'managed': False,
            },
            bases=(uploader.base_models.SqlView, models.Model),
        ),
        migrations.CreateModel(
            name='SymptomsView',
            fields=[
                ('disease', models.CharField(db_column='disease', max_length=128)),
                ('value_class', models.CharField(choices=[('BOOL', 'Bool'), ('STR', 'Str'), ('INT', 'Int'), ('FLOAT', 'Float')], default='BOOL', max_length=128)),
                ('days_symptomatic', models.IntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Days of Symptoms onset')),
                ('severity', models.IntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)])),
                ('disease_value', models.CharField(blank=True, max_length=128, null=True)),
                ('visit_id', models.BigIntegerField(primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'v_symptoms',
                'managed': False,
            },
            bases=(uploader.base_models.SqlView, models.Model),
        ),
        migrations.CreateModel(
            name='VisitSymptomsView',
            fields=[
                ('visit_id', models.BigIntegerField(primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'v_visit_symptoms',
                'managed': False,
            },
            bases=(uploader.base_models.SqlView, models.Model),
        ),
        migrations.CreateModel(
            name='BioSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sample_type', models.CharField(choices=[('PHARYNGEAL_SWAB', 'Pharyngeal Swab')], default='PHARYNGEAL_SWAB', max_length=128, verbose_name='Sample Type')),
                ('sample_processing', models.CharField(blank=True, default='None', max_length=128, null=True, verbose_name='Sample Processing')),
                ('freezing_temp', models.FloatField(blank=True, null=True, verbose_name='Freezing Temperature')),
                ('thawing_time', models.IntegerField(blank=True, null=True, verbose_name='Thawing time')),
            ],
        ),
        migrations.CreateModel(
            name='Disease',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('description', models.CharField(max_length=256)),
                ('alias', models.CharField(help_text='Alias column name for bulk data ingestion from .csv, etc.', max_length=128)),
                ('value_class', models.CharField(choices=[('BOOL', 'Bool'), ('STR', 'Str'), ('INT', 'Int'), ('FLOAT', 'Float')], default='BOOL', max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Instrument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spectrometer', models.CharField(choices=[('AGILENT_CORY_630', 'Agilent Cory 630')], default='AGILENT_CORY_630', max_length=128, verbose_name='Spectrometer')),
                ('atr_crystal', models.CharField(choices=[('ZNSE', 'Znse')], default='ZNSE', max_length=128, verbose_name='ATR Crystal')),
            ],
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('patient_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female')], max_length=8, null=True, verbose_name='Gender (M/F)')),
            ],
        ),
        migrations.CreateModel(
            name='UploadedFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meta_data_file', models.FileField(help_text='File containing rows of all patient, symptom, and other meta data.', upload_to='raw_data/', validators=[django.core.validators.FileExtensionValidator(['csv', 'xlsx'])])),
                ('spectral_data_file', models.FileField(help_text='File containing rows of spectral intensities for the corresponding meta data file.', upload_to='raw_data/', validators=[django.core.validators.FileExtensionValidator(['csv', 'xlsx'])])),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('patient_age', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(150)], verbose_name='Age')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visit', to='uploader.patient')),
                ('previous_visit', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_visit', to='uploader.visit')),
            ],
        ),
        migrations.CreateModel(
            name='Symptom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('days_symptomatic', models.IntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Days of Symptoms onset')),
                ('severity', models.IntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)])),
                ('disease_value', models.CharField(blank=True, max_length=128, null=True)),
                ('disease', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='symptom', to='uploader.disease')),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='symptom', to='uploader.visit')),
            ],
        ),
        migrations.CreateModel(
            name='SpectralData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spectra_measurement', models.CharField(choices=[('ATR_FTIR', 'Atr Ftir')], default='ATR_FTIR', max_length=128, verbose_name='Spectra Measurement')),
                ('acquisition_time', models.IntegerField(blank=True, null=True, verbose_name='Acquisition time [s]')),
                ('n_coadditions', models.IntegerField(default=32, verbose_name='Number of coadditions')),
                ('resolution', models.IntegerField(blank=True, null=True, verbose_name='Resolution [cm-1]')),
                ('data', models.FileField(upload_to='spectral_data/', validators=[django.core.validators.FileExtensionValidator(['csv', 'xlsx'])])),
                ('bio_sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spectral_data', to='uploader.biosample')),
                ('instrument', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spectral_data', to='uploader.instrument')),
            ],
        ),
        migrations.AddConstraint(
            model_name='disease',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name'), name='unique_disease_name'),
        ),
        migrations.AddConstraint(
            model_name='disease',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('alias'), name='unique_alias_name'),
        ),
        migrations.AddField(
            model_name='biosample',
            name='visit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bio_sample', to='uploader.visit'),
        ),
    ]
