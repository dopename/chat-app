from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect
from .models import * 

def home(request):
	if request.method == 'GET':
		template_name = 'chat/index.html'
		return render(request, template_name)

def chat(request, room):
	template_name = 'chat/chat.html'
	chat_room = None
	messages = None

	try:
		chat_room = Room.objects.get(room_name=room)
		messages = ChatMessage.objects.filter(room=chat_room)
	except:
		print('sucks')

	return render(request, template_name, {'room':room, 'messages':messages})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request=request, username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
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