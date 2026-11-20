import 'dart:math';

import 'package:flutter/material.dart';

import '../store.dart';
import '../widgets/common.dart';
import 'game_screen.dart';
import 'shell.dart';

/// Reusable match configuration form. If [fixedMode] is null the player chooses the mode.
class MatchSetup extends StatefulWidget {
  const MatchSetup({super.key, required this.catalog, this.fixedMode});
  final Map<String, dynamic> catalog;
  final String? fixedMode;
  @override
  State<MatchSetup> createState() => _MatchSetupState();
}

class _MatchSetupState extends State<MatchSetup> {
  late String mode = widget.fixedMode ?? 'robot_wars';
  String difficulty = 'normal';
  String world = 'ironvale';
  int seed = Random().nextInt(900) + 1;
  bool enemy = false;

  @override
  Widget build(BuildContext context) {
    final modes = widget.catalog['modes'] as Map<String, dynamic>;
    final diffs = widget.catalog['difficulties'] as Map<String, dynamic>;
    final worlds = widget.catalog['worlds'] as Map<String, dynamic>;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (widget.fixedMode == null)
        Panel(
          title: 'Mode',
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            for (final e in modes.entries)
              ChoiceChip(label: Text((e.value as Map)['title'] as String), selected: mode == e.key, onSelected: (_) => setState(() => mode = e.key)),
          ]),
        ),
      Panel(
        title: modes[mode]['title'] as String,
        child: Text(modes[mode]['blurb'] as String),
      ),
      Panel(
        title: 'Difficulty',
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Wrap(spacing: 8, children: [
            for (final k in diffs.keys) ChoiceChip(label: Text(kDifficultyNames[k] ?? k), selected: difficulty == k, onSelected: (_) => setState(() => difficulty = k)),
          ]),
          const SizedBox(height: 6),
          Text('${diffs[difficulty]['blurb']}', style: const TextStyle(fontSize: 13)),
          Text('Start credits ${diffs[difficulty]['start_credits']} - map ${diffs[difficulty]['map_size']}x${diffs[difficulty]['map_size']} - ore x${diffs[difficulty]['ore_mult']} - script budget ${diffs[difficulty]['line_budget']} lines/tick',
              style: const TextStyle(fontSize: 12, color: Colors.white60)),
        ]),
      ),
      Panel(
        title: 'World',
        child: Wrap(spacing: 8, runSpacing: 8, children: [
          for (final e in worlds.entries)
            ChoiceChip(label: Text((e.value as Map)['name'] as String), selected: world == e.key, onSelected: (_) => setState(() => world = e.key)),
        ]),
      ),
      Panel(
        title: 'Seed',
        child: Row(children: [
          Text('$seed', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(width: 12),
          OutlinedButton.icon(onPressed: () => setState(() => seed = Random().nextInt(9000) + 1), icon: const Icon(Icons.casino), label: const Text('Random')),
          IconButton(onPressed: () => setState(() => seed = max(1, seed - 1)), icon: const Icon(Icons.remove)),
          IconButton(onPressed: () => setState(() => seed++), icon: const Icon(Icons.add)),
        ]),
      ),
      if (mode == 'sandbox')
        SwitchListTile(title: const Text('Include an enemy team'), value: enemy, onChanged: (v) => setState(() => enemy = v)),
      const SizedBox(height: 8),
      FilledButton.icon(
        onPressed: () {
          final cfg = <String, dynamic>{
            'mode': mode,
            'difficulty': difficulty,
            'world': world,
            'seed': seed,
            'advanced_mode': !Store.I.guided,
            if (mode == 'sandbox') 'enemy': enemy,
          };
          Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => GameScreen(args: GameArgs(title: '${modes[mode]['title']} - ${kDifficultyNames[difficulty]}', config: cfg))));
        },
        icon: const Icon(Icons.play_arrow),
        label: const Text('Start match'),
      ),
    ]);
  }
}

class PlayScreen extends StatelessWidget {
  const PlayScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return EngineLoader<Map<String, dynamic>>(
      load: loadCatalog,
      builder: (context, cat) => ListenableBuilder(
        listenable: Store.I,
        builder: (context, _) => ListView(padding: const EdgeInsets.all(14), children: [
          screenTitle(context, 'Play', sub: 'Pick a mode, difficulty and world. Your assigned scripts control your robots.'),
          Panel(
            title: 'Saved games',
            child: Column(children: [
              for (var s = 0; s < 3; s++)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.save),
                  title: Text('Slot ${s + 1}'),
                  subtitle: Text(Store.I.saveMeta(s) == null ? 'empty' : '${Store.I.saveMeta(s)!['title']} - tick ${Store.I.saveMeta(s)!['tick']}'),
                  trailing: FilledButton.tonal(
                    onPressed: Store.I.saveBlob(s) == null
                        ? null
                        : () => Navigator.of(context).push(MaterialPageRoute<void>(
                            builder: (_) => GameScreen(args: GameArgs(title: '${Store.I.saveMeta(s)!['title']}', saveBlob: Store.I.saveBlob(s))))),
                    child: const Text('Load'),
                  ),
                ),
            ]),
          ),
          MatchSetup(catalog: cat),
        ]),
      ),
    );
  }
}
