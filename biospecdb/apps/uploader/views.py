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
            form.save()  # Save data to database.
            patient_id = form.cleaned_data["patient_id"]
            return render(request, 'DataInputForm_Success.html', {'form': form, 'patient_id': patient_id})
    else:
        form = DataInputForm()
        
    return render(request, 'DataInputForm.html', {'form': form})
