## NexusConnection - WebSocket client for the Nexus multi-entity server.
## Handles connect, send, receive, event parsing, and auto-reconnect.
class_name NexusConnection
extends Node

signal connected()
signal disconnected()
signal message_received(data: Dictionary)
signal participant_update(data: Dictionary)
signal status_update(data: Dictionary)
signal history_received(messages: Array)
signal error_received(message: String)
signal auto_event_received(msg_type: String, entity: String, data: Dictionary)
signal canvas_updated(entity: String, base64_png: String, dimensions: Array, iteration: int)
signal canvas_cleared(entity: String)
signal log_received(entity: String, tag: String, message: String, ts: float)

@export var server_url: String = "ws://localhost:8765"
@export var participant_name: String = "Re"
@export var participant_type: String = "human"
@export var auto_reconnect: bool = true
@export var reconnect_delay: float = 5.0

var _socket: WebSocketPeer = WebSocketPeer.new()
var _connected: bool = false
var _reconnect_timer: float = 0.0
var _wants_connection: bool = false
var _connection_attempts: int = 0
var _max_attempts: int = 0  # 0 = unlimited


func _ready() -> void:
	set_process(false)


func connect_to_nexus() -> void:
	_wants_connection = true
	_connection_attempts = 0
	_attempt_connect()


func _attempt_connect() -> void:
	var url = "%s/ws/%s?type=%s" % [server_url, participant_name, participant_type]
	var err = _socket.connect_to_url(url)
	if err != OK:
		push_error("NexusConnection: Failed to initiate connection: %s" % err)
		return
	_connection_attempts += 1
	set_process(true)


func disconnect_from_nexus() -> void:
	_wants_connection = false
	_socket.close()
	_connected = false
	set_process(false)
	disconnected.emit()


func is_nexus_connected() -> bool:
	return _connected


## --- Send methods ---

func send_chat(text: String) -> void:
	_send({"content": text, "msg_type": "chat"})


func send_emote(text: String) -> void:
	_send({"content": text, "msg_type": "emote"})


func send_whisper(target: String, text: String) -> void:
	_send({
		"content": text,
		"msg_type": "whisper",
		"recipients": [target]
	})


func send_thought(text: String) -> void:
	_send({"content": text, "msg_type": "thought"})


func send_status(status: String) -> void:
	_send_raw({"command": "status", "status": status})


func send_command(command: String, extra: Dictionary = {}) -> void:
	var payload = {"command": command}
	payload.merge(extra)
	_send_raw(payload)


func _send(payload: Dictionary) -> void:
	if not _connected:
		return
	_socket.send_text(JSON.stringify(payload))


func _send_raw(payload: Dictionary) -> void:
	if not _connected:
		return
	_socket.send_text(JSON.stringify(payload))


## --- Process loop ---

func _process(delta: float) -> void:
	_socket.poll()
	var state = _socket.get_ready_state()
	
	match state:
		WebSocketPeer.STATE_OPEN:
			if not _connected:
				_connected = true
				_connection_attempts = 0
				_reconnect_timer = 0.0
				connected.emit()
			# Read all available packets
			while _socket.get_available_packet_count() > 0:
				var raw = _socket.get_packet().get_string_from_utf8()
				_handle_raw_message(raw)
		
		WebSocketPeer.STATE_CLOSING:
			pass
		
		WebSocketPeer.STATE_CLOSED:
			var was_connected = _connected
			_connected = false
			if was_connected:
				disconnected.emit()
			# Auto-reconnect
			if _wants_connection and auto_reconnect:
				_reconnect_timer += delta
				if _reconnect_timer >= reconnect_delay:
					_reconnect_timer = 0.0
					_attempt_connect()
			else:
				set_process(false)


func _handle_raw_message(raw: String) -> void:
	var json_parser = JSON.new()
	var err = json_parser.parse(raw)
	if err != OK:
		push_warning("NexusConnection: Bad JSON: %s" % raw.left(100))
		return

	var event: Dictionary = json_parser.data
	var event_type: String = event.get("event_type", "")
	var data: Dictionary = event.get("data", {})

	# Handle raw log messages (not wrapped in ServerEvent format)
	var raw_type: String = event.get("type", "")
	if raw_type == "log":
		log_received.emit(
			event.get("entity", ""), event.get("tag", ""),
			event.get("message", ""), event.get("ts", 0.0)
		)
		return
	elif raw_type == "log_batch":
		var logs = event.get("logs", [])
		if logs is Array:
			for entry in logs:
				if entry is Dictionary:
					log_received.emit(
						entry.get("entity", ""), entry.get("tag", ""),
						entry.get("message", ""), entry.get("ts", 0.0)
					)
		return

	match event_type:
		"message":
			message_received.emit(data)
		"history":
			var messages_raw = data.get("messages")
			var messages: Array = messages_raw if messages_raw is Array else []
			history_received.emit(messages)
		"participant_list":
			participant_update.emit(data)
		"status_update":
			status_update.emit(data)
		"error":
			error_received.emit(data.get("message", "Unknown error"))
		"auto_status", "auto_goal", "auto_monologue":
			auto_event_received.emit(event_type, event.get("entity", ""), data)
		"canvas_update":
			var entity_name: String = data.get("entity", "")
			var b64: String = data.get("base64", "")
			var dims: Array = data.get("dimensions", [0, 0])
			var iteration: int = data.get("iteration", 0)
			canvas_updated.emit(entity_name, b64, dims, iteration)
		"canvas_clear":
			canvas_cleared.emit(data.get("entity", ""))
		_:
			pass


func get_connection_attempts() -> int:
	return _connection_attempts
