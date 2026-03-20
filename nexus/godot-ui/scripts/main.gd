## Main - Application entry point.
## Creates panels via PanelManager, manages connections, routes messages.
## 
## THREE ROOMS ARCHITECTURE:
##   Kay's Room  (ws://localhost:8770) — private 1:1
##   Reed's Room (ws://localhost:8771) — private 1:1
##   The Nexus   (ws://localhost:8765) — group chat (manual connect)
extends Control

const ChatPanelScene = preload("res://scenes/ChatPanel.tscn")

@onready var nexus: NexusConnection = $NexusConnection

## Private room connections (added as child nodes in _ready)
var _kay_private: PrivateConnection
var _reed_private: PrivateConnection

@onready var panel_mgr: PanelManager = %PanelManager

## Chat panel references (content inside DockablePanels)
var _nexus_chat: ChatPanel
var _kay_chat: ChatPanel
var _reed_chat: ChatPanel

## Sidebar + feature panels
var _sidebar: Sidebar
var _feature_panel: FeaturePanel
var _easel_panel: EaselPanel
var _gallery_panel: GalleryPanel
var _room_panel: RoomPanel
var _system_dashboard: SystemDashboard
var _voice_mgr: VoiceManager
var _face_panel_kay: FacePanel
var _face_panel_reed: FacePanel

## Participant tracking
var _participants: Dictionary = {}
var _user_name: String = "Re"
var _nexus_url: String = "ws://localhost:8765"
var _reconnect_notice_shown: bool = false
var _nexus_active: bool = false  # Whether we WANT Nexus connected

## Room state tracking
var _room_registry: Dictionary = {
	"den": {"label": "Kay's Den", "entities": [], "objects": 11},
	"sanctum": {"label": "Reed's Sanctum", "entities": [], "objects": 7},
	"commons": {"label": "The Commons", "entities": [], "objects": 9},
}
var _current_room_view: String = "commons"
var _auto_follow: bool = true
var _room_popup: PopupMenu

## Track which entities are active in Nexus (toggle who's in group chat)
var _nexus_members: Dictionary = {"Kay": true, "Reed": true}

## Curation response routing — when set, next private response goes to curate panel
var _curate_pending_entity: String = ""


func _ready() -> void:
	get_tree().root.min_size = Vector2(900, 600)
	await get_tree().process_frame
	_create_panels()
	_setup_sidebar()
	_setup_private_rooms()
	_setup_nexus()
	_setup_voice()  # Comment this line out if reconnect loop happens, to test
	await get_tree().process_frame
	panel_mgr.arrange_default()
	
	# Auto-connect to private rooms (always available)
	_kay_private.connect_to_room()
	_reed_private.connect_to_room()


## ========================================================================
## Panel creation
## ========================================================================

func _create_panels() -> void:
	var screen = get_viewport_rect().size
	
	# --- Nexus group chat panel ---
	_nexus_chat = ChatPanelScene.instantiate() as ChatPanel
	panel_mgr.create_panel(
		"nexus", "NEXUS", "the crossroads",
		Vector2(10, 10), Vector2(screen.x * 0.55, screen.y - 50),
		_nexus_chat
	)
	_nexus_chat.configure("nexus", true)
	_nexus_chat.message_submitted.connect(_on_nexus_message)
	
	# --- Kay panel ---
	_kay_chat = ChatPanelScene.instantiate() as ChatPanel
	panel_mgr.create_panel(
		"kay", "KAY ZERO", "[entity-type]",
		Vector2(screen.x * 0.55 + 20, 10),
		Vector2(screen.x * 0.44, screen.y * 0.48),
		_kay_chat
	)
	_kay_chat.configure("kay", true)
	_kay_chat.message_submitted.connect(_on_wrapper_message.bind("Kay"))
	_kay_chat.warmup_requested.connect(_on_warmup.bind("Kay"))
	_kay_chat.affect_changed.connect(_on_affect.bind("Kay"))
	
	# --- Reed panel ---
	_reed_chat = ChatPanelScene.instantiate() as ChatPanel
	panel_mgr.create_panel(
		"reed", "REED", "teal-gold serpent",
		Vector2(screen.x * 0.55 + 20, screen.y * 0.5 + 10),
		Vector2(screen.x * 0.44, screen.y * 0.48),
		_reed_chat
	)
	_reed_chat.configure("reed", true)
	_reed_chat.message_submitted.connect(_on_wrapper_message.bind("Reed"))
	_reed_chat.warmup_requested.connect(_on_warmup.bind("Reed"))
	_reed_chat.affect_changed.connect(_on_affect.bind("Reed"))
	
	# Welcome messages
	_nexus_chat.add_system_message("Nexus UI initialized")
	_nexus_chat.add_system_message("Drag panels to rearrange • Ctrl+1/2/3 to focus • Ctrl+0 to reset")
	_nexus_chat.add_system_message("Right sidebar: 📚Sessions 🧠Auto 📋Curate 📄Media ⚙Settings")
	
	# --- Room panel (spatial view) ---
	_room_panel = RoomPanel.new()
	panel_mgr.create_panel(
		"room", "ROOMS ▼", "spatial view",
		Vector2(screen.x * 0.55 + 20, 10),
		Vector2(screen.x * 0.44, screen.y * 0.3),
		_room_panel
	)
	_setup_room_popup()
	_room_panel.mini_map_room_clicked.connect(_on_mini_map_room_clicked)
	# Start minimized — user opens via Ctrl+R
	var room_dock = panel_mgr.get_panel("room")
	if room_dock:
		room_dock._minimize_panel()

	# --- System dashboard (live dashboard) ---
	_system_dashboard = SystemDashboard.new()
	panel_mgr.create_panel(
		"system", "SYSTEM", "live dashboard",
		Vector2(10, screen.y * 0.5),
		Vector2(screen.x * 0.55, screen.y * 0.48),
		_system_dashboard
	)
	# Start minimized — user opens via Ctrl+D
	var system_dock = panel_mgr.get_panel("system")
	if system_dock:
		system_dock._minimize_panel()

	# --- Face panels (expression rendering) ---
	_face_panel_kay = FacePanel.new()
	_face_panel_kay.set_entity("kay")
	panel_mgr.create_panel(
		"face_kay", "KAY FACE", "expression",
		Vector2(screen.x * 0.7, screen.y * 0.5),
		Vector2(200, 250),
		_face_panel_kay
	)
	# Start minimized — user opens via Ctrl+F
	var face_kay_dock = panel_mgr.get_panel("face_kay")
	if face_kay_dock:
		face_kay_dock._minimize_panel()

	_face_panel_reed = FacePanel.new()
	_face_panel_reed.set_entity("reed")
	panel_mgr.create_panel(
		"face_reed", "REED FACE", "expression",
		Vector2(screen.x * 0.7 + 210, screen.y * 0.5),
		Vector2(200, 250),
		_face_panel_reed
	)
	# Start minimized
	var face_reed_dock = panel_mgr.get_panel("face_reed")
	if face_reed_dock:
		face_reed_dock._minimize_panel()


