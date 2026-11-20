import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Local persistence: scripts, assignments, settings, progress and save games. Everything is offline.
class Store extends ChangeNotifier {
  Store._();
  static final Store I = Store._();

  SharedPreferences? _p;
  Map<String, String> scripts = {};
  Map<String, String> assign = {};
  String quality = 'medium';
  double textScale = 1.0;
  bool guided = true;
  Map<String, int> stars = {};
  Set<String> lessonsDone = {};
  Set<String> puzzlesDone = {};
  String openScript = 'main.py';

  Future<void> init() async {
    final p = await SharedPreferences.getInstance();
    _p = p;
    scripts = _readMap(p.getString('scripts')).map((k, v) => MapEntry(k, v.toString()));
    assign = _readMap(p.getString('assign')).map((k, v) => MapEntry(k, v.toString()));
    quality = p.getString('quality') ?? 'medium';
    textScale = p.getDouble('textScale') ?? 1.0;
    guided = p.getBool('guided') ?? true;
    stars = _readMap(p.getString('stars')).map((k, v) => MapEntry(k, (v as num).toInt()));
    lessonsDone = (p.getStringList('lessonsDone') ?? <String>[]).toSet();
    puzzlesDone = (p.getStringList('puzzlesDone') ?? <String>[]).toSet();
    openScript = p.getString('openScript') ?? 'main.py';
  }

  Map<String, dynamic> _readMap(String? s) {
    if (s == null || s.isEmpty) return {};
    try {
      final v = jsonDecode(s);
      return v is Map<String, dynamic> ? v : {};
    } catch (_) {
      return {};
    }
  }

  /// First run: install the starter army (all templates) and sensible assignments.
  Future<void> ensureDefaults(Map<String, dynamic> catalog) async {
    if (scripts.isNotEmpty) return;
    for (final t in (catalog['templates'] as List<dynamic>)) {
      scripts[t['name'] as String] = t['source'] as String;
    }
    final sa = catalog['starter_assign'] as Map<String, dynamic>;
    assign = sa.map((k, v) => MapEntry(k, v.toString()));
    openScript = 'miner.py';
    await saveScripts();
  }

  Future<void> saveScripts() async {
    await _p?.setString('scripts', jsonEncode(scripts));
    await _p?.setString('assign', jsonEncode(assign));
    await _p?.setString('openScript', openScript);
    notifyListeners();
  }

  Future<void> setQuality(String q) async {
    quality = q;
    await _p?.setString('quality', q);
    notifyListeners();
  }

  Future<void> setTextScale(double v) async {
    textScale = v;
    await _p?.setDouble('textScale', v);
    notifyListeners();
  }

  Future<void> setGuided(bool v) async {
    guided = v;
    await _p?.setBool('guided', v);
    notifyListeners();
  }

  int starsFor(String key) => stars[key] ?? 0;

  Future<void> recordStars(String key, int n) async {
    if (n > (stars[key] ?? 0)) {
      stars[key] = n;
      await _p?.setString('stars', jsonEncode(stars));
      notifyListeners();
    }
  }

  Future<void> markLesson(String id) async {
    lessonsDone.add(id);
    await _p?.setStringList('lessonsDone', lessonsDone.toList());
    notifyListeners();
  }

  Future<void> markPuzzle(String id) async {
    puzzlesDone.add(id);
    await _p?.setStringList('puzzlesDone', puzzlesDone.toList());
    notifyListeners();
  }

  // ---- save games (3 slots) -------------------------------------------------
  Map<String, dynamic>? saveMeta(int slot) {
    final s = _p?.getString('save_meta_$slot');
    if (s == null) return null;
    try {
      return jsonDecode(s) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  String? saveBlob(int slot) => _p?.getString('save_blob_$slot');

  Future<void> writeSave(int slot, String blob, Map<String, dynamic> meta) async {
    await _p?.setString('save_blob_$slot', blob);
    await _p?.setString('save_meta_$slot', jsonEncode(meta));
    notifyListeners();
  }

  Future<void> resetProgress() async {
    stars = {};
    lessonsDone = {};
    puzzlesDone = {};
    await _p?.remove('stars');
    await _p?.remove('lessonsDone');
    await _p?.remove('puzzlesDone');
    notifyListeners();
  }

  Future<void> resetScripts(Map<String, dynamic> catalog) async {
    scripts = {};
    await ensureDefaults(catalog);
  }
}
