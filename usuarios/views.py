from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.views import LoginView
from .forms import PerfilUsuarioForm, AlterarSenhaForm


class CustomLoginView(LoginView):
    template_name = 'usuarios/login.html'
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    context = {
        'usuario': request.user,
    }
    return render(request, 'usuarios/dashboard.html', context)


@login_required
def perfil(request):
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('perfil')
    else:
        form = PerfilUsuarioForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'usuarios/perfil.html', context)


@login_required
def alterar_senha(request):
    if request.method == 'POST':
        form = AlterarSenhaForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('dashboard')
    else:
        form = AlterarSenhaForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'usuarios/alterar_senha.html', context)