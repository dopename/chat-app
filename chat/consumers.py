import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.core import serializers

from .models import *
#MEssage, Thread

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
				'username': username
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