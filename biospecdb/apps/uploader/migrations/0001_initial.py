# Generated by Django 4.2.7 on 2024-02-12 20:26

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.functions.text
import uploader.base_models
import uploader.models
import user.models
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
            name='ObservationsView',
            fields=[
                ('observable', models.CharField(db_column='observable', max_length=128)),
                ('value_class', models.CharField(choices=[('BOOL', 'Bool'), ('STR', 'Str'), ('INT', 'Int'), ('FLOAT', 'Float')], default='BOOL', max_length=128)),
                ('days_observed', models.IntegerField(blank=True, default=None, help_text='Supersedes Visit.days_observed', null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Days observed')),
                ('observable_value', models.CharField(blank=True, default='', max_length=128, null=True)),
                ('visit_id', models.BigIntegerField(primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'v_observations',
                'managed': False,
            },
            bases=(uploader.base_models.SqlView, models.Model),
        ),
        migrations.CreateModel(
            name='VisitObservationsView',
            fields=[
                ('visit_id', models.BigIntegerField(primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'v_visit_observations',
                'managed': False,
            },
            bases=(uploader.base_models.SqlView, models.Model),
        ),
        migrations.CreateModel(
            name='BioSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sample_cid', models.CharField(blank=True, max_length=256, null=True, verbose_name='Sample CID')),
                ('sample_study_id', models.CharField(blank=True, max_length=256, null=True, verbose_name='Sample Study ID')),
                ('sample_study_name', models.CharField(blank=True, max_length=256, null=True, verbose_name='Sample Study Name')),
                ('sample_processing', models.CharField(blank=True, max_length=128, null=True, verbose_name='Sample Processing Description')),
                ('sample_extraction', models.CharField(blank=True, max_length=128, null=True, verbose_name='Sample Extraction Description')),
                ('sample_extraction_tube', models.CharField(blank=True, max_length=128, null=True, verbose_name='Sample Extraction Tube Brand Name')),
                ('centrifuge_time', models.IntegerField(blank=True, null=True, verbose_name='Extraction Tube Centrifuge Time (s)')),
                ('centrifuge_rpm', models.IntegerField(blank=True, null=True, verbose_name='Extraction Tube Centrifuge RPM')),
                ('freezing_temp', models.FloatField(blank=True, null=True, verbose_name='Freezing Temperature (C)')),
                ('thawing_temp', models.FloatField(blank=True, null=True, verbose_name='Thawing Temperature (C)')),
                ('thawing_time', models.IntegerField(blank=True, null=True, verbose_name='Thawing time (s)')),
                ('freezing_time', models.IntegerField(blank=True, null=True, verbose_name='Freezing time (s)')),
            ],
            options={
                'db_table': 'bio_sample',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='BioSampleType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=128, verbose_name='Sample Type')),
            ],
            options={
                'db_table': 'bio_sample_type',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='Center',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=128)),
                ('country', models.CharField(max_length=128, validators=[user.models.validate_country])),
            ],
            options={
                'abstract': False,
                'unique_together': {('name', 'country')},
            },
        ),
        migrations.CreateModel(
            name='Instrument',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True, verbose_name='instrument id')),
                ('cid', models.CharField(max_length=128, verbose_name='instrument cid')),
                ('manufacturer', models.CharField(max_length=128, verbose_name='Instrument manufacturer')),
                ('model', models.CharField(max_length=128, verbose_name='Instrument model')),
                ('serial_number', models.CharField(max_length=128, verbose_name='Instrument SN#')),
                ('spectrometer_manufacturer', models.CharField(max_length=128, verbose_name='Spectrometer manufacturer')),
                ('spectrometer_model', models.CharField(max_length=128, verbose_name='Spectrometer model')),
                ('spectrometer_serial_number', models.CharField(max_length=128, verbose_name='Spectrometer SN#')),
                ('laser_manufacturer', models.CharField(max_length=128, verbose_name='Laser manufacturer')),
                ('laser_model', models.CharField(max_length=128, verbose_name='Laser model')),
                ('laser_serial_number', models.CharField(max_length=128, verbose_name='Laser SN#')),
                ('center', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='uploader.center')),
            ],
            options={
                'db_table': 'instrument',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='Observable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.CharField(choices=[('BLOODWORK', 'Bloodwork'), ('COMORBIDITY', 'Comorbidity'), ('DRUG', 'Drug'), ('PATIENT_INFO', 'Patient Info'), ('PATIENT_INFO_II', 'Patient Info Ii'), ('PATIENT_PREP', 'Patient Prep'), ('SYMPTOM', 'Symptom'), ('TEST', 'Test'), ('VITALS', 'Vitals')], max_length=128)),
                ('name', models.CharField(max_length=128)),
                ('description', models.CharField(max_length=256)),
                ('alias', models.CharField(help_text='Alias column name for bulk data ingestion from .csv, etc.', max_length=128)),
                ('value_class', models.CharField(choices=[('BOOL', 'Bool'), ('STR', 'Str'), ('INT', 'Int'), ('FLOAT', 'Float')], default='BOOL', max_length=128)),
                ('value_choices', models.CharField(blank=True, help_text="Supply comma separated text choices for STR value_classes. E.g., 'LOW, MEDIUM, HIGH'", max_length=512, null=True)),
                ('validator', models.CharField(blank=True, help_text="This must be the fully qualified Python name. E.g., 'django.core.validators.validate_email'.", max_length=128, null=True, validators=[uploader.models.validate_import])),
                ('center', models.ManyToManyField(blank=True, help_text='Only visible to users of these centers.\nSelecting none is equivalent to all.', related_name='observable', to='uploader.center')),
                ('default', models.ManyToManyField(blank=True, help_text='Automatically add an observation of this observable to the data input form for users of these centers.\nSelecting none is equivalent to all.', related_name='observable_default', to='uploader.center')),
            ],
            options={
                'db_table': 'observable',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient_id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True, verbose_name='Patient ID')),
                ('patient_cid', models.CharField(blank=True, help_text='Patient ID prescribed by the associated center', max_length=128, null=True)),
                ('center', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='uploader.center')),
            ],
            options={
                'db_table': 'patient',
                'get_latest_by': 'updated_at',
                'unique_together': {('patient_cid', 'center')},
            },
        ),
        migrations.CreateModel(
            name='QCAnnotator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=128, unique=True)),
                ('fully_qualified_class_name', models.CharField(help_text="This must be the fully qualified Python name for an implementation of QCFilter, e.g.,'myProject.qc.myQCFilter'.", max_length=128, unique=True, validators=[uploader.models.validate_qc_annotator_import])),
                ('value_type', models.CharField(choices=[('BOOL', 'Bool'), ('STR', 'Str'), ('INT', 'Int'), ('FLOAT', 'Float')], default='BOOL', max_length=128)),
                ('description', models.CharField(blank=True, max_length=256, null=True)),
                ('default', models.BooleanField(default=True, help_text='If True it will apply to all spectral data samples.')),
            ],
            options={
                'db_table': 'qc_annotator',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='SpectraMeasurementType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=128, verbose_name='Spectra Measurement')),
            ],
            options={
                'db_table': 'spectra_measurement_type',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('days_observed', models.IntegerField(blank=True, default=None, help_text='Applies to all visit observations unless otherwise specified', null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Days observed')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visit', to='uploader.patient')),
                ('previous_visit', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_visit', to='uploader.visit')),
            ],
            options={
                'db_table': 'visit',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='UploadedFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('meta_data_file', models.FileField(help_text='File containing rows of all patient, observation, and other meta data.', upload_to='raw_data/', validators=[django.core.validators.FileExtensionValidator(['csv', 'xlsx', 'jsonl'])])),
                ('spectral_data_file', models.FileField(help_text='File containing rows of spectral intensities for the corresponding meta data file.', upload_to='raw_data/', validators=[django.core.validators.FileExtensionValidator(['csv', 'xlsx', 'jsonl'])])),
                ('center', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='uploader.center')),
            ],
            options={
                'verbose_name': 'Bulk Data Upload',
                'db_table': 'bulk_upload',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='SpectralData',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True)),
                ('measurement_id', models.CharField(blank=True, max_length=128, null=True)),
                ('atr_crystal', models.CharField(blank=True, max_length=128, null=True, verbose_name='ATR Crystal')),
                ('n_coadditions', models.IntegerField(blank=True, null=True, verbose_name='Number of coadditions')),
                ('acquisition_time', models.IntegerField(blank=True, null=True, verbose_name='Acquisition time [s]')),
                ('resolution', models.IntegerField(blank=True, null=True, verbose_name='Resolution [cm-1]')),
                ('power', models.FloatField(blank=True, max_length=128, null=True, verbose_name='Power incident to the sample [mW]')),
                ('temperature', models.FloatField(blank=True, max_length=128, null=True, verbose_name='Temperature [C]')),
                ('pressure', models.FloatField(blank=True, max_length=128, null=True, verbose_name='Pressure [bar]')),
                ('humidity', models.FloatField(blank=True, max_length=128, null=True, verbose_name='Humidity [%]')),
                ('date', models.DateTimeField(blank=True, null=True)),
                ('sers_description', models.CharField(blank=True, max_length=128, null=True, verbose_name='SERS description')),
                ('sers_particle_material', models.CharField(blank=True, max_length=128, null=True, verbose_name='SERS particle material')),
                ('sers_particle_size', models.FloatField(blank=True, null=True, verbose_name='SERS particle size [μm]')),
                ('sers_particle_concentration', models.FloatField(blank=True, null=True, verbose_name='SERS particle concentration')),
                ('data', models.FileField(max_length=256, upload_to='spectral_data/', validators=[django.core.validators.FileExtensionValidator(['csv', 'xlsx', 'jsonl'])], verbose_name='Spectral data file')),
                ('bio_sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spectral_data', to='uploader.biosample')),
                ('instrument', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spectral_data', to='uploader.instrument')),
                ('measurement_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spectral_data', to='uploader.spectrameasurementtype', verbose_name='Measurement type')),
            ],
            options={
                'verbose_name': 'Spectral Data',
                'verbose_name_plural': 'Spectral Data',
                'db_table': 'spectral_data',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.CreateModel(
            name='Observation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('days_observed', models.IntegerField(blank=True, default=None, help_text='Supersedes Visit.days_observed', null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Days observed')),
                ('observable_value', models.CharField(blank=True, default='', max_length=128, null=True)),
                ('observable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='observation', to='uploader.observable')),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='observation', to='uploader.visit')),
            ],
            options={
                'db_table': 'observation',
                'get_latest_by': 'updated_at',
            },
        ),
        migrations.AddField(
            model_name='biosample',
            name='sample_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bio_sample', to='uploader.biosampletype', verbose_name='Sample Type'),
        ),
        migrations.AddField(
            model_name='biosample',
            name='visit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bio_sample', to='uploader.visit'),
        ),
        migrations.CreateModel(
            name='QCAnnotation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('value', models.CharField(blank=True, max_length=128, null=True)),
                ('annotator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qc_annotation', to='uploader.qcannotator')),
                ('spectral_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qc_annotation', to='uploader.spectraldata')),
            ],
            options={
                'db_table': 'qc_annotation',
                'get_latest_by': 'updated_at',
                'unique_together': {('annotator', 'spectral_data')},
            },
        ),
        migrations.AddConstraint(
            model_name='observable',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name'), name='unique_observable_name'),
        ),
        migrations.AddConstraint(
            model_name='observable',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('alias'), name='unique_alias_name'),
        ),
    ]
