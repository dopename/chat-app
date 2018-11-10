import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.core import serializers
import datetime

from .models import *
#MEssage, Thread

import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.core import serializers
import datetime

from .models import *
from .definitions import *
#MEssage, Thread

# GLOBAL_ROOM_NAME = 'global'
# GLOBAL_USER_UPDATE = 'global_user_update'
# ROOM_USER_UPDATE = 'room_user_update'
# ROOM_CHAT_MESSAGE = 'room_chat_message'
# WEBSOCKET_ACCEPT = 'websocket.accept'
# WEBSOCKET_DISCONNECT = 'websocket.disconnect'
# WEBSOCKET_SEND = 'websocket.send'

class GlobalConsumer(AsyncConsumer):

	async def websocket_connect(self, event):

		user = self.scope['user'] #grab the user from the scope

		if user.is_authenticated: #update the user's logged in attribute if they are logged in
			self.user = self.scope['user']

			await self.login_user(user)

		await self.channel_layer.group_add(
			GLOBAL_ROOM_NAME, 
			self.channel_name
		)

		await self.send({
			"type":WEBSOCKET_ACCEPT,
		})

		await self.channel_layer.group_send(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_UPDATE,
				'text':json.dumps({'users':await self.count_current_users()})
			}
		)

	# async def room_update(self, event):
	# 	await self.send({
	# 			'type':WEBSOCKET_SEND,
	# 			'text':event['text']
	# 		})

	async def websocket_receive(self, event):
		print("receive", event)

	async def websocket_disconnect(self, event):
		await self.logout_user(self.user)

		await self.channel_layer.group_send(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_UPDATE,
				'text':json.dumps({'users':await self.count_current_users()})
			}
		)

		await self.channel_layer.group_discard(
			GLOBAL_ROOM_NAME,
			self.channel_name
		)

	async def global_user_update(self, event):
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':event['text']
			})

	@database_sync_to_async
	def login_user(self, user):
		chat_user = ChatUser.objects.get(user=user.id)
		chat_user.logged_in = True
		chat_user.save(update_fields=['logged_in'])

	@database_sync_to_async
	def logout_user(self, user):
		chat_user = ChatUser.objects.get(user=user.id)
		chat_user.logged_in = False
		chat_user.save(update_fields=['logged_in'])

	@database_sync_to_async
	def count_current_users(self):
		return len(ChatUser.objects.filter(logged_in=True))


class ChatConsumer(AsyncConsumer):
	async def websocket_connect(self, event):
		print("connected", event)

		room_url = self.scope['url_route']['kwargs']['room_name']

		me = self.scope['user']

		connected_room = await self.get_room(room_url, me)

		connected_room_name = connected_room.room.room_name

		chat_room = 'chatroom_{}'.format(connected_room_name)
		self.chat_room = chat_room

		await self.channel_layer.group_add(
				chat_room, 
				self.channel_name
			)

		await self.send({
			"type":WEBSOCKET_ACCEPT
		})

		await self.channel_layer.group_send(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_UPDATE,
				'text':json.dumps({'channel':{self.chat_room.split('_')[-1]: await self.users_per_room(connected_room_name)}})
			}
		)

	async def websocket_receive(self, event):
		print("receive", event)

		front_text = event.get('text', None)

		if front_text is not None:
			dict_data = json.loads(front_text)
			msg = dict_data.get('message')
			print(msg)
			user = self.scope['user']
			username = 'default'
			if user.is_authenticated:
				chat_user = user.chat_user
				username = user.chat_user.chat_name

			myResponse = {
				'message':msg,
				'username': username,
				'timestamp':str(datetime.datetime.time(datetime.datetime.now()))[:8]
			}

			success = await self.create_chat_message(user=chat_user, message=msg, room=Room.objects.get(room_name=self.chat_room.split('_')[-1]))

			await self.channel_layer.group_send(
				self.chat_room,
				{
					'type':ROOM_CHAT_MESSAGE,
					'text':json.dumps(myResponse)
				}
			)
		else: 
			print("lol")


	async def room_user_update(self, event):
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':event['text']
			})

	async def room_chat_message(self, event):
		print('message', event)
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':event['text']
			})

	async def websocket_disconnect(self, event):
		print("disconnected", event)

		await self.send({
				'type':WEBSOCKET_DISCONNECT,
			})

		await self.channel_layer.group_send(
			GLOBAL_USER_UPDATE,
			{
				'type':ROOM_USER_UPDATE,
				'text':json.dumps({'channel':{self.chat_room.split('_')[-1]: await self.users_per_room(connected_room_name)}})
			}
		)

		await self.channel_layer.group_discard(
			self.chat_room,
			self.channel_name
		)

	@database_sync_to_async
	def users_per_room(self, roomname):
		return len(RoomSubscription.objects.filter(active=True, room__room_name=roomname))

	@database_sync_to_async
	def get_room(self, roomname, user):
		return_room = None
		room = None
		try:
			room = Room.objects.get(room_name=roomname)
		except:
			room = Room.objects.create(room_name=roomname)

		if len(RoomSubscription.objects.filter(chat_user=user.chat_user.id, room=int(room.id))) < 1:
			return_room = RoomSubscription.objects.create(chat_user=user.chat_user, room=room, active=True)
		else:
			return_room = RoomSubscription.objects.filter(chat_user=user.chat_user.id, room=int(room.id))[0]
			return_room.active = True
			return_room.save(update_fields=['active'])

		return return_room

	@database_sync_to_async
	def create_chat_message(self, message, room, user):
		print("creating chat messsage")
		try:
			ChatMessage.objects.create(user=user, message=message, room=room)
			return True
		except:
			return False
