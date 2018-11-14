function scrollWindow(div) {
	var windowHeightPx = (window.screen.height * 0.50).toString() + "px";
	var chatBox = document.getElementById(div)
	chatBox.style.height = windowHeightPx;
	chatBox.scrollTop = chatBox.scrollHeight;
}

function grabChatroom(select, display) {
	console.log(select, display)
	var url = '/chat/'
	var selectBox = document.getElementById(select)
	var selectedOption = selectBox.options[selectBox.selectedIndex].value

	fetch(url + selectedOption)
	.then(response => response.text())
	.then(html => {
		document.getElementById(display).innerHTML = html
	})
}