## ========================================================================
## Sidebar + Feature Panels
## ========================================================================

func _setup_sidebar() -> void:
	# Sidebar icon strip — right edge
	_sidebar = Sidebar.new()
	_sidebar.name = "Sidebar"
	add_child(_sidebar)
	
	# Feature panel — slides out left of sidebar
	_feature_panel = FeaturePanel.new()
	_feature_panel.name = "FeaturePanel"
	add_child(_feature_panel)
	
	# Connect sidebar toggle to feature panel
	_sidebar.feature_toggled.connect(_on_sidebar_feature_toggled)
	_sidebar.dock_changed.connect(_on_sidebar_dock_changed)
	
	# Connect session browser load signal
	_feature_panel.session_browser.session_load_requested.connect(_on_session_load)
	
	# Connect auto panel signals
	_feature_panel.auto_panel.auto_session_requested.connect(_on_auto_session)
	
	# Connect curate panel signals
	_feature_panel.curate_panel.curate_action.connect(_on_curate_action)
	
	# Canvas signals now handled by EaselWindow (created below)
	
	# Connect media panel signals
	_feature_panel.media_panel.file_import_requested.connect(_on_file_import)
	
	# Connect settings signals
	_feature_panel.settings_panel.setting_changed.connect(_on_setting_changed)
	
	# Create the easel as a managed panel (starts minimized)
	_easel_panel = EaselPanel.new()
	var screen = get_viewport_rect().size
	panel_mgr.create_panel(
		"easel", "EASEL", "🎨 canvas",
		Vector2(screen.x * 0.25, screen.y * 0.1),
		Vector2(480, screen.y * 0.8),
		_easel_panel
	)
	_easel_panel.clear_requested.connect(_on_canvas_clear_requested)
	# Start minimized — user opens via sidebar 🎨 button or Ctrl+E
	var easel_dock = panel_mgr.get_panel("easel")
	if easel_dock:
		easel_dock._minimize_panel()
	
	# Create the gallery panel (starts minimized)
	_gallery_panel = GalleryPanel.new()
	panel_mgr.create_panel(
		"easel_gallery", "GALLERY", "🖼️ all paintings",
		Vector2(screen.x * 0.3, screen.y * 0.05),
		Vector2(520, screen.y * 0.85),
		_gallery_panel
	)
	var gallery_dock = panel_mgr.get_panel("easel_gallery")
	if gallery_dock:
		gallery_dock._minimize_panel()
	
	# Position on resize
	get_viewport().size_changed.connect(_position_sidebar)
	_position_sidebar()


func _position_sidebar() -> void:
	var screen = get_viewport_rect().size
	var thick := _sidebar.get_thickness()  # 44
	var feat_w := 320
	var feat_h := 320  # For horizontal docks
	var dock = _sidebar.get_dock()
	var feat_open = _feature_panel.visible
	
	match dock:
		Sidebar.Dock.RIGHT:
			_sidebar.position = Vector2(screen.x - thick, 0)
			_sidebar.size = Vector2(thick, screen.y)
			_feature_panel.position = Vector2(screen.x - thick - feat_w, 0)
			_feature_panel.size = Vector2(feat_w, screen.y)
			panel_mgr.position = Vector2.ZERO
			panel_mgr.size = Vector2(
				screen.x - thick - (feat_w if feat_open else 0), screen.y
			)
		
		Sidebar.Dock.LEFT:
			_sidebar.position = Vector2.ZERO
			_sidebar.size = Vector2(thick, screen.y)
			_feature_panel.position = Vector2(thick, 0)
			_feature_panel.size = Vector2(feat_w, screen.y)
			var offset_x = thick + (feat_w if feat_open else 0)
			panel_mgr.position = Vector2(offset_x, 0)
			panel_mgr.size = Vector2(screen.x - offset_x, screen.y)
		
		Sidebar.Dock.TOP:
			_sidebar.position = Vector2.ZERO
			_sidebar.size = Vector2(screen.x, thick)
			_feature_panel.position = Vector2(0, thick)
			_feature_panel.size = Vector2(screen.x, feat_h)
			var offset_y = thick + (feat_h if feat_open else 0)
			panel_mgr.position = Vector2(0, offset_y)
			panel_mgr.size = Vector2(screen.x, screen.y - offset_y)
		
		Sidebar.Dock.BOTTOM:
			_sidebar.position = Vector2(0, screen.y - thick)
			_sidebar.size = Vector2(screen.x, thick)
			_feature_panel.position = Vector2(0, screen.y - thick - feat_h)
			_feature_panel.size = Vector2(screen.x, feat_h)
			panel_mgr.position = Vector2.ZERO
			panel_mgr.size = Vector2(
				screen.x, screen.y - thick - (feat_h if feat_open else 0)
			)


