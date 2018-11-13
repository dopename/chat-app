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

class WebsocketChecker:

	def __init__(self):
		self.session_id = None

	def set_session_id(self, session_id):
		self.session_id = session_id

	def check_session_id_active(self):
		ws_clients = WebsocketClient.objects.filter(session_id=self.session_id)

		if len(ws_clients) < 1:
			return []
		return [ws for ws in ws_clients]

	def add_global_channel(self, session):
		if self.session_id is None:
			self.session_id = session._session_key

		current_channels = self.check_session_id_active()
		flag = False

		if flag:
			WebsocketClient.create(group_name=GLOBAL_ROOM_NAME, session_id=self.session_id)	


class Home(View, WebsocketChecker):
	template_name = 'chat/index.html'

	def get(self, request, *args, **kwargs):
		available_rooms = Room.objects.all()
		return render(request, self.template_name, {'rooms':available_rooms})


class Chatroom(View, WebsocketChecker):
	template_name = 'chat/chat.html'

	def get(self, request, room, *args, **kwargs):
		chat_room = None
		messages = None

		try:
			print("****************\n\n" + request.session + "\n\n*******************\n\n")
		except:
			pass

		try:
			chat_room = Room.objects.get(room_name=room)
			messages = ChatMessage.objects.filter(room=chat_room)
		except:
			print('sucks')

		async_to_sync(channel_layer.group_send)(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_JOINED_ROOM,
				'text':{'room':room, 'user':request.user.chat_user.chat_name}
			}
		)

		return render(request, self.template_name, {'room':room, 'messages':messages})


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
						'text':{'user':chat_user.chat_name}
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