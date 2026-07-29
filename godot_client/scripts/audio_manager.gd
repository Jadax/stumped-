class_name AudioManager
extends Node
## Simple audio manager for Stumped! Godot client.
## Plays match sounds (boundary, wicket, crowd, etc.) using Godot's
## built-in audio system.

var _audio_players: Array = []
var _sound_cache: Dictionary = {}
var _volume: float = 1.0
var _muted: bool = false


func _ready() -> void:
	# Create audio players for different sound types
	for i in range(8):
		var player := AudioStreamPlayer.new()
		player.bus = "Master"
		add_child(player)
		_audio_players.append(player)


func set_volume(vol: float) -> void:
	_volume = clampf(vol, 0.0, 1.0)


func set_muted(mute: bool) -> void:
	_muted = mute


func play_sound(sound_name: String, volume_scale: float = 1.0) -> void:
	if _muted:
		return
	var stream := _load_sound(sound_name)
	if stream:
		var player := _get_free_player()
		if player:
			player.stream = stream
			player.volume_db = linear_to_db(_volume * volume_scale)
			player.play()


func _load_sound(sound_name: String) -> AudioStream:
	if _sound_cache.has(sound_name):
		return _sound_cache[sound_name]
	var path := "res://assets/audio/%s.wav" % sound_name
	if ResourceLoader.exists(path):
		var stream = load(path)
		_sound_cache[sound_name] = stream
		return stream
	return null


func _get_free_player() -> AudioStreamPlayer:
	for player in _audio_players:
		if not player.playing:
			return player
	return _audio_players[0] if _audio_players.size() > 0 else null


func play_boundary() -> void:
	play_sound("boundary", 0.8)


func play_six() -> void:
	play_sound("six", 1.0)


func play_wicket() -> void:
	play_sound("wicket", 0.9)


func play_run() -> void:
	play_sound("run", 0.6)


func play_applause() -> void:
	play_sound("applause", 0.5)


func play_ambience() -> void:
	play_sound("ambience", 0.3)