func _on_sidebar_feature_toggled(feature_id: String, show: bool) -> void:
	# Canvas gets its own managed panel
	if feature_id == "canvas":
		var easel_dock = panel_mgr.get_panel("easel")
		if not easel_dock:
			return
		if show:
			easel_dock.restore()
			_easel_panel.fetch_latest_canvas()
		else:
			easel_dock._minimize_panel()
		return
	# Gallery gets its own managed panel
	if feature_id == "gallery":
		var gallery_dock = panel_mgr.get_panel("easel_gallery")
		if not gallery_dock:
			return
		if show:
			gallery_dock.restore()
			_gallery_panel.fetch_gallery()
		else:
			gallery_dock._minimize_panel()
		return
	# Face panels - toggle both together
	if feature_id == "face":
		var kay_face = panel_mgr.get_panel("face_kay")
		var reed_face = panel_mgr.get_panel("face_reed")
		if show:
			if kay_face:
				kay_face.restore()
			if reed_face:
				reed_face.restore()
		else:
			if kay_face:
				kay_face._minimize_panel()
			if reed_face:
				reed_face._minimize_panel()
		return
	if show:
		_feature_panel.show_feature(feature_id)
	else:
		_feature_panel.hide_feature(feature_id)
	# Adjust panel manager layout when feature panel opens/closes
	_position_sidebar()


func _on_sidebar_dock_changed(_new_dock: int) -> void:
	_position_sidebar()


func _on_session_load(filename: String, messages: Array) -> void:
	# Display loaded session in Nexus chat as history
	_nexus_chat.clear_chat()
	_nexus_chat.add_system_message("=== Loaded session: %s ===" % filename)
	
	for msg in messages:
		if msg is Dictionary:
			var sender: String = msg.get("sender", "?")
			var content: String = msg.get("content", "")
			var msg_type: String = msg.get("type", "chat")
			if msg_type == "system":
				_nexus_chat.add_system_message(content)
			else:
				_nexus_chat.add_message(sender, content, msg_type)
	
	_nexus_chat.add_system_message("=== End of loaded session (%d messages) ===" % messages.size())


func _on_auto_session(entity: String, action: String) -> void:
	# Autonomous events flow through the Nexus WebSocket, so ensure it's connected
	if action == "start" and not nexus.is_nexus_connected():
		_nexus_chat.add_system_message("Auto-connecting to Nexus for autonomous events...")
		_nexus_active = true
		nexus.auto_reconnect = true
		nexus.connect_to_nexus()
		_nexus_chat.set_nexus_state(true)


func _on_auto_event(msg_type: String, entity: String, data: Dictionary) -> void:
	# Route autonomous processing events to the auto panel
	if _feature_panel and _feature_panel.auto_panel:
		_feature_panel.auto_panel.handle_auto_event(msg_type, entity, data)
	
	# Also show monologue snippets in the entity's chat panel
	if msg_type == "auto_monologue":
		var text = str(data.get("text", ""))
		if not text.is_empty():
			var chat = _get_entity_chat(entity)
			var preview = text.substr(0, 200)
			if text.length() > 200:
				preview += "..."
			chat.add_system_message("🧠 %s" % preview)
	elif msg_type == "auto_goal":
		var desc = str(data.get("description", ""))
		if not desc.is_empty():
			var chat = _get_entity_chat(entity)
			chat.add_system_message("🧠 exploring: %s" % desc.substr(0, 120))


func _on_canvas_updated(entity: String, base64_png: String, dimensions: Array, iteration: int) -> void:
	# Route canvas updates to the easel panel
	if _easel_panel:
		_easel_panel.on_canvas_updated(entity, base64_png, dimensions, iteration)
	# Refresh gallery if it's visible
	if _gallery_panel and _gallery_panel.visible:
		_gallery_panel.fetch_gallery()
	# Also show a brief note in the entity's chat
	var chat = _get_entity_chat(entity)
	chat.add_system_message("🎨 canvas iteration %d — %dx%d" % [iteration, dimensions[0] if dimensions.size() > 0 else 0, dimensions[1] if dimensions.size() > 1 else 0])


func _on_canvas_cleared(entity: String) -> void:
	if _easel_panel:
		_easel_panel.on_canvas_cleared(entity)


func _on_canvas_clear_requested(entity: String) -> void:
	# Send clear command to server via Nexus WebSocket
	if _nexus_active and nexus.is_nexus_connected():
		nexus.send_command("clear_canvas", {"entity": entity})


func _on_easel_paint_command(entity: String, text: String) -> void:
	# Route paint commands from the easel command bar to the Nexus server.
	# Supports raw JSON array or simple text that gets forwarded as-is.
	if not _nexus_active or not nexus.is_nexus_connected():
		_nexus_chat.add_system_message("Not connected to Nexus — can't send paint command")
		return
	
	var trimmed = text.strip_edges()
	
	# Try parsing as JSON array of paint commands
	var json_test = JSON.parse_string(trimmed)
	if json_test is Array:
		nexus.send_command("paint", {"entity": entity, "commands": json_test})
		_nexus_chat.add_system_message("🎨 Sent %d paint commands for %s" % [json_test.size(), entity])
		return
	
	# Otherwise, wrap as a single text command and let the server figure it out
	# For now, send as a chat message with paint intent
	nexus.send_command("paint", {
		"entity": entity,
		"commands": [{"action": "draw_text", "text": trimmed, "x": 20, "y": 20, "color": "#4fc2e9"}]
	})
	_nexus_chat.add_system_message("🎨 Painted text for %s: %s" % [entity, trimmed.substr(0, 60)])


func _on_curate_action(entity: String, action: String, data: Dictionary) -> void:
	# Route curation commands to wrapper
	var conn: PrivateConnection = _kay_private if entity == "Kay" else _reed_private
	_curate_pending_entity = entity
	_feature_panel.curate_panel.set_status("Processing %s..." % action)
	match action:
		"search":
			conn.send_chat("/memory search %s" % data.get("query", ""))
		"refresh":
			conn.send_chat("/memory list")
		"consolidate":
			conn.send_chat("/memory consolidate")
		"prune":
			conn.send_chat("/memory prune")
		"contradictions":
			conn.send_chat("/memory contradictions")
		"pending":
			conn.send_chat("/memory pending")
		"approve_all":
			conn.send_chat("/memory approve all")
		"curator_status":
			conn.send_chat("/memory curator")
		"auto_resolve":
			conn.send_chat("/memory auto_resolve")
		"curate":
			conn.send_chat("/memory curate")
		"sweep":
			conn.send_chat("/memory sweep")


func _on_file_import(path: String, entity: String) -> void:
	var conn: PrivateConnection = _kay_private if entity == "Kay" else _reed_private
	conn.send_chat("/import %s" % path)


