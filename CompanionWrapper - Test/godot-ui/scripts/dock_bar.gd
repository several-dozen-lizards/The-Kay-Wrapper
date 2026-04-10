## DockBar - Bottom taskbar showing minimized/hidden panels.
## Click a dock button to restore its panel.
class_name DockBar
extends PanelContainer

signal panel_restore_requested(panel_id: String)

var _buttons: Dictionary = {}  # panel_id -> Button

@onready var button_container: HBoxContainer = $HBox


func _ready() -> void:
	# Style the dock bar
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.05, 0.08, 0.9)
	style.border_color = Color(0.15, 0.15, 0.25, 1.0)
	style.border_width_top = 1
	style.content_margin_left = 6
	style.content_margin_right = 6
	style.content_margin_top = 3
	style.content_margin_bottom = 3
	add_theme_stylebox_override("panel", style)


func register_panel(panel_id: String, title: String, accent_color: Color) -> void:
	if _buttons.has(panel_id):
		return
	
	var btn = Button.new()
	btn.text = title
	btn.visible = false  # Hidden until panel is minimized
	btn.pressed.connect(func(): _on_dock_button_pressed(panel_id))
	
	# Style per entity
	var btn_style = StyleBoxFlat.new()
	btn_style.bg_color = accent_color * 0.4
	btn_style.border_color = accent_color
	btn_style.border_width_bottom = 2
	btn_style.corner_radius_top_left = 3
	btn_style.corner_radius_top_right = 3
	btn_style.corner_radius_bottom_left = 3
	btn_style.corner_radius_bottom_right = 3
	btn_style.content_margin_left = 12
	btn_style.content_margin_right = 12
	btn_style.content_margin_top = 4
	btn_style.content_margin_bottom = 4
	btn.add_theme_stylebox_override("normal", btn_style)
	
	var hover_style = btn_style.duplicate()
	hover_style.bg_color = accent_color * 0.6
	btn.add_theme_stylebox_override("hover", hover_style)
	
	btn.add_theme_color_override("font_color", Color(0.85, 0.85, 0.9))
	btn.add_theme_font_size_override("font_size", 12)
	
	button_container.add_child(btn)
	_buttons[panel_id] = btn


func show_dock_button(panel_id: String) -> void:
	if _buttons.has(panel_id):
		_buttons[panel_id].visible = true
		_update_visibility()


func hide_dock_button(panel_id: String) -> void:
	if _buttons.has(panel_id):
		_buttons[panel_id].visible = false
		_update_visibility()


func _on_dock_button_pressed(panel_id: String) -> void:
	panel_restore_requested.emit(panel_id)
	hide_dock_button(panel_id)


func _update_visibility() -> void:
	# Show/hide the entire dock bar based on whether any buttons are visible
	var any_visible = false
	for btn in _buttons.values():
		if btn.visible:
			any_visible = true
			break
	visible = any_visible
