from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect
from .models import * 
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .definitions import *
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

channel_layer = get_channel_layer()

def home_page(request):
	available_rooms = Room.objects.all()
	return render(request, self.template_name, {'rooms':available_rooms})


class Base(View):
	template_name = 'chat/base.html'

	def get(self, request, *args, **kwargs):
		return render(request, self.template_name)


class Chatroom(View, LoginRequiredMixin):
	template_name = 'chat/chat.html'
	login_url = '/login/'

	def get(self, request, room, *args, **kwargs):
		chat_room = None
		messages = None

		try:
			chat_room = Room.objects.get(room_name=room)
			messages = ChatMessage.objects.filter(room=chat_room)
		except:
			print('sucks')

		room_users = len(RoomSubscription.objects.filter(room__room_name=room, active=True))

		async_to_sync(channel_layer.group_send)(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_JOINED_ROOM,
				'text':{'chatroom_user_count_update':{'room':room, 'user':request.user.chat_user.chat_name, 'user_count':room_users}}
			}
		)

		return render(request, self.template_name, {'room':room, 'messages':messages, 'active_session':self.check_session_id_active(request.session.session_key)})


def user_login(request):
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')

		user = authenticate(request=request, username=username, password=password)
		if user:
			if user.is_active:
				login(request, user)

				chat_user = ChatUser.objects.get(user=user.id)
				chat_user.logged_in = True
				chat_user.save(update_fields=['logged_in'])

				async_to_sync(channel_layer.group_send)(
					GLOBAL_ROOM_NAME,
					{
						'type':GLOBAL_USER_LOGGED_IN,
						'text':{'user_logged_in':chat_user.chat_name}
					}
				)
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