func _on_setting_changed(key: String, value: Variant) -> void:
	match key:
		"font_size":
			# Apply to all chat panels
			pass  # TODO: propagate font size
		"reset_layout":
			panel_mgr.arrange_default()
			_position_sidebar()
		"save":
			_nexus_chat.add_system_message("Settings saved")
		"panel_bg_nexus":
			_nexus_chat.reload_background()
		"panel_bg_kay":
			_kay_chat.reload_background()
		"panel_bg_reed":
			_reed_chat.reload_background()


## ========================================================================
## Private room connections (1:1 with each entity)
## ========================================================================

func _setup_private_rooms() -> void:
	# Kay private room
	_kay_private = PrivateConnection.new()
	_kay_private.name = "KayPrivate"
	_kay_private.server_url = "ws://localhost:8770"
	_kay_private.entity_name = "Kay"
	add_child(_kay_private)
	
	_kay_private.connected.connect(_on_private_connected.bind("Kay"))
	_kay_private.disconnected.connect(_on_private_disconnected.bind("Kay"))
	_kay_private.chat_received.connect(_on_private_chat.bind("Kay"))
	_kay_private.emote_received.connect(_on_private_emote.bind("Kay"))
	_kay_private.status_received.connect(_on_private_status.bind("Kay"))
	_kay_private.system_received.connect(_on_private_system.bind("Kay"))
	_kay_private.history_received.connect(_on_private_history.bind("Kay"))
	_kay_private.room_updated.connect(_on_room_updated)
	_kay_private.room_changed.connect(_on_room_changed)
	_kay_private.logs_received.connect(_on_logs_received)
	_kay_private.log_received.connect(_on_log_received)

	# Reed private room
	_reed_private = PrivateConnection.new()
	_reed_private.name = "ReedPrivate"
	_reed_private.server_url = "ws://localhost:8771"
	_reed_private.entity_name = "Reed"
	add_child(_reed_private)

	_reed_private.connected.connect(_on_private_connected.bind("Reed"))
	_reed_private.disconnected.connect(_on_private_disconnected.bind("Reed"))
	_reed_private.chat_received.connect(_on_private_chat.bind("Reed"))
	_reed_private.emote_received.connect(_on_private_emote.bind("Reed"))
	_reed_private.status_received.connect(_on_private_status.bind("Reed"))
	_reed_private.system_received.connect(_on_private_system.bind("Reed"))
	_reed_private.history_received.connect(_on_private_history.bind("Reed"))
	_reed_private.room_updated.connect(_on_room_updated)
	_reed_private.room_changed.connect(_on_room_changed)
	_reed_private.logs_received.connect(_on_logs_received)
	_reed_private.log_received.connect(_on_log_received)


func _on_private_connected(entity: String) -> void:
	var chat = _get_entity_chat(entity)
	chat.add_system_message("Connected to %s's room" % entity)
	chat.set_status("online", Color(0.3, 0.8, 0.4))
	# Request initial room data so panel isn't blank on startup
	match entity:
		"Kay":
			_request_room_data("den")
		"Reed":
			_request_room_data("sanctum")


func _on_private_disconnected(entity: String) -> void:
	var chat = _get_entity_chat(entity)
	chat.add_system_message("%s's room disconnected — reconnecting..." % entity)
	chat.set_status("offline", Color(0.5, 0.5, 0.5))


func _on_private_chat(sender: String, content: String, entity: String) -> void:
	var chat = _get_entity_chat(entity)

	# Route curation responses to curate panel
	if _curate_pending_entity == entity:
		_curate_pending_entity = ""
		_feature_panel.curate_panel.display_results(content)
		_feature_panel.curate_panel.set_status("Done")
		# Also show in chat for context
		chat.add_message(sender, content)
		return

	chat.add_message(sender, content)

	# Auto-speak if voice mode is active OR last input was voice-initiated
	if _voice_mgr != null:
		var should_speak = false
		if chat.has_method("is_voice_active") and chat.is_voice_active():
			should_speak = true
		elif chat.has_method("was_last_input_voice") and chat.was_last_input_voice():
			should_speak = true
		if should_speak:
			var panel_id = "kay" if entity.to_lower() == "kay" else "reed"
			_voice_mgr.speak(content, entity, panel_id)
			if chat.has_method("clear_voice_input_flag"):
				chat.clear_voice_input_flag()


func _on_private_emote(sender: String, content: String, entity: String) -> void:
	var chat = _get_entity_chat(entity)
	chat.add_message(sender, content, "emote")


func _on_private_status(status: String, entity: String) -> void:
	var chat = _get_entity_chat(entity)
	_set_entity_status(chat, status)


func _on_private_system(content: String, entity: String) -> void:
	var chat = _get_entity_chat(entity)
	chat.add_system_message(content)


func _on_private_history(messages: Array, entity: String) -> void:
	var chat = _get_entity_chat(entity)
	if messages.is_empty():
		return
	chat.add_system_message("— session history —")
	for msg in messages:
		if msg is Dictionary:
			var sender = msg.get("sender", "?")
			var content = msg.get("content", "")
			var msg_type = msg.get("type", "chat")
			var timestamp = msg.get("timestamp", "")
			chat.add_message(sender, content, msg_type, timestamp)
	chat.add_system_message("— end history —")


func _on_room_updated(state: Dictionary) -> void:
	if _room_panel:
		_room_panel.update_room(state)
		# Auto-restore room panel if minimized on first update
		var room_dock = panel_mgr.get_panel("room")
		if room_dock and room_dock.is_minimized():
			room_dock.restore()


func _on_room_changed(entity: String, to_room: String, from_room: String) -> void:
	# Entity moved to a different room — update registry
	print("[ROOM] %s moved from %s to %s" % [entity, from_room, to_room])

	# Update registry
	if from_room and _room_registry.has(from_room):
		var ents: Array = _room_registry[from_room].get("entities", [])
		ents.erase(entity)
		_room_registry[from_room]["entities"] = ents
	if to_room and _room_registry.has(to_room):
		var ents: Array = _room_registry[to_room].get("entities", [])
		if not ents.has(entity):
			ents.append(entity)
		_room_registry[to_room]["entities"] = ents

	# Auto-follow: switch view to entity's new room
	if _auto_follow and to_room and _room_registry.has(to_room):
		_current_room_view = to_room
		_switch_room_view(to_room)

	# Refresh popup and mini-map to show updated entity locations
	_refresh_room_popup()
	_update_mini_map()


