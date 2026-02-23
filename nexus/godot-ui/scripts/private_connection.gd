## PrivateConnection - Simple WebSocket client for 1:1 wrapper rooms.
## Much lighter than NexusConnection - just sends/receives JSON.
class_name PrivateConnection
extends Node

signal connected()
signal disconnected()
signal chat_received(sender: String, content: String)
signal emote_received(sender: String, content: String)
signal status_received(status: String)
signal system_received(content: String)
signal history_received(messages: Array)

@export var server_url: String = "ws://localhost:8770"
@export var entity_name: String = "Entity"

var _socket: WebSocketPeer = WebSocketPeer.new()
var _connected: bool = false
var _wants_connection: bool = false
var _reconnect_timer: float = 0.0
var _reconnect_delay: float = 3.0


func _ready() -> void:
	set_process(false)


func connect_to_room() -> void:
	_wants_connection = true
	var err = _socket.connect_to_url(server_url)
	if err != OK:
		push_error("PrivateConnection: connect failed: %s" % err)
		return
	set_process(true)


func disconnect_from_room() -> void:
	_wants_connection = false
	if _connected:
		_socket.close()
	set_process(false)


func is_room_connected() -> bool:
	return _connected


func send_chat(text: String) -> void:
	_send({"type": "chat", "content": text})


func send_command(command: String, extra: Dictionary = {}) -> void:
	var data = {"type": "command", "command": command}
	data.merge(extra)
	_send(data)


func _send(data: Dictionary) -> void:
	if _connected:
		var json_str = JSON.stringify(data)
		_socket.send_text(json_str)


func _process(delta: float) -> void:
	_socket.poll()
	var state = _socket.get_ready_state()
	
	match state:
		WebSocketPeer.STATE_OPEN:
			if not _connected:
				_connected = true
				_reconnect_timer = 0.0
				connected.emit()
			
			while _socket.get_available_packet_count() > 0:
				var raw = _socket.get_packet().get_string_from_utf8()
				var parsed = JSON.parse_string(raw)
				if parsed is Dictionary:
					_handle_message(parsed)
		
		WebSocketPeer.STATE_CLOSING:
			pass
		
		WebSocketPeer.STATE_CLOSED:
			if _connected:
				_connected = false
				disconnected.emit()
			
			if _wants_connection:
				_reconnect_timer += delta
				if _reconnect_timer >= _reconnect_delay:
					_reconnect_timer = 0.0
					_socket = WebSocketPeer.new()
					_socket.connect_to_url(server_url)


func _handle_message(data: Dictionary) -> void:
	var msg_type = data.get("type", "")
	
	match msg_type:
		"chat":
			chat_received.emit(
				data.get("sender", entity_name),
				data.get("content", "")
			)
		"emote":
			emote_received.emit(
				data.get("sender", entity_name),
				data.get("content", "")
			)
		"status":
			status_received.emit(data.get("status", ""))
		"system":
			system_received.emit(data.get("content", ""))
		"history":
			var msgs = data.get("messages", [])
			if msgs is Array:
				history_received.emit(msgs)
		"pong":
			pass  # keepalive response
