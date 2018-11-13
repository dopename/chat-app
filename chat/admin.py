from django.contrib import admin
from .models import *

admin.site.register(Room)
admin.site.register(ChatUser)
admin.site.register(RoomSubscription)
admin.site.register(ChatMessage)
admin.site.register(WebsocketClient)

# Register your models here.
