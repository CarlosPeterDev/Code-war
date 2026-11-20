import 'package:flutter/material.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'shell.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, this.bootError});
  final String? bootError;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Store.I,
      builder: (context, _) {
        final totalStars = Store.I.stars.entries.where((e) => e.key.startsWith('campaign:')).fold<int>(0, (a, e) => a + e.value);
        return ListView(padding: const EdgeInsets.all(16), children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              gradient: const LinearGradient(colors: [Color(0xFF0E3A4A), Color(0xFF14202B)]),
              border: Border.all(color: const Color(0x5522D3EE)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('CODE WARS', style: TextStyle(fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: 4)),
              const SizedBox(height: 4),
              const Text('Write real Python. Command a robot army. Win the war.', style: TextStyle(fontSize: 15)),
              const SizedBox(height: 14),
              Wrap(spacing: 10, runSpacing: 10, children: [
                FilledButton.icon(onPressed: () => Nav.go(Nav.campaign), icon: const Icon(Icons.flag), label: const Text('Campaign')),
                FilledButton.tonalIcon(onPressed: () => Nav.go(Nav.wars), icon: const Icon(Icons.bolt), label: const Text('Quick battle')),
                OutlinedButton.icon(onPressed: () => Nav.go(Nav.editor), icon: const Icon(Icons.code), label: const Text('Python editor')),
                OutlinedButton.icon(onPressed: () => Nav.go(Nav.learn), icon: const Icon(Icons.school), label: const Text('Learn Python')),
              ]),
            ]),
          ),
          if (bootError != null) Padding(padding: const EdgeInsets.only(top: 12), child: ErrorBox('Python runtime problem: $bootError')),
          const SizedBox(height: 8),
          Panel(
            title: 'Your progress',
            child: Wrap(spacing: 24, runSpacing: 8, children: [
              _stat(Icons.star, 'Campaign stars', '$totalStars / 39'),
              _stat(Icons.menu_book, 'Lessons done', '${Store.I.lessonsDone.length}'),
              _stat(Icons.extension, 'Puzzles solved', '${Store.I.puzzlesDone.length}'),
              _stat(Icons.description, 'Scripts', '${Store.I.scripts.length}'),
            ]),
          ),
          Panel(
            title: 'How it works',
            child: const Text(
                '1. Open the Python Editor and read or change the starter scripts.\n'
                '2. Assign scripts to robot classes (or groups) in the Robot Lab.\n'
                '3. Start a match. Your update(robot) functions run on every robot, every tick, inside a sandboxed Python 3.12.\n'
                '4. Watch the 3D battlefield, debug in the editor, and read the post-match analysis.'),
          ),
          FutureBuilder<dynamic>(
            future: Engine.I.call('version'),
            builder: (context, s) => Padding(
              padding: const EdgeInsets.all(8),
              child: Text(s.hasData ? 'Engine ${s.data['engine']} - embedded Python ${s.data['python']}' : s.hasError ? 'Python runtime unavailable' : 'Starting Python...',
                  style: Theme.of(context).textTheme.bodySmall),
            ),
          ),
        ]);
      },
    );
  }

  Widget _stat(IconData i, String label, String value) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(i, size: 20, color: const Color(0xFF22D3EE)),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          Text(label, style: const TextStyle(fontSize: 12, color: Colors.white60)),
        ]),
      ]);
}
