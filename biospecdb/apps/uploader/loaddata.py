from pathlib import Path
from tempfile import TemporaryFile

import pandas as pd
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction

import biospecdb.util


@transaction.atomic
def save_data_to_db(meta_data, spectral_data, joined_data=None, validate=True):
    """
    Ingest into the database large tables of symptom & disease data (aka "meta" data) along with associated spectral
    data.

    Note: Data can be passed in pre-joined, i.e., save_data_to_db(None, None, joined_data). If so, data can't be
          validated.
    Note: This func is called by UploadedFile.clean() which, therefore, can't also be called here.
    """
    from uploader.models import BioSample, Disease, Instrument, Patient, SpectralData, Symptom, UploadedFile, Visit

    if joined_data is None:
        # Read in all data.
        meta_data = meta_data if isinstance(meta_data, pd.DataFrame) else biospecdb.util.read_meta_data(meta_data)
        spec_data = spectral_data if isinstance(spectral_data, pd.DataFrame) else \
            biospecdb.util.read_spectral_data_table(spectral_data)

        if validate:
            UploadedFile.validate_lengths(meta_data, spec_data)
            # This uses a join so returns the joined data so that it doesn't go to waste if needed, which it is here.
            joined_data = UploadedFile.validate_primary_keys(meta_data, spec_data)
    else:
        if validate:
            raise ValueError("When using pre-joined data, validation isn't possible so please pre-validate and "
                             "pass ``validate=False``.")

    # Ingest into db.
    for index, row in joined_data.iterrows():
        # NOTE: The pattern for column lookup is to use get(..., default=None) and defer the field validation, i.e.,
        # whether null/blank etc., to the actual field def.

        # Patient
        try:
            # NOTE: ValidationError is raised when ``index`` is not a UUID.
            patient = Patient.objects.get(pk=index)
        except (Patient.DoesNotExist, ValidationError):
            gender = row.get(Patient.gender.field.verbose_name.lower())
            patient = Patient(gender=Patient.Gender(gender))
            patient.full_clean()

            patient.save()

        # Visit
        visit = Visit(patient=patient,
                      patient_age=row.get(Visit.patient_age.field.verbose_name.lower()),
                      )  # TODO: Add logic to auto-find previous_visit. https://github.com/ssec-jhu/biospecdb/issues/37
        visit.full_clean()
        visit.save()

        # BioSample
        biosample = BioSample(visit=visit,
                              sample_type=BioSample.SampleKind(
                                  row.get(BioSample.sample_type.field.verbose_name.lower())),
                              sample_processing=row.get(BioSample.sample_processing.field.verbose_name.lower()),
                              freezing_temp=row.get(BioSample.freezing_temp.field.verbose_name.lower()),
                              thawing_time=row.get(BioSample.thawing_time.field.verbose_name.lower()))
        visit.bio_sample.add(biosample, bulk=False)
        biosample.full_clean()
        biosample.save()

        # SpectralData
        spectrometer = Instrument.Spectrometers(row.get(Instrument.spectrometer.field.verbose_name.lower()))
        atr_crystal = Instrument.SpectrometerCrystal(row.get(Instrument.atr_crystal.field.verbose_name.lower()))
        try:
            instrument = Instrument.objects.get(spectrometer=spectrometer, atr_crystal=atr_crystal)
        except Instrument.DoesNotExist:
            instrument = Instrument(spectrometer=spectrometer, atr_crystal=atr_crystal)
            instrument.full_clean()
            instrument.save()  # Makes sense to save this now for reuse in future data rows.

        # Create datafile
        wavelengths = row["wavelength"]
        intensities = row["intensity"]

        with TemporaryFile("w+") as data_file:
            # Write data to tempfile.
            biospecdb.util.spectral_data_to_csv(data_file, wavelengths, intensities)
            data_filename = Path(str(Visit)).with_suffix(str(UploadedFile.FileFormats.CSV))

            spectraldata = SpectralData(instrument=instrument,
                                        bio_sample=biosample,
                                        spectra_measurement=SpectralData.SpectralMeasurementKind(
                                            row.get(SpectralData.spectra_measurement.field.verbose_name.lower())
                                        ),
                                        acquisition_time=row.get(
                                            SpectralData.acquisition_time.field.verbose_name.lower()),
                                        n_coadditions=row.get(SpectralData.n_coadditions.field.verbose_name.lower()),
                                        resolution=row.get(SpectralData.resolution.field.verbose_name.lower()),

                                        # TODO: See https://github.com/ssec-jhu/biospecdb/issues/40
                                        data=File(data_file, name=data_filename))
            biosample.spectral_data.add(spectraldata, bulk=False)

            instrument.spectral_data.add(spectraldata, bulk=False)
            spectraldata.full_clean()
            spectraldata.save()

        # Symptoms
        for disease in Disease.objects.all():
            symptom_value = row.get(disease.alias.lower(), None)
            if symptom_value is None:
                continue

            if disease.value_class:
                symptom_value = Disease.Types(disease.value_class).cast(symptom_value)
                symptom = Symptom(disease=disease, visit=visit, is_symptomatic=True, disease_value=symptom_value)
            else:
                symptom_value = biospecdb.util.to_bool(symptom_value)
                symptom = Symptom(disease=disease, visit=visit, is_symptomatic=symptom_value)

            disease.symptom.add(symptom, bulk=False)
            symptom.full_clean()
            symptom.save()
