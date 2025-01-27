from django.shortcuts import render

################################################
#   Pagina de bienvenida
################################################
def inicio(request):
    template = 'dashboard/index.html' 
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR Generador
################################################
def qrgen(request):
    template = 'dashboard/qrgenerator.html' 
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR Escaner
################################################
def qrscan(request):
    template = 'dashboard/qrscan.html' 
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR create event
################################################
def create(request):
    template = 'dashboard/create.html' 
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR assign assign
################################################
def assign(request):
    template = 'dashboard/assign.html' 
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR basic
################################################
def basic(request):
    template = 'dashboard/basic.html'    
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR tables
################################################
def tables(request):
    template = 'dashboard/tables.html' 
    context = {}
    return render(request, template, context)