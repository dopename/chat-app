from django.urls import path
import chat.views as views

app_name = 'chat'

urlpatterns = [
	path('', views.Base.as_view()),
	path('chat/<str:room>/', views.Chatroom.as_view(), name='chat'),
	path('home/', views.home),
	path('login/', views.user_login, name='login'),
	path('register/', views.register),
]