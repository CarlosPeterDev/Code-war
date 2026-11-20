import 'package:flutter/material.dart';

import '../widgets/common.dart';
import 'shell.dart';

class RobotsScreen extends StatelessWidget {
  const RobotsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return EngineLoader<Map<String, dynamic>>(
      load: loadCatalog,
      builder: (context, cat) {
        final classes = cat['classes'] as Map<String, dynamic>;
        final tech = cat['tech'] as Map<String, dynamic>;
        final structs = cat['structures'] as Map<String, dynamic>;
        return ListView(padding: const EdgeInsets.all(14), children: [
          screenTitle(context, 'Robots', sub: 'Seven classes. What a class can do decides which API calls work for it.'),
          for (final e in classes.entries) _classCard(context, e.key, e.value as Map<String, dynamic>),
          Panel(
            title: 'Research',
            child: Column(children: [
              for (final t in tech.entries)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text('${clsTitle(t.key)} (${(t.value as Map)['levels']} levels)'),
                  subtitle: Text('${(t.value as Map)['desc']}  Costs: ${((t.value as Map)['costs'] as List).join(' / ')}'),
                ),
            ]),
          ),
          Panel(
            title: 'Structures (built by Builder / Advanced robots)',
            child: Column(children: [
              for (final s in structs.entries)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text('${clsTitle(s.key)} - ${(s.value as Map)['cost']} credits, ${(s.value as Map)['hp']} hp'),
                  subtitle: Text('${(s.value as Map)['desc']}'),
                ),
            ]),
          ),
        ]);
      },
    );
  }

  Widget _classCard(BuildContext context, String name, Map<String, dynamic> c) {
    final abilities = <String>[
      if ((c['damage'] as num) > 0) 'attack(target)',
      if ((c['mine'] as num) > 0) 'mine(ore)',
      if ((c['build'] as num) > 0) 'build(kind, x, y)',
      if ((c['repair'] as num) > 0) 'repair(target)',
      if (name == 'support' || name == 'advanced') 'share_energy(target, amount)',
    ];
    return Panel(
      title: clsTitle(name),
      trailing: Icon(clsIcon(name)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${c['desc']}'),
        const SizedBox(height: 6),
        Wrap(spacing: 14, runSpacing: 4, children: [
          for (final k in const ['hp', 'energy', 'speed', 'vision', 'capacity', 'damage', 'range', 'armor', 'cost', 'build_time'])
            Text('$k ${c[k]}', style: const TextStyle(fontSize: 12.5, fontFamily: 'monospace')),
        ]),
        const SizedBox(height: 6),
        Text('Special API: ${abilities.isEmpty ? 'none (movement, scanning, deposit, recharge)' : abilities.map((a) => 'robot.$a').join(', ')}', style: const TextStyle(fontSize: 12.5, color: Color(0xFF8BD3E6))),
        const SizedBox(height: 6),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(onPressed: () => Nav.go(Nav.lab), child: const Text('Assign a script')),
        ),
      ]),
    );
  }
}
