import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import AsyncToSync
from django.core import serializers
from channels.layers import get_channel_layer
import datetime
import time

from .models import *
from .definitions import *

USER_MAPPINGS = {}



class GlobalWebsocket(AsyncConsumer):
	async def websocket_connect(self, event):

		active_channels = await self.check_if_active()
		if len(active_channels) > 0:
			if len(active_channels) > 1:
				await self.close_old_channels(active_channels)

				await self.create_channel_record()
			else:
				await self.update_channel_record(active_channels[0])
		else:
			await self.create_channel_record()


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
				'text':{'global_user_count_update':{'total_users':await self.count_active_users()}}
			}
		)

	async def websocket_disconnect(self, event):
		await self.channel_layer.group_send(
			GLOBAL_ROOM_NAME,
			{
				'type':GLOBAL_USER_LOGGED_IN,
				'text':{'global_user_count_update':{'total_users':await self.count_active_users()}}
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
		# if 'room' in event.keys():
		# 	USER_MAPPINGS[event['text']['room']] = event['text']['user']
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':json.dumps(event['text'])
			})

	async def global_user_left_room(self, event):
		# if 'room' in event.keys():
		# 	USER_MAPPINGS[event['text']['room']] = event['text']['user']
		await self.send({
				'type':WEBSOCKET_SEND,
				'text':json.dumps(event['text'])
			})

	async def disconnect_global_channel(self, channel_name):
		self.channel_layer.group_discard(
			GLOBAL_ROOM_NAME,
			channel_name
		)

	@database_sync_to_async
	def close_old_channel(self, sessions):
		for session in sessions:
			self.disconnect_global_channel(session.channel_name)

			session.delete()

	@database_sync_to_async
	def update_channel_record(self, channel):
		self.disconnect_global_channel(channel.channel_name)
		channel.channel_name = self.channel_name
		channel.save(update_fields=['channel_name'])

	@database_sync_to_async
	def count_active_users(self):
		return len(ChatUser.objects.filter(logged_in=True))

	@database_sync_to_async
	def check_if_active(self):
		ws_clients = WebsocketClient.objects.filter(session_id=self.scope['session'].session_key, group_name=GLOBAL_ROOM_NAME)
		return ws_clients

	@database_sync_to_async
	def create_channel_record(self):
		ws_client = WebsocketClient.objects.create(session_id=self.scope['session'].session_key, group_name=GLOBAL_ROOM_NAME, channel_name=self.channel_name)
		print("Created new record {}".format(ws_client.session_id))




class ChatRoomConsumer(AsyncConsumer):
	async def websocket_connect(self, event):

		room_url = self.scope['url_route']['kwargs']['room_name']
		connecting_user = self.scope['user']

		self.me = connecting_user

		chat_room = 'chatroom_{}'.format(room_url)

		self.chat_room = chat_room

		await self.channel_layer.group_add(
			self.chat_room, 
			self.channel_name
		)

		await self.send({
			'type':WEBSOCKET_ACCEPT
		})

		await self.join_chatroom(chat_user=connecting_user.chat_user, room=room_url)

	async def websocket_receive(self, event):

		front_text = event.get('text', None)

		if front_text is not None:
			dict_data = json.loads(front_text)
			msg = dict_data.get('message')

			user = self.scope['user']
			username = 'default'

			chat_user = user.chat_user

			response = {
				'message':msg,
				'username':chat_user.chat_name,
				'timestamp':str(datetime.datetime.time(datetime.datetime.now()))[:8]
			}

			await self.create_chat_message(user=chat_user, message=msg, chat_room=self.chat_room)

			await self.channel_layer.group_send(
				self.chat_room,
				{
					'type':ROOM_CHAT_MESSAGE,
					'text':json.dumps(response)
				}
			)


	async def websocket_disconnect(self, event):
		print("disconnected", event)

		await self.channel_layer.group_send(
			GLOBAL_ROOM_NAME,
			{
				'type':'global_user_left_room',
				'text':await self.get_current_user_count()
			}
		)

		await self.leave_chatroom(chat_user=self.scope['user'].chat_user, room=self.chat_room)

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
	def join_chatroom(self, chat_user, room):
		print(f"Connecting {chat_user.chat_name} to {room}")
		chat_room = None
		try:
			chat_room = Room.objects.get(room_name=room)
		except:
			chat_room = Room.objects.create(room_name=room)

		room_subscription = RoomSubscription.objects.filter(chat_user__id=chat_user.id, room=chat_room.id)
		if len(room_subscription) > 0:
			rs = room_subscription[0]
			print(rs)
			if rs.active == False:
				rs.active == True
				rs.save(update_fields=['active'])
				print(rs.active)
		else:
			RoomSubscription.objects.create(chat_user=chat_user, room=chat_room, active=True)

		return None

	@database_sync_to_async
	def leave_chatroom(self, chat_user, room):
		print(f"Disconnecting {chat_user.chat_name} from {room}")
		chat_room = [r for r in Room.objects.all() if r.chat_room == room]
		chat_room = chat_room[0]
		room_subscription = RoomSubscription.objects.filter(chat_user=chat_user, room=chat_room)
		if room_subscription.exists():
			rs = room_subscription[0]
			print(rs)
			if rs.active == True:
				rs.active == False
				rs.save(update_fields=['active'])
				print(rs.active)
		return None

	@database_sync_to_async
	def create_chat_message(self, message, chat_room, user):
		print("creating chat messsage")
		room = Room.objects.get(room_name=chat_room.split('_')[-1])
		print(room)
		newmsg = ChatMessage.objects.create(user=user, message=message, room=room)
		print(newmsg)
		return True

	@database_sync_to_async
	def get_current_user_count(self):
		chat_room = [r for r in Room.objects.all() if r.chat_room == self.chat_room]
		chat_room = chat_room[0]

		return len(RoomSubscription.objects.filter(room=chat_room, active=True))