func _setup_room_popup() -> void:
	_room_popup = PopupMenu.new()
	_room_popup.name = "RoomPopup"
	add_child(_room_popup)

	_refresh_room_popup()
	_room_popup.id_pressed.connect(_on_room_selected)

	# Wire the room panel title click to open popup
	var room_dock = panel_mgr.get_panel("room")
	if room_dock and room_dock.has_method("set_title_clickable"):
		room_dock.set_title_clickable(true)
		room_dock.title_clicked.connect(_on_room_title_clicked)


func _refresh_room_popup() -> void:
	if not _room_popup:
		return
	_room_popup.clear()

	var idx := 0
	for room_id in ["den", "sanctum", "commons"]:
		var info: Dictionary = _room_registry.get(room_id, {})
		var label: String = info.get("label", room_id.capitalize())
		var entities: Array = info.get("entities", [])

		# Build display string with entity indicators
		var display := label
		if not entities.is_empty():
			var markers: PackedStringArray = []
			for ent in entities:
				if ent == "Kay":
					markers.append("●")  # Pink dot for Kay
				elif ent == "Reed":
					markers.append("◆")  # Teal marker for Reed
			if not markers.is_empty():
				display += "  " + " ".join(markers)

		_room_popup.add_item(display, idx)

		# Check current room
		if room_id == _current_room_view:
			_room_popup.set_item_checked(idx, true)

		idx += 1

	# Add separator and auto-follow toggle
	_room_popup.add_separator()
	var follow_label := "Auto-Follow [ON]" if _auto_follow else "Auto-Follow [OFF]"
	_room_popup.add_check_item(follow_label, 100)
	_room_popup.set_item_checked(_room_popup.get_item_index(100), _auto_follow)


func _on_room_title_clicked() -> void:
	var room_dock = panel_mgr.get_panel("room")
	if room_dock:
		var title_pos: Vector2 = room_dock.global_position + Vector2(10, 30)
		_room_popup.position = Vector2i(int(title_pos.x), int(title_pos.y))
		_room_popup.popup()


func _on_room_selected(id: int) -> void:
	if id == 100:
		# Toggle auto-follow
		_auto_follow = not _auto_follow
		_refresh_room_popup()
		var msg := "Auto-follow enabled" if _auto_follow else "Auto-follow disabled"
		_nexus_chat.add_system_message(msg)
		return

	# Room selection
	var rooms := ["den", "sanctum", "commons"]
	if id >= 0 and id < rooms.size():
		var room_id: String = rooms[id]
		_current_room_view = room_id
		_switch_room_view(room_id)
		_refresh_room_popup()


func _switch_room_view(room_id: String) -> void:
	if not _room_registry.has(room_id):
		return

	var info: Dictionary = _room_registry[room_id]
	var label: String = info.get("label", room_id.capitalize())

	# Update panel title
	var room_dock = panel_mgr.get_panel("room")
	if room_dock and room_dock.has_method("set_title"):
		room_dock.set_title(label)

	# Tell room panel to switch view
	if _room_panel:
		_room_panel.switch_room(room_id)
		_room_panel.set_mini_map_current_room(room_id)

	# Request room data from server
	_request_room_data(room_id)


func _request_room_data(room_id: String) -> void:
	# Request fresh room state — route through private connections
	# (both Kay and Reed have the room manager and can serve ANY room's data)
	var conn: PrivateConnection
	match room_id:
		"den":
			conn = _kay_private
		"sanctum":
			conn = _reed_private
		"commons":
			# Route through Kay's private room (has room manager for all rooms)
			# Fall back to Reed if Kay isn't connected
			if _kay_private and _kay_private.is_room_connected():
				conn = _kay_private
			elif _reed_private and _reed_private.is_room_connected():
				conn = _reed_private

	if conn and conn.is_room_connected():
		conn.send_command("room_data_request", {"room": room_id})


func _on_mini_map_room_clicked(room_id: String) -> void:
	# Mini-map click navigates to that room
	_current_room_view = room_id
	_switch_room_view(room_id)
	_refresh_room_popup()


func _update_mini_map() -> void:
	# Sync mini-map with current room registry
	if _room_panel:
		_room_panel.update_mini_map(_room_registry)
		_room_panel.set_mini_map_current_room(_current_room_view)


func _on_logs_received(entries: Array) -> void:
	if _system_dashboard:
		_system_dashboard.handle_logs(entries)


func _on_log_received(entity: String, tag: String, message: String, ts: float) -> void:
	if _system_dashboard:
		_system_dashboard.add_log(entity, tag, message, ts)


## ========================================================================
## Voice setup
## ========================================================================

func _setup_voice() -> void:
	_voice_mgr = VoiceManager.new()
	_voice_mgr.name = "VoiceManager"
	add_child(_voice_mgr)

	# Connect voice toggle signals from all chat panels
	if _kay_chat:
		_kay_chat.voice_toggled.connect(_on_voice_toggled.bind("kay"))
	if _reed_chat:
		_reed_chat.voice_toggled.connect(_on_voice_toggled.bind("reed"))
	if _nexus_chat:
		_nexus_chat.voice_toggled.connect(_on_voice_toggled.bind("nexus"))

	# Connect voice manager signals
	_voice_mgr.transcription_ready.connect(_on_transcription_ready)
	_voice_mgr.playback_finished.connect(_on_playback_finished)
	_voice_mgr.voice_error.connect(_on_voice_error)


func _on_voice_toggled(enabled: bool, panel_id: String) -> void:
	# Update panel voice state
	var chat = _get_chat_panel(panel_id)
	if chat:
		chat.set_voice_active(enabled)

	if enabled:
		_voice_mgr.start_recording(panel_id)
	else:
		_voice_mgr.stop_recording()
		# Reset voice mode on wrapper when voice toggle is disabled
		match panel_id:
			"kay":
				_kay_private.send_command("set_voice_mode", {"enabled": false})
			"reed":
				_reed_private.send_command("set_voice_mode", {"enabled": false})


