from django.shortcuts import render
from django.contrib.auth import authenticate
from .models import * 

def home(request):
	if request.method == 'GET':
		template_name = 'chat/index.html'
		return render(request, template_name)

def chat(request, room):
	template_name = 'chat/chat.html'
	chat_room = None
	messages = None

	try:
		chat_room = Room.objects.get(room_name=room)
		messages = ChatMessage.objects.filter(room=chat_room)
	except:
		print('sucks')

	return render(request, template_name, {'room':room, 'messages':messages})

def user_login(request):
	template_name = 'chat/login.html'

	username = request.POST.get('username')
	password = request.POST.get('password')

	user = authenticate(username=username, password=password)

	return render(request, 'chat/index.html')