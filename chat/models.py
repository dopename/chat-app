from django.db import models
from django.contrib.auth.models import User
import datetime

class ChatUser(models.Model):
	chat_name = models.CharField(max_length=64)
	user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True, related_name='chat_user')
	logged_in = models.BooleanField(default=False)

class Room(models.Model):
	room_name = models.CharField(max_length=64)

class RoomSubscription(models.Model):
	chat_user = models.ForeignKey(ChatUser, on_delete=models.CASCADE)
	room = models.ForeignKey(Room, on_delete=models.CASCADE)

class ChatMessage(models.Model):
	user = models.ForeignKey(ChatUser, on_delete=models.CASCADE)
	message = models.TextField()
	room = models.ForeignKey(Room, on_delete=models.CASCADE)
	timestamp = models.DateTimeField(default=datetime.datetime.now)