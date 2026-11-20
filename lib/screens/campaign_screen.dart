import 'package:flutter/material.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'game_screen.dart';
import 'shell.dart';

class CampaignScreen extends StatelessWidget {
  const CampaignScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return EngineLoader<List<dynamic>>(
      load: () async => (await Engine.I.call('campaign')) as List<dynamic>,
      builder: (context, missions) => ListenableBuilder(
        listenable: Store.I,
        builder: (context, _) {
          return ListView(padding: const EdgeInsets.all(14), children: [
            screenTitle(context, 'Campaign', sub: '13 missions that teach Python while escalating the war. Earn a star to unlock the next one.'),
            for (var i = 0; i < missions.length; i++) _card(context, missions, i),
          ]);
        },
      ),
    );
  }

  Widget _card(BuildContext context, List<dynamic> ms, int i) {
    final m = ms[i] as Map<String, dynamic>;
    final key = 'campaign:${m['id']}';
    final unlocked = i == 0 || Store.I.starsFor('campaign:${(ms[i - 1] as Map)['id']}') > 0;
    final stars = Store.I.starsFor(key);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(unlocked ? Icons.lock_open : Icons.lock, size: 18, color: unlocked ? Colors.greenAccent : Colors.white38),
            const SizedBox(width: 8),
            Expanded(child: Text('${i + 1}. ${m['title']}', style: Theme.of(context).textTheme.titleMedium)),
            Stars(stars),
          ]),
          const SizedBox(height: 4),
          Text('${m['brief']}'),
          const SizedBox(height: 4),
          Text('${m['mode']}  -  ${kDifficultyNames[m['difficulty']]}  -  ${m['world']}', style: const TextStyle(fontSize: 12, color: Colors.white54)),
          Text('Hint: ${m['hint']}', style: const TextStyle(fontSize: 12.5, color: Color(0xFF8BD3E6))),
          const SizedBox(height: 8),
          Row(children: [
            FilledButton(
              onPressed: unlocked
                  ? () => Navigator.of(context).push(MaterialPageRoute<void>(
                      builder: (_) => GameScreen(args: GameArgs(title: '${m['title']}', campaignId: m['id'] as String, starKey: key))))
                  : null,
              child: Text(unlocked ? 'Play' : 'Locked'),
            ),
            const SizedBox(width: 8),
            OutlinedButton(onPressed: () => Nav.go(Nav.editor), child: const Text('Edit scripts')),
          ]),
        ]),
      ),
    );
  }
}