func _on_transcription_ready(text: String, panel_id: String) -> void:
	if text.strip_edges().is_empty():
		_get_chat_panel(panel_id).add_system_message("(no speech detected)")
		return

	# Send transcribed text as a regular chat message
	# Set voice mode BEFORE sending chat so wrapper uses fast path
	match panel_id:
		"kay":
			_kay_private.send_command("set_voice_mode", {"enabled": true})
			_kay_private.send_chat(text)
			_kay_chat.add_message(_user_name, text)
			_kay_chat.mark_voice_input()
		"reed":
			_reed_private.send_command("set_voice_mode", {"enabled": true})
			_reed_private.send_chat(text)
			_reed_chat.add_message(_user_name, text)
			_reed_chat.mark_voice_input()
		"nexus":
			# Nexus mode doesn't use voice fast path (goes through group chat)
			if _nexus_active and nexus.is_nexus_connected():
				nexus.send_chat(text)
				_nexus_chat.add_message(_user_name, text)
				_nexus_chat.mark_voice_input()
			else:
				_nexus_chat.add_system_message("Nexus not connected")


func _on_playback_finished(panel_id: String) -> void:
	var chat = _get_chat_panel(panel_id)
	if chat:
		chat.show_speaking_indicator(false)


func _on_voice_error(message: String) -> void:
	# Show error in whichever panel is active
	var panel_id = _voice_mgr.get_active_panel()
	if not panel_id.is_empty():
		_get_chat_panel(panel_id).add_system_message("Voice error: " + message)
	else:
		_nexus_chat.add_system_message("Voice error: " + message)


func _get_chat_panel(panel_id: String) -> ChatPanel:
	match panel_id:
		"kay": return _kay_chat
		"reed": return _reed_chat
		"nexus": return _nexus_chat
		_: return _nexus_chat


func _get_entity_chat(entity: String) -> ChatPanel:
	if entity.to_lower() in ["kay", "kayzero", "kay zero"]:
		return _kay_chat
	return _reed_chat


## ========================================================================
## Emergency Stop (Safety Critical)
## ========================================================================

func _emergency_stop(entity: String = "") -> void:
	"""
	SAFETY CRITICAL: Immediately halt all touch processing.

	If no entity specified, stops ALL entities.
	This clears touch queues and triggers circuit breakers.
	"""
	var entities_to_stop: Array = []
	if entity.is_empty():
		entities_to_stop = ["Kay", "Reed"]
	else:
		entities_to_stop = [entity.capitalize()]

	for ent in entities_to_stop:
		# Call emergency-stop endpoint
		var url = "http://localhost:8765/touch/%s/emergency-stop" % ent.to_lower()
		var http = HTTPRequest.new()
		add_child(http)
		http.request_completed.connect(_on_emergency_stop_complete.bind(ent, http))

		var headers = ["Content-Type: application/json"]
		var body = JSON.stringify({"reason": "User panic button triggered"})
		var err = http.request(url, headers, HTTPClient.METHOD_POST, body)

		if err != OK:
			_nexus_chat.add_system_message("⛔ EMERGENCY STOP failed for %s: HTTP error" % ent)
		else:
			_nexus_chat.add_system_message("⛔ EMERGENCY STOP triggered for %s" % ent)
			var chat = _get_entity_chat(ent)
			chat.add_system_message("⛔ EMERGENCY STOP — touch processing halted")


func _on_emergency_stop_complete(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray, entity: String, http: HTTPRequest) -> void:
	http.queue_free()
	if response_code == 200:
		_nexus_chat.add_system_message("⛔ %s circuit breaker active — touch suspended" % entity)
	else:
		_nexus_chat.add_system_message("⛔ Emergency stop for %s returned code %d" % [entity, response_code])


func _get_private_conn(entity: String) -> PrivateConnection:
	if entity.to_lower() in ["kay", "kayzero", "kay zero"]:
		return _kay_private
	return _reed_private


func _normalize_entity_name(raw: String) -> String:
	## Returns canonical name ("Kay" or "Reed") or "" if unknown.
	var lower = raw.strip_edges().to_lower()
	if lower in ["kay", "kayzero", "kay zero", "k"]:
		return "Kay"
	elif lower in ["reed", "r"]:
		return "Reed"
	return ""


## ========================================================================
## Nexus connection
## ========================================================================

func _setup_nexus() -> void:
	nexus.connected.connect(_on_connected)
	nexus.disconnected.connect(_on_disconnected)
	nexus.message_received.connect(_on_message_received)
	nexus.participant_update.connect(_on_participant_update)
	nexus.status_update.connect(_on_status_update)
	nexus.history_received.connect(_on_history_received)
	nexus.error_received.connect(_on_error_received)
	nexus.auto_event_received.connect(_on_auto_event)
	nexus.canvas_updated.connect(_on_canvas_updated)
	nexus.canvas_cleared.connect(_on_canvas_cleared)
	nexus.log_received.connect(_on_log_received)
	
	nexus.server_url = _nexus_url
	nexus.participant_name = _user_name
	nexus.auto_reconnect = true  # Auto-reconnect on disconnect
	
	# Wire the nexus connect/disconnect button
	_nexus_chat.nexus_toggle_requested.connect(_on_nexus_toggle)
	
	# Auto-connect to Nexus server (needed for canvas broadcasts + group chat)
	_nexus_active = true
	_nexus_chat.add_system_message("Connecting to Nexus at %s..." % _nexus_url)
	nexus.connect_to_nexus()
	_kay_chat.add_system_message("Connecting to Kay's room...")
	_reed_chat.add_system_message("Connecting to Reed's room...")


func _on_nexus_toggle(should_connect: bool) -> void:
	if should_connect:
		_nexus_active = true
		_nexus_chat.add_system_message("Connecting to %s..." % _nexus_url)
		nexus.auto_reconnect = true
		nexus.connect_to_nexus()
	else:
		_nexus_active = false
		nexus.auto_reconnect = false
		nexus.disconnect_from_nexus()
		_nexus_chat.set_nexus_state(false)
		_nexus_chat.add_system_message("Disconnected from group chat — private rooms still active")


