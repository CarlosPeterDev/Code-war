import 'dart:convert';

import 'package:flutter/services.dart';

import 'store.dart';

class EngineException implements Exception {
  EngineException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Thin wrapper over the native bridge to the embedded CPython runtime.
/// Every call maps to a function in the Python module `codewars.bridge` and returns JSON.
class Engine {
  Engine._();
  static final Engine I = Engine._();
  static const MethodChannel _channel = MethodChannel('codewars/py');

  Map<String, dynamic>? _catalog;
  List<dynamic>? _api;

  Future<String> raw(String fn, [List<Object?> args = const []]) async {
    try {
      final r = await _channel.invokeMethod<String>(fn, args);
      return r ?? 'null';
    } on PlatformException catch (e) {
      throw EngineException(e.message ?? e.code);
    } on MissingPluginException {
      throw EngineException('The Python runtime is not available on this platform.');
    }
  }

  Future<dynamic> call(String fn, [List<Object?> args = const []]) async =>
      jsonDecode(await raw(fn, args));

  Future<Map<String, dynamic>> catalog() async {
    _catalog ??= (await call('catalog')) as Map<String, dynamic>;
    return _catalog!;
  }

  Future<List<dynamic>> apiReference() async {
    _api ??= (await call('api_reference')) as List<dynamic>;
    return _api!;
  }

  /// Loads the catalog and installs the starter scripts on first run.
  Future<void> ensureDefaults() async {
    final c = await catalog();
    await Store.I.ensureDefaults(c);
  }

  Map<String, String> get scriptsJsonMap => Store.I.scripts;
  String scriptsJson() => jsonEncode(Store.I.scripts);
  String assignJson() => jsonEncode(Store.I.assign);
}
