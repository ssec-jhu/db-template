from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from openpyxl import load_workbook
from .forms import FileUploadForm, DataInputForm
from uploader.models import Patient, Visit, SpectralData, BioSample, Symptom


def home(request):
    return render(request, 'home.html')


@staff_member_required
def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            #return render(request, 'UploadSuccess.html')
            return display_xlsx(request)
    else:
        form = FileUploadForm()
    return render(request, 'MetadataFileUpload.html', {'form': form})


@staff_member_required
def display_xlsx(request):
    workbook = load_workbook('./biospecdb/apps/uploader/uploads/METADATA_barauna2021ultrarapid.xlsx')
    worksheet = workbook.active
    data = []
    for row in worksheet.iter_rows(values_only=True):
        data.append(row)
    return render(request, 'MetadataDisplay.html', {'data': data})


@staff_member_required
def data_input(request):
    if request.method == 'POST':
        form = DataInputForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()  # Save data to database.
            patient_id = form.cleaned_data["patient_id"]
            return render(request, 'DataInputForm_Success.html', {'form': form, 'patient_id': patient_id})
        
    elif request.method == 'GET':
        patient_id = request.GET.get('patient_id')
        if patient_id:
            try:
                patient = Patient.objects.get(patient_id=patient_id)
                last_visit = Visit.objects.filter(patient_id=patient_id).order_by('created_at').last()
                biosample = BioSample.objects.get(visit=last_visit)
                last_visit_symptoms = Symptom.objects.filter(visit=last_visit)
                symptom = last_visit_symptoms.order_by('days_symptomatic').last()
                spectraldata = SpectralData.objects.get(bio_sample=biosample)      
                initial_data={
                    'patient_id': patient_id,
                    'gender': patient.gender,
                    'days_symptomatic': symptom.days_symptomatic,
                    'patient_age': last_visit.patient_age,
                    'spectra_measurement': spectraldata.spectra_measurement,
                    'instrument': spectraldata.instrument,
                    'acquisition_time': spectraldata.acquisition_time,
                    'n_coadditions': spectraldata.n_coadditions,
                    'resolution': spectraldata.resolution,
                    'sample_type': biosample.sample_type,
                    'sample_processing': biosample.sample_processing,
                    'freezing_temp': biosample.freezing_temp,
                    'thawing_time': biosample.thawing_time,
                    'spectral_data': spectraldata.data.name
                }
                for symptom in last_visit_symptoms:
                    if symptom.disease.value_class == "BOOL":
                        if symptom.disease_value == 'True':
                            initial_data[symptom.disease.name] = True
                        else:
                            initial_data[symptom.disease.name] = False
                    else:
                        initial_data[symptom.disease.name] = symptom.disease_value
                form = DataInputForm(initial=initial_data)
                return render(request, 'DataInputForm.html', {'form': form})
            
            except (Patient.DoesNotExist, Visit.DoesNotExist, BioSample.DoesNotExist, SpectralData.DoesNotExist):
                return render(request, 'DataSearchForm_Failure.html', {'patient_id': patient_id})
        else:
            form = DataInputForm()
        
    else:
        form = DataInputForm()
        
    return render(request, 'DataInputForm.html', {'form': form})