func _on_connected() -> void:
	_reconnect_notice_shown = false
	_nexus_active = true
	# Clear stale messages before history replay to prevent duplicates
	_nexus_chat.clear_chat()
	_nexus_chat.add_system_message("Connected to Nexus!")
	_nexus_chat.set_status("ONLINE", Color(0.3, 0.8, 0.4))
	_nexus_chat.set_nexus_state(true)


func _on_disconnected() -> void:
	_nexus_chat.add_system_message("Disconnected from Nexus group")
	_nexus_chat.set_status("OFFLINE", Color(0.8, 0.3, 0.3))
	_nexus_chat.set_nexus_state(false)
	_participants.clear()
	if _nexus_active and not _reconnect_notice_shown:
		_reconnect_notice_shown = true
		_nexus_chat.add_system_message("Auto-reconnecting...")


func _on_error_received(message: String) -> void:
	_nexus_chat.add_system_message("Error: %s" % message)


## ========================================================================
## Message routing
## ========================================================================

func _on_message_received(data: Dictionary) -> void:
	var sender: String = data.get("sender", "???")
	var content: String = data.get("content", "")
	var msg_type: String = data.get("msg_type", "chat")
	var timestamp: String = data.get("timestamp", "")
	var recipients_raw = data.get("recipients")
	var recipients: Array = recipients_raw if recipients_raw is Array else []
	
	# Filter by Nexus membership (skip messages from removed entities)
	var sender_entity = _normalize_entity_name(sender)
	if sender_entity and not _nexus_members.get(sender_entity, true):
		return  # Entity removed from group
	
	# Skip our own messages — we already added them locally for instant feedback
	if sender == _user_name:
		return
	
	# Nexus messages go to Nexus panel ONLY (entity panels are private DMs)
	var is_whisper = msg_type == "whisper"
	var involves_us = not is_whisper or recipients.has(_user_name) or sender == _user_name
	
	if involves_us or not is_whisper:
		_nexus_chat.add_message(sender, content, msg_type, timestamp)


## ========================================================================
## Participant & status tracking
## ========================================================================

func _on_participant_update(data: Dictionary) -> void:
	var participants_raw = data.get("participants")
	var participants: Array = participants_raw if participants_raw is Array else []
	_participants.clear()
	
	var names: PackedStringArray = []
	for p in participants:
		var pname: String = p.get("name", "?") if p is Dictionary else str(p)
		var status: String = p.get("status", "online") if p is Dictionary else "online"
		var ptype: String = p.get("participant_type", "?") if p is Dictionary else "?"
		_participants[pname] = {"type": ptype, "status": status}
		names.append(pname)
	
	_nexus_chat.add_system_message("In session: %s" % ", ".join(names))
	# NOTE: Entity panel statuses managed by private room connections, not Nexus


func _on_status_update(data: Dictionary) -> void:
	var sname: String = data.get("name", "")
	var status: String = data.get("status", "online")
	
	if sname in _participants:
		_participants[sname]["status"] = status
	
	# Nexus status only shown in Nexus panel context, not entity panels
	# Entity panels get status from their private room connections


func _set_entity_status(chat: ChatPanel, status: String) -> void:
	match status:
		"online":
			chat.set_status("online", Color(0.3, 0.8, 0.4))
		"thinking":
			chat.set_status("thinking...", Color(0.9, 0.7, 0.2))
		"typing":
			chat.set_status("typing...", Color(0.5, 0.8, 0.9))
		"idle":
			chat.set_status("idle", Color(0.6, 0.6, 0.6))
		"away":
			chat.set_status("away", Color(0.5, 0.5, 0.5))
		_:
			chat.set_status(status, Color(0.6, 0.6, 0.6))


## ========================================================================
## History replay
## ========================================================================

func _on_history_received(messages: Array) -> void:
	for msg in messages:
		if msg is Dictionary:
			_on_message_received(msg)


## ========================================================================
## User input handlers
## ========================================================================

func _on_nexus_message(text: String) -> void:
	if text.begins_with("/"):
		_handle_command(text)
		return
	if not _nexus_active or not nexus.is_nexus_connected():
		_nexus_chat.add_system_message("Not connected — press Connect or type /connect")
		return
	nexus.send_chat(text)
	_nexus_chat.add_message(_user_name, text)


func _on_wrapper_message(text: String, wrapper_name: String) -> void:
	## Wrapper panel = private DM. Goes to private room ONLY, never Nexus.
	var target_chat: ChatPanel = _get_entity_chat(wrapper_name)
	var private_conn: PrivateConnection = _get_private_conn(wrapper_name)
	
	target_chat.add_message(_user_name, text)
	if private_conn.is_room_connected():
		private_conn.send_chat(text)
	else:
		target_chat.add_system_message("(%s's room not connected)" % wrapper_name)


func _on_warmup(wrapper_name: String) -> void:
	var target_chat: ChatPanel = _get_entity_chat(wrapper_name)
	var private_conn: PrivateConnection = _get_private_conn(wrapper_name)
	
	# Warmup always goes through private room
	if private_conn.is_room_connected():
		private_conn.send_command("warmup")
		target_chat.add_system_message("Warming up %s..." % wrapper_name)
	else:
		target_chat.add_system_message("%s's room not connected" % wrapper_name)


func _on_affect(level: float, wrapper_name: String) -> void:
	var target_chat: ChatPanel = _get_entity_chat(wrapper_name)
	var private_conn: PrivateConnection = _get_private_conn(wrapper_name)
	
	# Affect always goes through private room
	if private_conn.is_room_connected():
		private_conn.send_command("set_affect", {"value": level})
	
	# Also send through Nexus if connected (so group behavior adjusts too)
	if _nexus_active and nexus.is_nexus_connected():
		nexus.send_command("set_affect", {"target": wrapper_name, "value": level})
	
	target_chat.add_system_message("Affect → %.1f" % level)


