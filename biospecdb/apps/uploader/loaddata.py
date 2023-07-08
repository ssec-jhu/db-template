from pathlib import Path
from tempfile import TemporaryFile

from django.core.exceptions import ValidationError
from django.core.files import File
from django.utils.translation import gettext_lazy as _

import pandas as pd

import biospecdb.util


def save_data_to_db(meta_data_file, spectral_data_file):
    from .models import BioSample, Disease, Instrument, Patient, SpectralData, Symptom, UploadedFile, Visit

    # TODO: Rip this out of here and to some other func elsewhere (perhaps utils).
    # Read in all data.
    meta_data = biospecdb.util.read_meta_data(meta_data_file)
    spec_data = biospecdb.util.read_spectral_data_table(spectral_data_file)

    # Files must be of equal length (same number of rows).
    if len(meta_data) != len(spec_data):
        raise ValidationError(_("meta and spectral data must be of equal length (%(a)i!=%(b)i)."),
                              params={"a": len(meta_data), "b": len(spec_data)},
                              code="invalid")

    # Join and check primary keys are unique and associative.
    try:
        data = meta_data.join(spec_data, validate="1:1")
    except pd.errors.MergeError as error:
        raise ValidationError(_("meta and spectral data must have unique and identical patient IDs")) from error

    # Ingest into db.
    # TODO: Should this go in self.save() instead?
    for index, row in data.iterrows():
        # NOTE: The patter for column lookup is to use get(..., default=None) and defer the field validation, i.e.,
        # whether null/blank etc., to the actual field def.

        # Patient
        try:
            # NOTE: ValidationError is raised when ``index`` is not a UUID.
            patient = Patient.objects.get(pk=index)
        except (Patient.DoesNotExist, ValidationError):
            # Create new (in mem only - not saved to db).
            gender = row.get(Patient.gender.field.verbose_name.lower())
            patient = Patient(gender=Patient.Gender(gender))
            patient.full_clean()
            patient.save()

        # Visit
        visit = Visit(patient=patient,
                      patient_age=row.get(Visit.patient_age.field.verbose_name.lower()),
                      )  # TODO: Add logic to auto-find previous_visit.
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
                                        data=File(data_file, name=data_filename))
            biosample.spectral_data.add(spectraldata, bulk=False)
            instrument.spectral_data.add(spectraldata, bulk=False)
            spectraldata.full_clean()
            spectraldata.save()

        # Symptoms
        # TODO: For symptom/disease parsing see https://github.com/ssec-jhu/biospecdb/issues/30 (aliases).
        for disease in Disease.objects.all():
            symptom_value = row.get(disease.alias.lower(), None)
            if not symptom_value:
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
