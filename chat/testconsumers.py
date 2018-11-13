import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core import serializers
import datetime

from .models import *
from .definitions import *

USER_MAPPINGS = {}

class GlobalWebsocket(AsyncConsumer):
	async def websocket_connect(self, event):

		await self.close_old_channel()

		print(self.scope['session'].session_key)

		await self.channel_layer.group_add( #add global room name to channel layer
			GLOBAL_ROOM_NAME, 
			self.channel_name
		)

		await self.send({
			'type':WEBSOCKET_ACCEPT
		})

		await self.channel_layer.group_send(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_LOGGED_IN,
				'text':{'user_count': await self.count_active_users()}
			}
		)

	async def websocket_disconnect(self, event):
		await self.channel_layer.group_send(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_LOGGED_IN,
				'text':{'user_count': await self.count_active_users()}
			}
		)

		await self.send({
				'type':WEBSOCKET_DISCONNECT,
			})

	async def global_user_logged_in(self, event):
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':json.dumps(event['text'])
			})		

	async def global_user_joined_room(self, event):
		if 'room' in event.keys():
			USER_MAPPINGS[event['text']['room']] = event['text']['user']
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':json.dumps(event['text'])
			})

	async def disconnect_global_channel(self, channel_name):
		self.channel_layer.group_discard(
			GLOBAL_ROOM_NAME,
			channel_name
		)

		self.create_channel_record()

	@database_sync_to_async
	def close_old_channel(self):
		sessions = WebsocketClient.objects.filter(session_id=self.scope['session'].session_key, group_name=GLOBAL_ROOM_NAME)

		if len(sessions) > 1:
			for session in sessions:

				self.disconnect_global_channel(session.channel_name)

				session.delete()
			self.create_channel_record()
		elif len(sessions) > 0:
			session = sessions[0]
			self.disconnect_global_channel(session.channel_name)
			session.channel_name = self.channel_name
			session.save(update_fields=['channel_name'])
		else:
			self.create_channel_record


	@database_sync_to_async
	def count_active_users(self):
		return len(ChatUser.objects.filter(logged_in=True))

	# @database_sync_to_async
	# def check_if_active(self):
	# 	ws_clients = WebsocketClient.objects.filter(session_id=self.scope['session'].session_key, group_name=GLOBAL_ROOM_NAME)
	# 	if GLOBAL_ROOM_NAME in [ws.group_name for ws in ws_clients]:
	# 		return True
	# 	return False

	@database_sync_to_async
	def create_channel_record(self):
		ws_client = WebsocketClient.objects.create(session_id=self.scope['session'].session_key, group_name=GLOBAL_ROOM_NAME, channel_name=self.channel_name)




class ChatRoomConsumer(AsyncConsumer):
	async def websocket_connect(self, event):

		room_url = self.scope['url_route']['kwargs']['room_name']
		connecting_user = self.scope['user']

		chat_room = 'chatroom_{}'.format(room_url)

		self.chat_room = chat_room

		await self.channel_layer.group_add(
			self.chat_room, 
			self.channel_name
		)

		await self.send({
			'type':WEBSOCKET_ACCEPT
		})

	async def websocket_receive(self, event):

		front_text = event.get('text', None)

		if front_text is not None:
			dict_data = json.loads(front_text)
			msg = dict_data.get('message')

			user = self.scope['user']
			username = 'default'

			if user.is_authenticated:
				chat_user = user.chat_user

			response = {
				'message':msg,
				'username':chat_user.chat_name,
				'timestamp':str(datetime.datetime.time(datetime.datetime.now()))[:8]
			}

			await self.create_chat_message(user=chat_user, message=msg, chat_room=self.chat_room)

			await self.channel_later.group_send(
				self.chat_room,
				{
					'type':ROOM_CHAT_MESSAGE,
					'text':json.dumps(response)
				}
			)


	async def websocket_disconnect(self, event):
		print("disconnected", event)

		await self.send({
				'type':WEBSOCKET_DISCONNECT,
			})

	async def room_chat_message(self, event):
		print('message', event)
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':event['text']
			})

	@database_sync_to_async
	def create_chat_message(self, message, chat_room, user):
		print("creating chat messsage")
		try:
			room = Room.objects.get(chat_room=chat_room)
			ChatMessage.objects.create(user=user, message=message, room=room)
			return True
		except:
			return False