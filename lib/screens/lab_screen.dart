import 'package:flutter/material.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'game_screen.dart';
import 'shell.dart';

/// Robot Lab: assign scripts to classes, groups and the base commander; launch a test arena.
class LabScreen extends StatefulWidget {
  const LabScreen({super.key});
  @override
  State<LabScreen> createState() => _LabScreenState();
}

class _LabScreenState extends State<LabScreen> {
  final TextEditingController _group = TextEditingController();

  @override
  void dispose() {
    _group.dispose();
    super.dispose();
  }

  Widget _picker(String key, String label, List<String> scripts) {
    final cur = Store.I.assign[key];
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      title: Text(label),
      trailing: SizedBox(
        width: 190,
        child: DropdownButton<String>(
          isExpanded: true,
          value: scripts.contains(cur) ? cur : '',
          items: [
            const DropdownMenuItem(value: '', child: Text('(none)')),
            for (final s in scripts) DropdownMenuItem(value: s, child: Text(s, overflow: TextOverflow.ellipsis)),
          ],
          onChanged: (v) async {
            if (v == null || v.isEmpty) {
              Store.I.assign.remove(key);
            } else {
              Store.I.assign[key] = v;
            }
            await Store.I.saveScripts();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return EngineLoader<Map<String, dynamic>>(
      load: loadCatalog,
      builder: (context, cat) => ListenableBuilder(
        listenable: Store.I,
        builder: (context, _) {
          final scripts = Store.I.scripts.keys.toList()..sort();
          final classes = (cat['classes'] as Map<String, dynamic>).keys.toList();
          final groups = Store.I.assign.keys.where((k) => k.startsWith('group:')).toList()..sort();
          final robotKeys = Store.I.assign.keys.where((k) => k.startsWith('robot:')).toList();
          return ListView(padding: const EdgeInsets.all(14), children: [
            screenTitle(context, 'Robot Lab', sub: 'Decide which script drives which robots, then test it in an arena.'),
            Panel(
              title: 'Base commander',
              child: Column(children: [
                _picker('commander', 'Commander script (def commander(base))', scripts),
                _picker('default', 'Default script for unassigned robots', scripts),
              ]),
            ),
            Panel(
              title: 'Scripts by robot class',
              child: Column(children: [for (final c in classes) _picker('class:$c', clsTitle(c), scripts)]),
            ),
            Panel(
              title: 'Groups',
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Robots can join a group with robot.set_group("alpha") in code, or from a selected robot during a match. A group script overrides the class script.',
                    style: TextStyle(fontSize: 12.5)),
                for (final g in groups) _picker(g, 'Group ${g.substring(6)}', scripts),
                Row(children: [
                  Expanded(child: TextField(controller: _group, decoration: const InputDecoration(hintText: 'New group name', isDense: true))),
                  TextButton(
                    onPressed: () async {
                      final n = _group.text.trim().replaceAll(RegExp(r'[^A-Za-z0-9_]'), '');
                      if (n.isEmpty || scripts.isEmpty) return;
                      Store.I.assign['group:$n'] = scripts.first;
                      _group.clear();
                      await Store.I.saveScripts();
                    },
                    child: const Text('Add group'),
                  ),
                ]),
              ]),
            ),
            if (robotKeys.isNotEmpty)
              Panel(
                title: 'Single-robot overrides',
                child: Column(children: [
                  for (final k in robotKeys)
                    ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: Text('Robot ${k.substring(6)}  ->  ${Store.I.assign[k]}'),
                      trailing: IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () async {
                          Store.I.assign.remove(k);
                          await Store.I.saveScripts();
                        },
                      ),
                    ),
                ]),
              ),
            Panel(
              title: 'Test arena',
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('A sandbox match with 5 of your robots, optional enemy, 2000 credits and no time limit.', style: TextStyle(fontSize: 12.5)),
                const SizedBox(height: 8),
                Wrap(spacing: 8, children: [
                  FilledButton.icon(
                    onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => const GameScreen(args: GameArgs(title: 'Test arena', config: {'mode': 'sandbox', 'difficulty': 'normal', 'world': 'ironvale', 'seed': 5, 'enemy': false})))),
                    icon: const Icon(Icons.science),
                    label: const Text('Peaceful arena'),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => const GameScreen(args: GameArgs(title: 'Combat arena', config: {'mode': 'sandbox', 'difficulty': 'normal', 'world': 'ironvale', 'seed': 5, 'enemy': true})))),
                    icon: const Icon(Icons.local_fire_department),
                    label: const Text('Combat arena'),
                  ),
                ]),
              ]),
            ),
            Panel(
              title: 'Starter army',
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('You have ${scripts.length} scripts. Restoring installs the 10 built-in templates and the default assignments (your own scripts are kept).', style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: () async {
                    for (final t in (cat['templates'] as List<dynamic>)) {
                      Store.I.scripts.putIfAbsent(t['name'] as String, () => t['source'] as String);
                    }
                    Store.I.assign = (cat['starter_assign'] as Map<String, dynamic>).map((k, v) => MapEntry(k, v.toString()));
                    await Store.I.saveScripts();
                    if (context.mounted) toast(context, 'Starter assignments restored');
                  },
                  child: const Text('Restore starter assignments'),
                ),
                TextButton(onPressed: () => Nav.go(Nav.editor), child: const Text('Open the editor')),
              ]),
            ),
          ]);
        },
      ),
    );
  }
}
