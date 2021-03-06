import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.core import serializers
import datetime

from .models import *
from .definitions import *

USER_MAPPINGS = {}

class GlobalConsumer(AsyncConsumer):
	async def websocket_connect(self, event):

		user = self.scope['user'] #grab the user from the scope

		if user.is_authenticated: #update the user's logged in attribute if they are logged in
			self.user = self.scope['user']

		await self.channel_layer.group_add( #add global room name to channel layer
			GLOBAL_ROOM_NAME, 
			self.channel_name
		)

		await self.send({ #accept the connection
			"type":WEBSOCKET_ACCEPT,
		})

		await self.channel_layer.group_send( #send the updated user count to global group
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_UPDATE,
				'text':json.dumps({'users':await self.count_current_users()})
			}
		)

	async def websocket_receive(self, event):
		print("receive", event)

	async def websocket_disconnect(self, event):

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
		try:
			USER_MAPPINGS[event['room']] = event['user']
		except:
			pass
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':event['text']
			})


	async def global_user_logged_in(self, event):
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':json.dumps(event['text'])
			})		

	async def global_user_joined_room(self, event):
		try:
			USER_MAPPINGS[event['room']] = event['user']
		except:
			pass
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':event['text']
			})

	@database_sync_to_async
	def count_current_users(self):
		return len(ChatUser.objects.filter(logged_in=True))


class ChatConsumer(AsyncConsumer):
	async def websocket_connect(self, event):
		print("connected", event)

		room_url = self.scope['url_route']['kwargs']['room_name']

		me = self.scope['user']
		self.me = me

		connected_room = await self.join_room(room_url, me)

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
	def join_room(self, roomname, user):
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
	def leave_room(self, roomname, user):
		value = None
		try:
			room_subscription = RoomSubscription.objects.get(room__room_name=roomname, chat_user=user.chat_user, active=True)
			room_subscription.active = False
			room_subscription.save(update_fields=['active'])
			value = room_subscription
		except:
			pass


	@database_sync_to_async
	def create_chat_message(self, message, room, user):
		print("creating chat messsage")
		try:
			ChatMessage.objects.create(user=user, message=message, room=room)
			return True
		except:
			return False
