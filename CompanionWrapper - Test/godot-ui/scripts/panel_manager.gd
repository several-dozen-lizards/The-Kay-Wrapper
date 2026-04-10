## PanelManager - Creates, tracks, and manages all floating panels.
## Handles z-ordering, snapping, and panel lifecycle.
class_name PanelManager
extends Control

## Panel registry
var _panels: Dictionary = {}  # panel_id -> DockablePanel
var _z_order: Array[String] = []  # Front panel is last in array

## Panel theme presets (same as ChatPanel but used here for window chrome)
const PANEL_THEMES = {
	"nexus": {
		"bg": Color(0.06, 0.06, 0.09, 0.95),
		"header_bg": Color(0.08, 0.08, 0.14, 1.0),
		"header_text": Color(0.65, 0.65, 0.75),
		"border": Color(0.2, 0.2, 0.35, 1.0),
		"accent": Color(0.4, 0.4, 0.6),
	},
	"kay": {
		"bg": Color(0.08, 0.04, 0.1, 0.95),
		"header_bg": Color(0.12, 0.05, 0.15, 1.0),
		"header_text": Color(0.77, 0.52, 0.75),
		"border": Color(0.35, 0.12, 0.4, 1.0),
		"accent": Color(0.6, 0.2, 0.65),
	},
	"reed": {
		"bg": Color(0.03, 0.08, 0.08, 0.95),
		"header_bg": Color(0.04, 0.1, 0.1, 1.0),
		"header_text": Color(0.31, 0.76, 0.91),
		"border": Color(0.1, 0.3, 0.35, 1.0),
		"accent": Color(0.15, 0.55, 0.6),
	},
	"easel": {
		"bg": Color(0.04, 0.05, 0.08, 0.95),
		"header_bg": Color(0.06, 0.07, 0.12, 1.0),
		"header_text": Color(0.55, 0.7, 0.55),
		"border": Color(0.15, 0.25, 0.2, 1.0),
		"accent": Color(0.3, 0.55, 0.35),
	},
	"system": {
		"bg": Color(0.05, 0.05, 0.07, 0.95),
		"header_bg": Color(0.07, 0.07, 0.1, 1.0),
		"header_text": Color(0.6, 0.65, 0.7),
		"border": Color(0.2, 0.22, 0.28, 1.0),
		"accent": Color(0.4, 0.45, 0.55),
	},
}

@onready var dock_bar: DockBar = $DockBar
@onready var panel_canvas: Control = $PanelCanvas


func _ready() -> void:
	dock_bar.panel_restore_requested.connect(_on_restore_requested)


func create_panel(panel_id: String, title: String, subtitle: String,
		initial_pos: Vector2, initial_size: Vector2,
		content: Control = null) -> DockablePanel:
	
	var panel = DockablePanel.new()
	panel.panel_id = panel_id
	panel.panel_title = title
	panel.panel_subtitle = subtitle
	panel.position = initial_pos
	panel.size = initial_size
	
	# Apply theme
	var theme_key = panel_id.split("_")[0]  # "kay_chat" -> "kay"
	var theme = PANEL_THEMES.get(theme_key, PANEL_THEMES["nexus"])
	panel.theme_data = theme
	
	# Connect signals
	panel.panel_focused.connect(_on_panel_focused)
	panel.panel_closed.connect(_on_panel_closed)
	panel.panel_minimized.connect(_on_panel_minimized)
	
	# Add content if provided
	if content:
		panel.set_content(content)
	
	# Register
	_panels[panel_id] = panel
	_z_order.append(panel_id)
	panel_canvas.add_child(panel)
	
	# Force absolute pixel positioning — prevents anchor layout from overriding drag
	panel.set_anchors_preset(Control.PRESET_TOP_LEFT)
	panel.anchor_right = 0.0
	panel.anchor_bottom = 0.0
	panel.position = initial_pos
	panel.size = initial_size
	
	# Register in dock bar
	var accent = theme.get("accent", Color(0.4, 0.4, 0.6))
	dock_bar.register_panel(panel_id, title, accent)
	
	return panel


func get_panel(panel_id: String) -> DockablePanel:
	return _panels.get(panel_id)


func get_content(panel_id: String) -> Control:
	var panel = get_panel(panel_id)
	if panel and panel.get_child_count() > 0:
		return panel.get_child(0)
	return null


func _on_panel_focused(panel_id: String) -> void:
	# Move panel to front of z-order
	_z_order.erase(panel_id)
	_z_order.append(panel_id)
	_apply_z_order()


func _on_panel_closed(panel_id: String) -> void:
	dock_bar.show_dock_button(panel_id)


func _on_panel_minimized(panel_id: String) -> void:
	dock_bar.show_dock_button(panel_id)


func _on_restore_requested(panel_id: String) -> void:
	if _panels.has(panel_id):
		_panels[panel_id].restore()
		_on_panel_focused(panel_id)


func _apply_z_order() -> void:
	for i in range(_z_order.size()):
		var pid = _z_order[i]
		if _panels.has(pid):
			panel_canvas.move_child(_panels[pid], i)


## Snap helpers for future use
func snap_panel_left(panel_id: String) -> void:
	var panel = get_panel(panel_id)
	if panel:
		panel.position = Vector2(0, 0)
		panel.size = Vector2(size.x * 0.5, size.y - dock_bar.size.y)


func snap_panel_right(panel_id: String) -> void:
	var panel = get_panel(panel_id)
	if panel:
		panel.position = Vector2(size.x * 0.5, 0)
		panel.size = Vector2(size.x * 0.5, size.y - dock_bar.size.y)


func snap_panel_full(panel_id: String) -> void:
	var panel = get_panel(panel_id)
	if panel:
		panel.position = Vector2(0, 0)
		panel.size = Vector2(size.x, size.y - dock_bar.size.y)


## Arrange panels in a default layout
func arrange_default() -> void:
	var usable_h = size.y - 36  # Dock bar height
	var half_w = size.x * 0.5
	
	# Nexus starts minimized — if visible, give it left portion
	var nexus_visible = _panels.has("nexus") and not _panels["nexus"]._is_minimized
	var chat_offset_x = 0.0
	var chat_width = size.x
	
	if nexus_visible:
		var nexus_w = size.x * 0.33
		_panels["nexus"].position = Vector2(2, 2)
		_panels["nexus"].size = Vector2(nexus_w - 2, usable_h - 2)
		_panels["nexus"]._reposition_content()
		_panels["nexus"].queue_redraw()
		chat_offset_x = nexus_w + 2
		chat_width = size.x - nexus_w - 4
	
	# Kay: left half of available space
	if _panels.has("kay"):
		_panels["kay"].position = Vector2(chat_offset_x + 2, 2)
		_panels["kay"].size = Vector2(chat_width * 0.5 - 4, usable_h - 2)
		_panels["kay"]._reposition_content()
		_panels["kay"].queue_redraw()
	
	# Reed: right half of available space
	if _panels.has("reed"):
		_panels["reed"].position = Vector2(chat_offset_x + chat_width * 0.5 + 2, 2)
		_panels["reed"].size = Vector2(chat_width * 0.5 - 4, usable_h - 2)
		_panels["reed"]._reposition_content()
		_panels["reed"].queue_redraw()
