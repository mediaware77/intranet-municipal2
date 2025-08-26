from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # URLs de navegação padrão
    path('', views.dashboard, name='dashboard'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),
    
    # URLs de reconhecimento facial
    path('facial/cadastro/', views.cadastrar_face, name='cadastrar_face'),
    path('facial/login/', views.login_facial, name='login_facial'),
    path('facial/login-page/', views.facial_login_page, name='facial_login_page'),
    path('facial/historico/', views.historico_facial, name='historico_facial'),
    path('facial/remover/', views.remover_facial, name='remover_facial'),
    path('facial/admin-historico/', views.admin_historico_facial, name='admin_historico_facial'),
    
    # URLs de gerenciamento de foto facial
    path('facial/atualizar-foto/', views.atualizar_foto_facial, name='atualizar_foto_facial'),
    path('facial/remover-foto/', views.remover_foto_facial, name='remover_foto_facial'),
]