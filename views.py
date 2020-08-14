# -*- coding: utf-8 -*-
################################################################################

from django.contrib.auth.models import User
from django.contrib import auth
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect


################################################################################

def main(request):
    if request.user.is_authenticated():
        if request.user.username == 'cnb':
            return HttpResponseRedirect('/tp')
        elif request.user.username == 'manager':
            return HttpResponseRedirect('/content')

    return render(request, 'login.html', {})

################################################################################

@csrf_exempt
def login(request):
    username = request.POST['username']
    password = request.POST['password']
    user = auth.authenticate(username=username, password=password)
    if user is not None and user.is_active:
        auth.login(request, user)
        if user.username == 'cnb':
            return HttpResponseRedirect("/tp")
        if user.username == 'manager':
            return HttpResponseRedirect("/content")
    request.session['ERROR_LOGIN'] = u'Неверные логин или пароль'
    return HttpResponseRedirect("/")

################################################################################

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect("/")

################################################################################

