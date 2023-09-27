from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import HttpResponse
from openpyxl import load_workbook
from .forms import FileUploadForm, DataInputForm
from uploader.models import Patient, Visit, SpectralData, BioSample

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
    else:
        form = DataInputForm()
        
    return render(request, 'DataInputForm.html', {'form': form})


def data_search(request):
    if request.method == 'GET':
        patient_id = request.GET.get('patient_id')
        if patient_id:
            try:
                patient = Patient.objects.get(patient_id=patient_id)
                visit = Visit.objects.get(patient_id=patient_id)
                biosample = BioSample.objects.get(visit=visit)
                spectraldata = SpectralData.objects.get(bio_sample=biosample)

                form = DataInputForm(
                    initial={
                        'patient_id': patient_id,
                        'gender': patient.gender,
                        'patient_age': visit.patient_age,
                        'instrument': spectraldata.instrument,
                        'spectra_measurement': spectraldata.spectra_measurement,
                        'acquisition_time': spectraldata.acquisition_time,
                        'n_coadditions': spectraldata.n_coadditions,
                        'resolution': spectraldata.resolution,
                        'sample_type': biosample.sample_type,
                        'sample_processing': biosample.sample_processing,
                        'freezing_temp': biosample.freezing_temp,
                        'thawing_time': biosample.thawing_time 
                    }
                )
                return render(request, 'DataInputForm.html', {'form': form})
            except (Patient.DoesNotExist, Visit.DoesNotExist, BioSample.DoesNotExist, SpectralData.DoesNotExist):
                #form = DataInputForm()
                #request.method = 'PUT'
                return render(request, 'DataSearchForm_Failure.html', {'patient_id': patient_id})
        else:
            form = DataInputForm()
            return render(request, 'DataSearchForm.html', {'form': form})
    elif request.method == 'PUT':
        pass # Handle the PUT request here if needed

    return HttpResponse(status=405)  # Return a Method Not Allowed response
