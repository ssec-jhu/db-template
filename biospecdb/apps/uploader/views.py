from django.shortcuts import render
from openpyxl import load_workbook
from .forms import FileUploadForm, DataInputForm


def home(request):
    return render(request, 'home.html')


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


def display_xlsx(request):
    workbook = load_workbook('./biospecdb/apps/uploader/uploads/METADATA_barauna2021ultrarapid.xlsx')
    worksheet = workbook.active
    data = []
    for row in worksheet.iter_rows(values_only=True):
        data.append(row)
    return render(request, 'MetadataDisplay.html', {'data': data})


def data_input(request):
    if request.method == 'POST':
        form = DataInputForm(request.POST, request.FILES)

        if form.is_valid():
            form.save_to_db()  # Save data to database.
            patient_id = form.cleaned_data["patient_id"]
            return render(request, 'DataInputForm_Success.html', {'form': form, 'patient_id': patient_id})
    else:
        form = DataInputForm()
        
    return render(request, 'DataInputForm.html', {'form': form})
