import 'package:flutter/material.dart';

import '../widgets/common.dart';
import 'play_screen.dart';
import 'shell.dart';

class RobotWarsScreen extends StatelessWidget {
  const RobotWarsScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return EngineLoader<Map<String, dynamic>>(
      load: loadCatalog,
      builder: (context, cat) => ListView(padding: const EdgeInsets.all(14), children: [
        screenTitle(context, 'Robot Wars', sub: 'Strategic warfare against an AI that runs on the same API your robots use.'),
        Panel(
          title: 'Rules of engagement',
          child: const Text(
              '- Both sides start with a small crew and an HQ. Mine ore, build robots, research upgrades.\n'
              '- Fog of war: you only see what your robots see (vision is shared across your team).\n'
              '- Win by destroying the enemy HQ. Lose if yours falls or the clock runs out.\n'
              '- The enemy AI uses one of three styles: rusher, turtle or economist, scaled by difficulty.\n'
              '- Your "commander" script (def commander(base)) queues robots and research; each robot script (def update(robot)) acts every tick.'),
        ),
        MatchSetup(catalog: cat, fixedMode: 'robot_wars'),
        const SizedBox(height: 8),
        OutlinedButton.icon(onPressed: () => Nav.go(Nav.lab), icon: const Icon(Icons.science), label: const Text('Assign scripts in the Robot Lab')),
      ]),
    );
  }
}
