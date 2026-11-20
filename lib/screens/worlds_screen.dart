import 'package:flutter/material.dart';

import '../engine.dart';
import '../widgets/common.dart';
import 'shell.dart';

/// Lists the worlds with a small 2D top-down map thumbnail (a UI preview only; the match itself is rendered in 3D).
class WorldsScreen extends StatelessWidget {
  const WorldsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return EngineLoader<Map<String, dynamic>>(
      load: loadCatalog,
      builder: (context, cat) {
        final worlds = cat['worlds'] as Map<String, dynamic>;
        return ListView(padding: const EdgeInsets.all(14), children: [
          screenTitle(context, 'Worlds', sub: 'Five procedural worlds. Same seed = same map, always.'),
          for (final e in worlds.entries) _WorldCard(id: e.key, w: e.value as Map<String, dynamic>),
        ]);
      },
    );
  }
}

class _WorldCard extends StatefulWidget {
  const _WorldCard({required this.id, required this.w});
  final String id;
  final Map<String, dynamic> w;
  @override
  State<_WorldCard> createState() => _WorldCardState();
}

class _WorldCardState extends State<_WorldCard> {
  int seed = 1;
  late Future<dynamic> _f = Engine.I.call('world_preview', [widget.id, 36, seed]);

  @override
  Widget build(BuildContext context) {
    final pal = widget.w['palette'] as Map<String, dynamic>;
    return Panel(
      title: widget.w['name'] as String,
      trailing: IconButton(
        icon: const Icon(Icons.shuffle),
        tooltip: 'New preview seed',
        onPressed: () => setState(() {
          seed++;
          _f = Engine.I.call('world_preview', [widget.id, 36, seed]);
        }),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
          width: 140,
          height: 140,
          child: FutureBuilder<dynamic>(
            future: _f,
            builder: (context, s) {
              if (!s.hasData) return const Center(child: CircularProgressIndicator());
              return CustomPaint(painter: _MapPainter(s.data as Map<String, dynamic>, pal));
            },
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(widget.w['blurb'] as String),
            const SizedBox(height: 8),
            Text('Preview seed $seed (2D thumbnail)', style: const TextStyle(fontSize: 12, color: Colors.white54)),
            const SizedBox(height: 8),
            FilledButton.tonal(onPressed: () => Nav.go(Nav.play), child: const Text('Play here')),
          ]),
        ),
      ]),
    );
  }
}

class _MapPainter extends CustomPainter {
  _MapPainter(this.d, this.pal);
  final Map<String, dynamic> d;
  final Map<String, dynamic> pal;

  @override
  void paint(Canvas canvas, Size size) {
    final grid = d['grid'] as List<dynamic>;
    final n = grid.length;
    final cell = size.width / n;
    final p = Paint();
    for (var y = 0; y < n; y++) {
      final row = grid[y] as List<dynamic>;
      for (var x = 0; x < n; x++) {
        p.color = terrainColor((row[x] as num).toInt(), pal);
        canvas.drawRect(Rect.fromLTWH(x * cell, y * cell, cell + 0.5, cell + 0.5), p);
      }
    }
    p.color = const Color(0xFFFFC233);
    for (final o in (d['ore'] as List<dynamic>)) {
      canvas.drawCircle(Offset(((o[0] as num) + 0.5) * cell, ((o[1] as num) + 0.5) * cell), cell * 0.6, p);
    }
    final hq = d['hq'] as List<dynamic>;
    for (var i = 0; i < hq.length; i++) {
      p.color = i == 0 ? Colors.cyanAccent : Colors.redAccent;
      canvas.drawRect(Rect.fromLTWH(((hq[i][0] as num) - 1) * cell, ((hq[i][1] as num) - 1) * cell, cell * 3, cell * 3), p);
    }
  }

  @override
  bool shouldRepaint(covariant _MapPainter old) => old.d != d;
}
