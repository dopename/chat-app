from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from django.conf.urls import url
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator
from channels.sessions import SessionMiddlewareStack


from chat.consumers import ChatConsumer, GlobalConsumer
from chat.testconsumers import GlobalWebsocket, ChatRoomConsumer

old_application = ProtocolTypeRouter({
	'websocket': AllowedHostsOriginValidator(
		AuthMiddlewareStack(
			URLRouter(
				[
					url(r"^chat/(?P<room_name>[\w.@+-]+)/$", ChatConsumer),
					url(r"^logged_in/$", GlobalConsumer),
				]
			)

		)
	),
	# "channel":ChannelNameRouter({
	# 		"global":GlobalWorker
	# }),
})

application = ProtocolTypeRouter({
	'websocket': AllowedHostsOriginValidator(
		AuthMiddlewareStack(
			SessionMiddlewareStack(
				URLRouter(
					[
						url(r"^chat/(?P<room_name>[\w.@+-]+)/$", ChatRoomConsumer),
						url(r"^logged_in/$", GlobalWebsocket),
					]
				)

			)
		)
	),
	# "channel":ChannelNameRouter({
	# 		"global":GlobalWorker
	# }),
})