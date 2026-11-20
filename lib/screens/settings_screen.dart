import 'package:flutter/material.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/common.dart';
import 'shell.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Store.I,
      builder: (context, _) => ListView(padding: const EdgeInsets.all(14), children: [
        screenTitle(context, 'Settings'),
        Panel(
          title: 'Graphics quality',
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'low', label: Text('Low')),
                ButtonSegment(value: 'medium', label: Text('Medium')),
                ButtonSegment(value: 'high', label: Text('High')),
              ],
              selected: {Store.I.quality},
              onSelectionChanged: (s) => Store.I.setQuality(s.first),
            ),
            const SizedBox(height: 6),
            const Text('Low: no shadows, fewer trees, lower pixel ratio. Medium: soft shadows. High: larger shadow maps and full scenery. '
                'Quality can also be changed during a match.', style: TextStyle(fontSize: 12.5)),
          ]),
        ),
        Panel(
          title: 'Text size',
          child: Slider(value: Store.I.textScale, min: 0.8, max: 1.5, divisions: 7, label: Store.I.textScale.toStringAsFixed(2), onChanged: Store.I.setTextScale),
        ),
        Panel(
          title: 'Coding mode',
          child: SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(Store.I.guided ? 'Guided mode' : 'Advanced mode'),
            subtitle: const Text('Guided shows full parameter help and starter hints in the editor. Advanced shows compact help and runs matches with the advanced editor flag.'),
            value: !Store.I.guided,
            onChanged: (v) => Store.I.setGuided(!v),
          ),
        ),
        Panel(
          title: 'Data',
          child: Wrap(spacing: 10, children: [
            OutlinedButton(
              onPressed: () async {
                final ok = await _confirm(context, 'Reset campaign stars, lessons and puzzles?');
                if (ok) await Store.I.resetProgress();
              },
              child: const Text('Reset progress'),
            ),
            OutlinedButton(
              onPressed: () async {
                final ok = await _confirm(context, 'Replace ALL your scripts with the starter set? Your edits will be lost.');
                if (ok) await Store.I.resetScripts(await Engine.I.catalog());
              },
              child: const Text('Restore starter scripts'),
            ),
          ]),
        ),
        Panel(
          title: 'About',
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            FutureBuilder<dynamic>(
              future: Engine.I.call('version'),
              builder: (c, s) => Text(s.hasData ? 'Engine ${s.data['engine']}, embedded CPython ${s.data['python']}' : 'Python runtime: not available'),
            ),
            const SizedBox(height: 6),
            const Text('Code Wars runs your Python in a restricted in-process sandbox (AST validation, restricted builtins, line / time / memory budgets). '
                'It is not an operating-system boundary. All data stays on this device; the game works offline.'),
            const SizedBox(height: 6),
            Wrap(spacing: 10, children: [
              TextButton(onPressed: () => Nav.go(Nav.learn), child: const Text('Sandbox rules')),
              TextButton(
                onPressed: () => showLicensePage(context: context, applicationName: 'Code Wars'),
                child: const Text('Open-source licences'),
              ),
              TextButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (c) => AlertDialog(
                    title: const Text('Asset credits'),
                    content: const Text(
                        'Robot model: "RobotExpressive" by Tomas Laulhe (Quaternius), modified by Don McCurdy - CC0 1.0.\n\n'
                        'three.js (MIT), Chaquopy / CPython (MIT / PSF), Flutter packages (BSD-3). All other visuals are original and generated at runtime. '
                        'Full list: ASSET_LICENSES.md in the repository.'),
                    actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('OK'))],
                  ),
                ),
                child: const Text('Asset credits'),
              ),
            ]),
          ]),
        ),
      ]),
    );
  }

  Future<bool> _confirm(BuildContext context, String text) async {
    final r = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        content: Text(text),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Confirm')),
        ],
      ),
    );
    return r == true;
  }
}
