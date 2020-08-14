# -*- coding: utf-8 -*-
################################################################################

from django.contrib.auth.models import User
from django.contrib import auth


from django.http import HttpResponseRedirect
from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse_lazy

from django.conf import settings

################################################################################

def resolve_view_name(view):
    return reverse_lazy( '.'.join([view.__module__, view.__name__]) )

################################################################################
   
def only_cnb(view):
    def is_cnb(request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.username == 'cnb':
            return view(request, *args, **kwargs)
        else:
            return HttpResponseRedirect('/')            
    return is_cnb        
    
################################################################################
   
def only_manager(view):
    def is_manager(request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.username == 'manager':
            return view(request, *args, **kwargs)
        else:
            return HttpResponseRedirect('/')            
    return is_manager    
    
    
    
    
