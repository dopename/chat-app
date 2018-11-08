import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.core import serializers
import datetime

from .models import *
#MEssage, Thread

class GlobalConsumer(AsyncConsumer):

	async def websocket_connect(self, event):
		
		room_name = 'online'
		self.room_name = room_name

		user = self.scope['user']

		if user.is_authenticated:
			# self.user = self.scope['user']

			await self.login_user(user)

			await self.channel_layer.group_add(
				room_name, 
				self.channel_name
			)

			await self.send({
				"type":"websocket.accept",
				"text":"Total logged in: {}".format(await self.count_current_users())
			})

	async def websocket_receive(self, event):
		print("receive", event)

	async def websocket_disconnect(self, event):
		await self.logout_user(self.user)

		await self.channel_layer.group_discard(
			self.room_name,
			self.channel_name
		)

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

		chat_room = 'chatroom_{}'.format(connected_room.room_name)
		self.chat_room = chat_room

		await self.channel_layer.group_add(
				chat_room, 
				self.channel_name
			)

		await self.send({
			"type":"websocket.accept"
		})

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
					'type':'chat_message',
					'text':json.dumps(myResponse)
				}
			)
		else: 
			print("lol")

	async def chat_message(self, event):
		print('message', event)
		await self.send({
				'type':'websocket.send',
				'text':event['text']
			})

	async def websocket_disconnect(self, event):
		print("disconnected", event)

		await self.channel_layer.group_discard(
			self.chat_room,
			self.channel_name
		)


	@database_sync_to_async
	def get_room(self, roomname, user):
		print('Hit this funciton')
		return_room = None
		room = None
		try:
			room = Room.objects.get(room_name=roomname)
		except:
			room = Room.objects.create(room_name=roomname)

		if len(RoomSubscription.objects.filter(chat_user=user.chat_user.id, room=int(room.id))) < 1:
			RoomSubscription.objects.create(chat_user=user.chat_user, room=room)
		else:
			return_room = RoomSubscription.objects.filter(chat_user=user.chat_user.id, room=int(room.id))[0]

		return room

	@database_sync_to_async
	def create_chat_message(self, message, room, user):
		print("creating chat messsage")
		try:
			ChatMessage.objects.create(user=user, message=message, room=room)
			return True
		except:
			return False