func _handle_command(text: String) -> void:
	var parts = text.split(" ", false, 2)
	var cmd = parts[0].to_lower()
	
	match cmd:
		"/connect":
			if not _nexus_active:
				_on_nexus_toggle(true)
			else:
				_nexus_chat.add_system_message("Already connected (or connecting)")
		"/disconnect":
			if _nexus_active:
				_on_nexus_toggle(false)
			else:
				_nexus_chat.add_system_message("Already disconnected")
		"/who":
			if _participants.is_empty():
				_nexus_chat.add_system_message("No participant data yet")
			else:
				var lines: PackedStringArray = []
				for pname in _participants:
					var info = _participants[pname]
					lines.append("%s (%s) — %s" % [pname, info.get("type", "?"), info.get("status", "?")])
				_nexus_chat.add_system_message("Participants:\n" + "\n".join(lines))
		"/emote":
			if parts.size() > 1:
				nexus.send_emote(parts[1])
				_nexus_chat.add_message(_user_name, parts[1], "emote")
		"/think":
			if parts.size() > 1:
				nexus.send_thought(parts[1])
				_nexus_chat.add_message(_user_name, parts[1], "thought")
		"/status":
			if parts.size() > 1:
				nexus.send_status(parts[1])
				_nexus_chat.add_system_message("Status set to: %s" % parts[1])
		"/clear":
			if parts.size() > 1:
				match parts[1].to_lower():
					"nexus": _nexus_chat.clear_chat()
					"kay": _kay_chat.clear_chat()
					"reed": _reed_chat.clear_chat()
					"all":
						_nexus_chat.clear_chat()
						_kay_chat.clear_chat()
						_reed_chat.clear_chat()
			else:
				_nexus_chat.clear_chat()
		"/invite":
			if parts.size() > 1:
				var entity = _normalize_entity_name(parts[1])
				if entity:
					_nexus_members[entity] = true
					_nexus_chat.add_system_message("%s added to Nexus group" % entity)
				else:
					_nexus_chat.add_system_message("Unknown entity: %s (try Kay or Reed)" % parts[1])
			else:
				_nexus_chat.add_system_message("Usage: /invite <Kay|Reed>")
		"/remove":
			if parts.size() > 1:
				var entity = _normalize_entity_name(parts[1])
				if entity:
					_nexus_members[entity] = false
					_nexus_chat.add_system_message("%s removed from Nexus group (still in private room)" % entity)
				else:
					_nexus_chat.add_system_message("Unknown entity: %s" % parts[1])
			else:
				_nexus_chat.add_system_message("Usage: /remove <Kay|Reed>")
		"/group":
			var active: PackedStringArray = []
			for member in _nexus_members:
				if _nexus_members[member]:
					active.append(member)
			if active.is_empty():
				_nexus_chat.add_system_message("No one in the group — use /invite Kay or /invite Reed")
			else:
				_nexus_chat.add_system_message("Group members: %s" % ", ".join(active))
		"/help":
			_nexus_chat.add_system_message(
				"/connect — connect to Nexus group chat\n" +
				"/disconnect — disconnect from Nexus\n" +
				"/invite <name> — add entity to group chat\n" +
				"/remove <name> — remove entity from group\n" +
				"/group — show who's in the group\n" +
				"/who — list connected participants\n" +
				"/emote <text> — send emote\n" +
				"/think <text> — send thought\n" +
				"/status <online|away|idle> — set status\n" +
				"/clear [nexus|kay|reed|all] — clear chat\n" +
				"/save [name] — save current session\n" +
				"/sessions — open session browser\n" +
				"/help — this message"
			)
		"/save":
			_nexus_chat.add_system_message("Saving session...")
			_feature_panel.session_browser._save_current()
		"/sessions":
			_sidebar._on_feature_toggled(true, "sessions")
			if _sidebar._buttons.has("sessions"):
				_sidebar._buttons["sessions"].set_pressed_no_signal(true)
		_:
			_nexus_chat.add_system_message("Unknown command: %s (try /help)" % cmd)


## ========================================================================
## Keyboard shortcuts
## ========================================================================

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		var key = event as InputEventKey

		# F12 = EMERGENCY STOP (always available, no modifiers needed)
		if key.keycode == KEY_F12:
			_emergency_stop()  # Stop all entities
			get_viewport().set_input_as_handled()
			return

		if key.keycode == KEY_ESCAPE:
			_sidebar.close_all()
			_feature_panel.hide_all()
			get_viewport().set_input_as_handled()
		elif key.ctrl_pressed:
			match key.keycode:
				KEY_1:
					_nexus_chat.focus_input()
					get_viewport().set_input_as_handled()
				KEY_2:
					_kay_chat.focus_input()
					get_viewport().set_input_as_handled()
				KEY_3:
					_reed_chat.focus_input()
					get_viewport().set_input_as_handled()
				KEY_0:
					panel_mgr.arrange_default()
					get_viewport().set_input_as_handled()
				KEY_E:
					# Toggle easel panel
					var easel_dock = panel_mgr.get_panel("easel")
					if easel_dock:
						if easel_dock.is_minimized():
							easel_dock.restore()
							_easel_panel.fetch_latest_canvas()
						else:
							easel_dock._minimize_panel()
					get_viewport().set_input_as_handled()
				KEY_R:
					# Toggle room panel
					var room_dock = panel_mgr.get_panel("room")
					if room_dock:
						if room_dock.is_minimized():
							room_dock.restore()
						else:
							room_dock._minimize_panel()
					get_viewport().set_input_as_handled()
				KEY_D:
					# Toggle system dashboard (Ctrl+D)
					var system_dock = panel_mgr.get_panel("system")
					if system_dock:
						if system_dock.is_minimized():
							system_dock.restore()
						else:
							system_dock._minimize_panel()
					get_viewport().set_input_as_handled()
				KEY_F:
					# Toggle face panels (Ctrl+F)
					var kay_face = panel_mgr.get_panel("face_kay")
					var reed_face = panel_mgr.get_panel("face_reed")
					# Toggle both together
					var should_show = (kay_face and kay_face.is_minimized()) or (reed_face and reed_face.is_minimized())
					if kay_face:
						if should_show:
							kay_face.restore()
						else:
							kay_face._minimize_panel()
					if reed_face:
						if should_show:
							reed_face.restore()
						else:
							reed_face._minimize_panel()
					get_viewport().set_input_as_handled()
