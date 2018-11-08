from django.urls import path
from chat import views

app_name = 'chat'

urlpatterns = [
	path('', views.home),
	path('chat/<str:room>/', views.chat, name='chat'),
	path('login/', views.user_login),
]