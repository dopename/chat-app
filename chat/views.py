from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect
from .models import * 
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from asgiref.sync import AsyncToSync
from channels.layers import get_channel_layer
from .definitions import *

def home(request):
	template_name = 'chat/index.html'
	if request.method == 'GET':
		available_rooms = Room.objects.all()
		return render(request, template_name, {'rooms':available_rooms})

@login_required
def chat(request, room):
	template_name = 'chat/chat.html'
	chat_room = None
	messages = None
	channel_layer = get_channel_layer()

	try:
		chat_room = Room.objects.get(room_name=room)
		messages = ChatMessage.objects.filter(room=chat_room)
	except:
		print('sucks')

	# AsyncToSync(channel_layer.send)(
	# 	GLOBAL_ROOM_NAME,
	# 	{
	# 		'type':GLOBAL_USER_UPDATE,
	# 		'text':request.user.username + '!!!!'
	# 	}
	# )

	return render(request, template_name, {'room':room, 'messages':messages})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request=request, username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/')
            else:
                return HttpResponse("Your account is disabled.")
        else:
            print("Invalid login details: {0}, {1}".format(username, password))
            return HttpResponse("Invalid login details supplied.")
    else:
        return render(request, 'chat/login.html', {})
		
def user_logout(request):
	logout(request)
	return redirect('/') 

def register(request):
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')

		if len(User.objects.filter(username=username)) < 1:
			user = User.objects.create_user(username=username, password=password)
			ChatUser.objects.create(chat_name=username, user=user)

			return HttpResponseRedirect('/')
		else:
			return HttpResponse('That username is already taken')
	else:
		return render(request, 'chat/register.html')