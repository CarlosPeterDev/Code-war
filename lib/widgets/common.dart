import 'package:flutter/material.dart';

import '../engine.dart';

/// Section card with a title.
class Panel extends StatelessWidget {
  const Panel({super.key, this.title, required this.child, this.padding = const EdgeInsets.all(14), this.trailing});
  final String? title;
  final Widget child;
  final EdgeInsets padding;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: padding,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (title != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(children: [
                Expanded(child: Text(title!, style: Theme.of(context).textTheme.titleMedium)),
                if (trailing != null) trailing!,
              ]),
            ),
          child,
        ]),
      ),
    );
  }
}

class Stars extends StatelessWidget {
  const Stars(this.n, {super.key, this.size = 18});
  final int n;
  final double size;
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        for (var i = 0; i < 3; i++)
          Icon(i < n ? Icons.star_rounded : Icons.star_outline_rounded,
              size: size, color: i < n ? const Color(0xFFFFC233) : Colors.white38),
      ]);
}

class ErrorBox extends StatelessWidget {
  const ErrorBox(this.message, {super.key});
  final String message;
  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: const Color(0x33FF5252), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.redAccent)),
        child: Text(message, style: const TextStyle(fontSize: 13)),
      );
}

/// Loads a value from the engine and renders it (with loading / error states).
class EngineLoader<T> extends StatefulWidget {
  const EngineLoader({super.key, required this.load, required this.builder});
  final Future<T> Function() load;
  final Widget Function(BuildContext, T) builder;
  @override
  State<EngineLoader<T>> createState() => _EngineLoaderState<T>();
}

class _EngineLoaderState<T> extends State<EngineLoader<T>> {
  late Future<T> _f = widget.load();
  @override
  Widget build(BuildContext context) => FutureBuilder<T>(
        future: _f,
        builder: (context, snap) {
          if (snap.hasError) {
            return Padding(
                padding: const EdgeInsets.all(16),
                child: Column(children: [
                  ErrorBox('${snap.error}'),
                  TextButton(onPressed: () => setState(() => _f = widget.load()), child: const Text('Retry')),
                ]));
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          return widget.builder(context, snap.data as T);
        },
      );
}

void toast(BuildContext context, String text) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(text), duration: const Duration(seconds: 2)));
}

const Map<String, String> kDifficultyNames = {
  'beginner': 'Beginner',
  'easy': 'Easy',
  'normal': 'Normal',
  'hard': 'Hard',
  'expert': 'Expert',
};

String clsTitle(String c) => c.isEmpty ? c : c[0].toUpperCase() + c.substring(1);

IconData clsIcon(String c) {
  switch (c) {
    case 'scout':
      return Icons.visibility;
    case 'miner':
      return Icons.hardware;
    case 'builder':
      return Icons.construction;
    case 'defender':
      return Icons.shield;
    case 'support':
      return Icons.healing;
    case 'transport':
      return Icons.local_shipping;
    default:
      return Icons.bolt;
  }
}

Future<Map<String, dynamic>> loadCatalog() => Engine.I.catalog();

/// Colour for a terrain code (0 grass, 1 sand, 2 rock, 3 water) from a world palette.
Color terrainColor(int code, Map<String, dynamic> palette) {
  String k;
  switch (code) {
    case 1:
      k = 'sand';
      break;
    case 2:
      k = 'rock';
      break;
    case 3:
      k = 'water';
      break;
    default:
      k = 'ground';
  }
  return hex(palette[k] as String);
}

Color hex(String h) => Color(int.parse('FF${h.replaceAll('#', '')}', radix: 16));
