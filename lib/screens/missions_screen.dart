import 'dart:math';

import 'package:flutter/material.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'game_screen.dart';
import 'shell.dart';

/// Quick missions: every mode at every difficulty, with objectives listed from the engine.
class MissionsScreen extends StatelessWidget {
  const MissionsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return EngineLoader<Map<String, dynamic>>(
      load: loadCatalog,
      builder: (context, cat) {
        final modes = cat['modes'] as Map<String, dynamic>;
        final diffs = cat['difficulties'] as Map<String, dynamic>;
        return ListenableBuilder(
          listenable: Store.I,
          builder: (context, _) => ListView(padding: const EdgeInsets.all(14), children: [
            screenTitle(context, 'Missions', sub: 'Quick missions with fixed objectives. Stars are saved per mode and difficulty.'),
            for (final m in modes.entries.where((e) => e.key != 'sandbox'))
              Panel(
                title: (m.value as Map)['title'] as String,
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text((m.value as Map)['blurb'] as String),
                  const SizedBox(height: 8),
                  for (final d in diffs.keys)
                    _Row(mode: m.key, title: (m.value as Map)['title'] as String, diff: d),
                ]),
              ),
          ]),
        );
      },
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.mode, required this.title, required this.diff});
  final String mode, title, diff;
  @override
  Widget build(BuildContext context) {
    final key = 'mission:$mode:$diff';
    return FutureBuilder<dynamic>(
      future: Engine.I.call('mission_objectives', [mode, diff]),
      builder: (context, s) {
        final goals = s.hasData ? (s.data as List<dynamic>).join('; ') : '...';
        return ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(kDifficultyNames[diff] ?? diff),
          subtitle: Text(goals),
          leading: Stars(Store.I.starsFor(key), size: 16),
          trailing: FilledButton.tonal(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => GameScreen(
                args: GameArgs(
                  title: '$title - ${kDifficultyNames[diff]}',
                  starKey: key,
                  config: {'mode': mode, 'difficulty': diff, 'world': 'ironvale', 'seed': Random().nextInt(500) + 1, 'advanced_mode': !Store.I.guided},
                ),
              ),
            )),
            child: const Text('Play'),
          ),
        );
      },
    );
  }
}
