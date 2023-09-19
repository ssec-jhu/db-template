from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from openpyxl import load_workbook
from .forms import FileUploadForm, DataInputForm


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
            if form:
                form.save()  # Save data to database.
                patient_id = form.cleaned_data["patient_id"]
                return render(request, 'DataInputForm_Success.html', {'form': form, 'patient_id': patient_id})
            else:
                form = load_form_from_db(request, form.patient_id)
                patient_id = form.cleaned_data["patient_id"]
                return render(request, 'DataInputForm.html', {'form': form})
        
    else:
        form = DataInputForm()
        
    return render(request, 'DataInputForm.html', {'form': form})

def load_form_from_db(request, patient_id):
    """
    Ingest into the database large tables of symptom & disease data (aka "meta" data) along with associated spectral
    data.

    Note: Data can be passed in pre-joined, i.e., save_data_to_db(None, None, joined_data). If so, data can't be
          validated.
    Note: This func is called by UploadedFile.clean() which, therefore, can't also be called here.
    """
        
    from uploader.models import Patient, Visit
    from uploader.forms import DataInputForm
    from django.http import HttpResponse
    from django.core.exceptions import ValidationError
    
    try:
        patient = Patient.objects.get(patient_id = patient_id)
    except (Patient.DoesNotExist, ValidationError):
        return HttpResponse(patient_id = patient_id)     
    form = DataInputForm()
    form.patient_id = patient.patient_id
    form.gender = patient.gender

    try:
        visit = Visit.objects.get(patient = patient)
    except (Visit.DoesNotExist, ValidationError):
        return HttpResponse(patient = patient)
    form.patient_age - visit.patient_age
    
    return render(request, 'DataInputForm.html', {'form': form, 'patient_id': patient_id})
