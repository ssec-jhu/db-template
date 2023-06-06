from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import FileUploadForm

from django.shortcuts import render
from openpyxl import load_workbook

def home(request):
    context = {'name': 'World'}
    render(request, 'Home.html', context)
    return upload_file(request)
    #return render(request, 'Home.html', context)
    #return HttpResponse("Hello, world. You're at BioSpectral Repository website!!!")

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
