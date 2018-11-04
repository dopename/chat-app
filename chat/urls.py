from django.urls import path
import chat.views as views

app_name = 'chat'

urlpatterns = [
	path('', views.home),
	path('chat/<str:room>/', views.chat, name='chat'),
]