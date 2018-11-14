function scrollWindow(div) {
	var windowHeightPx = (window.screen.height * 0.50).toString() + "px";
	var chatBox = document.getElementById(div)
	chatBox.style.height = windowHeightPx;
	chatBox.scrollTop = chatBox.scrollHeight;
}

function grabChatroom(select, display) {
	//console.log(select, display)
	var url = '/chat/'
	var selectBox = document.getElementById(select)
	var selectedOption = selectBox.options[selectBox.selectedIndex].value

	fetch(url + selectedOption)
	.then(response => response.text())
	.then(html => {
		document.getElementById(display).innerHTML = html
	})
}

var openWebsocketConnection = (url_suffix) => {
	var loc = window.location

	var wsStart = "ws://"
	if (loc.protocol == 'https:') {
		wsStart = 'wss://'
	}

	var endpoint = wsStart + window.location.host + url_suffix;
					
	var socket = new WebSocket(endpoint)

	return socket
}

var websocketManagment = (url_suffix, type) => {
	var socket = openWebsocketConnection()

	socket.onmessage = (e) => {
		console.log("message", e);

		var onlineUsers = document.getElementById('online-users');

		var parsedData = JSON.parse(e.data);
		var responseKeys = Object.keys(parsedData);
		console.log(responseKeys)

		if (responseKeys.indexOf('global_user_count_update') > -1) {
			onlineUsers.innerHTML = parsedData.global_user_count_update.total_users;
		}
		if (responseKeys.indexOf('chatroom_user_count_update') > -1) {
			var updateKey = parsedData.chatroom_user_count_update.room
			var roomOnlineUsers = document.getElementById('badge_' + updateKey);
			console.log(updateKey, parsedData.chatroom_user_count_update.user_count)
						
			roomOnlineUsers.innerHTML = parsedData.chatroom_user_count_update.user_count;
		}
		if (responseKeys.indexOf('user_logged_in') > -1) {
			return null
		}
	}

	socket.onopen = (e) => {
		console.log("open", e)
	}

	socket.onerror = (e) => {
		console.log("error", e)
	}

	socket.onclose = (e) => {
		console.log("close", e)
	}

}