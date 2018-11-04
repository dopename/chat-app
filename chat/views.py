from django.shortcuts import render
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