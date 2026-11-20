import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/code_editor.dart';
import '../widgets/common.dart';
import 'game_screen.dart';

class EditorScreen extends StatefulWidget {
  const EditorScreen({super.key});
  @override
  State<EditorScreen> createState() => _EditorScreenState();
}

class _EditorScreenState extends State<EditorScreen> {
  final PyController _c = PyController();
  final GlobalKey<CodeEditorState> _ek = GlobalKey<CodeEditorState>();
  final Map<String, Set<int>> _breaks = {};
  List<dynamic> _api = [];
  List<dynamic> _problems = [];
  Map<String, dynamic>? _catalog;
  String _name = 'main.py';
  Timer? _debounce;
  Timer? _runTimer;
  bool _ready = false;
  bool _dirty = false;
  bool _showSearch = false;
  bool _showPanel = false;
  bool _running = false;
  int _tab = 1;
  final TextEditingController _find = TextEditingController();
  final TextEditingController _repl = TextEditingController();
  Map<String, dynamic> _snap = {};
  String? _runError;
  int? _dbgRobot;
  Map<String, dynamic>? _dbg;
  Map<String, dynamic>? _info;
  final List<String> _console = [];

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      _catalog = await Engine.I.catalog();
      _api = await Engine.I.apiReference();
    } catch (e) {
      _runError = '$e';
    }
    final s = Store.I.scripts;
    _name = s.containsKey(Store.I.openScript) ? Store.I.openScript : (s.keys.isEmpty ? 'main.py' : s.keys.first);
    if (!s.containsKey(_name)) s[_name] = 'def update(robot):\n    pass\n';
    _load(_name);
    if (mounted) setState(() => _ready = true);
  }

  void _load(String name) {
    _name = name;
    Store.I.openScript = name;
    _c.removeListener(_onText);
    _c.value = TextEditingValue(text: Store.I.scripts[name] ?? '');
    _c.addListener(_onText);
    _dirty = false;
    _validate();
  }

  void _onText() {
    _dirty = true;
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 500), () {
      _commit();
      _validate();
    });
  }

  Future<void> _commit() async {
    Store.I.scripts[_name] = _c.text;
    _dirty = false;
    await Store.I.saveScripts();
  }

  Future<void> _validate() async {
    try {
      final r = await Engine.I.call('validate', [_c.text, _name]);
      _problems = r as List<dynamic>;
      _c.errorLines = _problems.where((p) => (p as Map)['severity'] == 'error').map((p) => ((p as Map)['line'] as num).toInt()).toSet();
      if (mounted) setState(() {});
    } catch (_) {}
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _runTimer?.cancel();
    if (_dirty) {
      Store.I.scripts[_name] = _c.text;
      Store.I.saveScripts();
    }
    _c.dispose();
    _find.dispose();
    _repl.dispose();
    super.dispose();
  }

  // -------------------------------------------------------------- files
  Future<String?> _ask(String title, String initial) async {
    final t = TextEditingController(text: initial);
    final r = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(controller: t, autofocus: true, decoration: const InputDecoration(hintText: 'name.py')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, t.text.trim()), child: const Text('OK')),
        ],
      ),
    );
    if (r == null || r.isEmpty) return null;
    return r.endsWith('.py') ? r : '$r.py';
  }

  Future<void> _newFile({String? source}) async {
    final n = await _ask('New script', 'script${Store.I.scripts.length + 1}.py');
    if (n == null) return;
    if (Store.I.scripts.containsKey(n)) {
      if (mounted) toast(context, 'A script named $n already exists');
      return;
    }
    await _commit();
    Store.I.scripts[n] = source ?? 'def update(robot):\n    pass\n';
    await Store.I.saveScripts();
    _load(n);
    setState(() {});
  }

  Future<void> _rename() async {
    final n = await _ask('Rename script', _name);
    if (n == null || n == _name) return;
    if (Store.I.scripts.containsKey(n)) {
      if (mounted) toast(context, 'A script named $n already exists');
      return;
    }
    Store.I.scripts[n] = _c.text;
    Store.I.scripts.remove(_name);
    for (final k in Store.I.assign.keys.toList()) {
      if (Store.I.assign[k] == _name) Store.I.assign[k] = n;
    }
    await Store.I.saveScripts();
    _load(n);
    setState(() {});
  }

  Future<void> _delete() async {
    if (Store.I.scripts.length <= 1) {
      toast(context, 'Keep at least one script');
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Delete $_name?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok != true) return;
    Store.I.scripts.remove(_name);
    Store.I.assign.removeWhere((k, v) => v == _name);
    await Store.I.saveScripts();
    _load(Store.I.scripts.keys.first);
    setState(() {});
  }

  void _filesSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.7,
          builder: (ctx, sc) => ListView(controller: sc, children: [
            const ListTile(title: Text('Scripts', style: TextStyle(fontWeight: FontWeight.w800))),
            for (final n in (Store.I.scripts.keys.toList()..sort()))
              ListTile(
                dense: true,
                leading: Icon(n == _name ? Icons.edit_document : Icons.description_outlined),
                title: Text(n),
                subtitle: Text(_usedBy(n)),
                selected: n == _name,
                onTap: () async {
                  Navigator.pop(ctx);
                  await _commit();
                  _load(n);
                  setState(() {});
                },
              ),
            const Divider(),
            ListTile(leading: const Icon(Icons.add), title: const Text('New empty script'), onTap: () { Navigator.pop(ctx); _newFile(); }),
            ListTile(leading: const Icon(Icons.copy), title: const Text('Duplicate current script'), onTap: () { Navigator.pop(ctx); _newFile(source: _c.text); }),
            ListTile(leading: const Icon(Icons.drive_file_rename_outline), title: const Text('Rename current script'), onTap: () { Navigator.pop(ctx); _rename(); }),
            ListTile(leading: const Icon(Icons.delete_outline), title: const Text('Delete current script'), onTap: () { Navigator.pop(ctx); _delete(); }),
            const Divider(),
            const ListTile(title: Text('Templates', style: TextStyle(fontWeight: FontWeight.w800))),
            for (final t in ((_catalog?['templates'] as List<dynamic>?) ?? []))
              ListTile(
                dense: true,
                leading: const Icon(Icons.auto_awesome),
                title: Text('${(t as Map)['title']}'),
                subtitle: Text('${t['name']}'),
                onTap: () {
                  Navigator.pop(ctx);
                  _newFile(source: t['source'] as String);
                },
              ),
          ]),
        ),
      ),
    );
  }

  String _usedBy(String n) {
    final u = Store.I.assign.entries.where((e) => e.value == n).map((e) => e.key).toList();
    return u.isEmpty ? 'not assigned' : 'used by ${u.join(', ')}';
  }

  // -------------------------------------------------------------- assign
  void _assignDialog() {
    final cls = ((_catalog?['classes'] as Map<String, dynamic>?) ?? {}).keys.toList();
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Assign $_name to...'),
        content: SizedBox(
          width: 360,
          child: ListView(shrinkWrap: true, children: [
            for (final c in cls)
              CheckboxListTile(
                dense: true,
                title: Text('All ${clsTitle(c)} robots'),
                value: Store.I.assign['class:$c'] == _name,
                onChanged: (v) async {
                  if (v == true) {
                    Store.I.assign['class:$c'] = _name;
                  } else if (Store.I.assign['class:$c'] == _name) {
                    Store.I.assign.remove('class:$c');
                  }
                  await Store.I.saveScripts();
                  if (ctx.mounted) {
                    Navigator.pop(ctx);
                    _assignDialog();
                  }
                },
              ),
            CheckboxListTile(
              dense: true,
              title: const Text('Base commander (def commander(base))'),
              value: Store.I.assign['commander'] == _name,
              onChanged: (v) async {
                if (v == true) {
                  Store.I.assign['commander'] = _name;
                } else if (Store.I.assign['commander'] == _name) {
                  Store.I.assign.remove('commander');
                }
                await Store.I.saveScripts();
                if (ctx.mounted) {
                  Navigator.pop(ctx);
                  _assignDialog();
                }
              },
            ),
            CheckboxListTile(
              dense: true,
              title: const Text('Default for everything else'),
              value: Store.I.assign['default'] == _name,
              onChanged: (v) async {
                if (v == true) {
                  Store.I.assign['default'] = _name;
                } else if (Store.I.assign['default'] == _name) {
                  Store.I.assign.remove('default');
                }
                await Store.I.saveScripts();
                if (ctx.mounted) {
                  Navigator.pop(ctx);
                  _assignDialog();
                }
              },
            ),
            const Padding(
              padding: EdgeInsets.all(8),
              child: Text('Priority for a robot: its own script > its group script > its class script > default. Groups and single robots are assigned in the Robot Lab or from a selected robot in a match.',
                  style: TextStyle(fontSize: 12)),
            ),
          ]),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Done'))],
      ),
    );
  }

  // -------------------------------------------------------------- running (headless test arena)
  Map<String, String> _testAssign() {
    final a = Map<String, String>.from(Store.I.assign);
    final src = _c.text;
    if (src.contains('def update(')) {
      a.removeWhere((k, v) => k.startsWith('class:') || k == 'default');
      a['default'] = _name;
    }
    if (src.contains('def commander(')) a['commander'] = _name;
    return a;
  }

  Future<void> _reset() async {
    _runTimer?.cancel();
    _running = false;
    await _commit();
    try {
      final r = await Engine.I.call('new_game', [
        jsonEncode({'mode': 'sandbox', 'difficulty': 'normal', 'world': 'ironvale', 'seed': 7, 'advanced_mode': !Store.I.guided, 'enemy': true}),
        jsonEncode(Store.I.scripts),
        jsonEncode(_testAssign()),
      ]) as Map<String, dynamic>;
      _snap = r['snapshot'] as Map<String, dynamic>;
      _console
        ..clear()
        ..add('Test arena ready (sandbox, enemy on, seed 7). Press Run.');
      final pr = r['problems'];
      if (pr is Map && pr.isNotEmpty) _console.add('Script problems: $pr');
      _runError = null;
      _dbg = null;
      _info = null;
    } catch (e) {
      _runError = '$e';
    }
    if (mounted) setState(() {});
  }

  Future<void> _run() async {
    if (_snap.isEmpty) await _reset();
    if (_runError != null) return;
    setState(() {
      _running = true;
      _showPanel = true;
      _tab = 1;
    });
    _runTimer?.cancel();
    _runTimer = Timer.periodic(const Duration(milliseconds: 300), (t) async {
      if (!_running) return;
      try {
        await Engine.I.call('set_scripts', [jsonEncode(Store.I.scripts), jsonEncode(_testAssign())]);
        final s = await Engine.I.call('step', [4]) as Map<String, dynamic>;
        _snap = s;
        for (final l in (s['logs'] as List<dynamic>? ?? [])) {
          final lm = l as Map<String, dynamic>;
          final line = 't${lm['tick']} ${lm['robot'] != null ? '#${lm['robot']} ' : ''}${lm['text']}';
          if (!_console.contains(line)) _console.add(line);
        }
        if (_console.length > 300) _console.removeRange(0, _console.length - 300);
        if (_dbgRobot != null) {
          try {
            _info = await Engine.I.call('robot_info', [_dbgRobot]) as Map<String, dynamic>?;
          } catch (_) {}
        }
        if (mounted) setState(() {});
      } catch (e) {
        _running = false;
        _runError = '$e';
        if (mounted) setState(() {});
      }
    });
  }

  void _stop() {
    _runTimer?.cancel();
    setState(() => _running = false);
  }

  Future<void> _debugTick() async {
    final id = _dbgRobot;
    if (id == null) {
      toast(context, 'Pick a robot first');
      return;
    }
    try {
      final d = await Engine.I.call('debug_robot', [id, jsonEncode((_breaks[_name] ?? <int>{}).toList())]);
      setState(() => _dbg = d as Map<String, dynamic>);
    } catch (e) {
      toast(context, '$e');
    }
  }

  // -------------------------------------------------------------- build
  @override
  Widget build(BuildContext context) {
    if (!_ready) return const Center(child: CircularProgressIndicator());
    final ed = _ek.currentState;
    final bps = _breaks.putIfAbsent(_name, () => <int>{});
    return Column(children: [
      _toolbar(ed),
      if (_showSearch) _searchBar(ed),
      Expanded(
        flex: 5,
        child: CodeEditor(
          key: _ek,
          controller: _c,
          api: _api,
          guided: Store.I.guided,
          breakpoints: bps,
          onToggleBreakpoint: (l) => setState(() => bps.contains(l) ? bps.remove(l) : bps.add(l)),
          onChanged: () => setState(() {}),
        ),
      ),
      if (_showPanel) Expanded(flex: 4, child: _runPanel()) else _problemStrip(),
    ]);
  }

  Widget _toolbar(CodeEditorState? ed) {
    return Material(
      color: Theme.of(context).colorScheme.surfaceContainer,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          TextButton.icon(onPressed: _filesSheet, icon: const Icon(Icons.folder_open, size: 18), label: Text(_name + (_dirty ? ' *' : ''))),
          IconButton(icon: const Icon(Icons.undo), tooltip: 'Undo', onPressed: (ed?.canUndo ?? false) ? ed!.undo : null),
          IconButton(icon: const Icon(Icons.redo), tooltip: 'Redo', onPressed: (ed?.canRedo ?? false) ? ed!.redo : null),
          IconButton(icon: Icon(Icons.search, color: _showSearch ? const Color(0xFF22D3EE) : null), tooltip: 'Search / replace', onPressed: () => setState(() => _showSearch = !_showSearch)),
          IconButton(
              icon: const Icon(Icons.save),
              tooltip: 'Save',
              onPressed: () async {
                await _commit();
                if (mounted) toast(context, 'Saved $_name');
              }),
          IconButton(icon: const Icon(Icons.copy_all), tooltip: 'Copy all', onPressed: () async { await ed?.copyAll(); if (mounted) toast(context, 'Copied'); }),
          IconButton(
              icon: const Icon(Icons.content_paste),
              tooltip: 'Paste',
              onPressed: () async {
                final d = await Clipboard.getData('text/plain');
                if (d?.text != null) ed?.insertAtCursor(d!.text!);
              }),
          IconButton(icon: const Icon(Icons.link), tooltip: 'Assign to robots', onPressed: _assignDialog),
          const SizedBox(width: 6),
          if (!_running)
            FilledButton.icon(onPressed: _run, icon: const Icon(Icons.play_arrow), label: const Text('Run'))
          else
            FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Colors.redAccent), onPressed: _stop, icon: const Icon(Icons.stop), label: const Text('Stop')),
          IconButton(icon: const Icon(Icons.restart_alt), tooltip: 'Reset test arena', onPressed: _reset),
          IconButton(
              icon: Icon(Icons.terminal, color: _showPanel ? const Color(0xFF22D3EE) : null),
              tooltip: 'Console / debugger',
              onPressed: () => setState(() => _showPanel = !_showPanel)),
          IconButton(
            icon: const Icon(Icons.view_in_ar),
            tooltip: 'Test in 3D',
            onPressed: () async {
              await _commit();
              if (!mounted) return;
              Navigator.of(context).push(MaterialPageRoute<void>(
                  builder: (_) => GameScreen(
                      args: GameArgs(
                          title: 'Script test: $_name',
                          assignOverride: _testAssign(),
                          config: {'mode': 'sandbox', 'difficulty': 'normal', 'world': 'ironvale', 'seed': 7, 'advanced_mode': !Store.I.guided, 'enemy': true}))));
            },
          ),
        ]),
      ),
    );
  }

  Widget _searchBar(CodeEditorState? ed) {
    return Container(
      color: Theme.of(context).colorScheme.surfaceContainerHigh,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Row(children: [
        Expanded(child: TextField(controller: _find, decoration: const InputDecoration(isDense: true, hintText: 'Find'), onSubmitted: (_) => ed?.findNext(_find.text))),
        const SizedBox(width: 6),
        Expanded(child: TextField(controller: _repl, decoration: const InputDecoration(isDense: true, hintText: 'Replace'))),
        IconButton(icon: const Icon(Icons.keyboard_arrow_up), onPressed: () => ed?.findNext(_find.text, backwards: true)),
        IconButton(icon: const Icon(Icons.keyboard_arrow_down), onPressed: () => ed?.findNext(_find.text)),
        TextButton(
            onPressed: () {
              if (ed != null && ed.replaceCurrent(_find.text, _repl.text)) ed.findNext(_find.text);
            },
            child: const Text('Replace')),
        TextButton(
            onPressed: () {
              final n = ed?.replaceAll(_find.text, _repl.text) ?? 0;
              toast(context, '$n replaced');
            },
            child: const Text('All')),
      ]),
    );
  }

  Widget _problemStrip() {
    if (_problems.isEmpty) {
      return Container(
        width: double.infinity,
        color: const Color(0xFF12301F),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        child: const Text('No problems found', style: TextStyle(fontSize: 12.5)),
      );
    }
    final p = _problems.first as Map<String, dynamic>;
    return InkWell(
      onTap: () => setState(() {
        _showPanel = true;
        _tab = 0;
      }),
      child: Container(
        width: double.infinity,
        color: p['severity'] == 'error' ? const Color(0xFF3A1717) : const Color(0xFF3A3017),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        child: Text('${_problems.length} problem(s). Line ${p['line']}: ${p['message']}', style: const TextStyle(fontSize: 12.5), maxLines: 1, overflow: TextOverflow.ellipsis),
      ),
    );
  }

  Widget _runPanel() {
    const tabs = ['Problems', 'Console', 'Robots', 'Debug', 'History'];
    return Container(
      color: const Color(0xFF111820),
      child: Column(children: [
        SizedBox(
          height: 40,
          child: ListView(scrollDirection: Axis.horizontal, children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                child: ChoiceChip(
                  label: Text(i == 0 && _problems.isNotEmpty ? '${tabs[i]} (${_problems.length})' : tabs[i]),
                  selected: _tab == i,
                  onSelected: (_) => setState(() => _tab = i),
                  visualDensity: VisualDensity.compact,
                ),
              ),
          ]),
        ),
        if (_runError != null) Padding(padding: const EdgeInsets.all(6), child: ErrorBox(_runError!)),
        Expanded(child: _tabBody()),
      ]),
    );
  }

  Widget _tabBody() {
    switch (_tab) {
      case 0:
        return ListView(padding: const EdgeInsets.all(8), children: [
          if (_problems.isEmpty) const Text('No problems found.'),
          for (final p in _problems)
            ListTile(
              dense: true,
              leading: Icon((p as Map)['severity'] == 'error' ? Icons.error : Icons.warning, color: p['severity'] == 'error' ? Colors.redAccent : Colors.amber, size: 18),
              title: Text('Line ${p['line']}, col ${p['col']}: ${p['message']}', style: const TextStyle(fontSize: 12.5)),
            ),
        ]);
      case 1:
        return ListView(padding: const EdgeInsets.all(8), reverse: true, children: [
          for (final l in _console.reversed.take(200)) Text(l, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
          Text('tick ${_snap['tick'] ?? 0}${_running ? '  (running)' : ''}', style: const TextStyle(fontSize: 12, color: Colors.cyanAccent)),
        ]);
      case 2:
        final robots = ((_snap['robots'] as List<dynamic>?) ?? []).where((r) => (r as Map)['team'] == 0).toList();
        return ListView(padding: const EdgeInsets.all(8), children: [
          for (final r in robots)
            ListTile(
              dense: true,
              leading: Icon(clsIcon((r as Map)['cls'] as String), size: 18),
              title: Text('${clsTitle(r['cls'] as String)} #${r['id']}  (${r['x']},${r['y']})  ${r['action']}', style: const TextStyle(fontSize: 12.5)),
              subtitle: Text('hp ${r['hp']}/${r['maxhp']}  energy ${r['energy']}  cargo ${r['cargo']}  script ${r['script']}${(r['err'] ?? '').toString().isEmpty ? '' : '\nERROR: ${r['err']}'}',
                  style: TextStyle(fontSize: 11.5, color: (r['err'] ?? '').toString().isEmpty ? null : Colors.amber)),
              selected: _dbgRobot == r['id'],
              onTap: () => setState(() => _dbgRobot = (r['id'] as num).toInt()),
            ),
          if (robots.isEmpty) const Text('Press Run to start the test arena.'),
        ]);
      case 3:
        return ListView(padding: const EdgeInsets.all(8), children: [
          Text('Tap a line number to toggle a breakpoint (${(_breaks[_name] ?? <int>{}).length} set in $_name). '
              'Select a robot in the Robots tab, then run its next tick on a copy of the game.', style: const TextStyle(fontSize: 12)),
          Wrap(spacing: 8, children: [
            Text('Robot: ${_dbgRobot ?? 'none'}'),
            FilledButton.tonal(onPressed: _debugTick, child: const Text('Debug next tick')),
          ]),
          if (_dbg != null) ...[
            Text('ok ${_dbg!['ok']}  script ${_dbg!['script']}  lines ${_dbg!['lines']}  action ${_dbg!['action']}', style: const TextStyle(fontSize: 12)),
            if (_dbg!['error'] != null) Text('${_dbg!['error']}', style: const TextStyle(color: Colors.amber, fontSize: 12)),
            Text('Executed lines: ${((_dbg!['trace'] as List<dynamic>?) ?? []).take(80).join(' ')}', style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5)),
            const Text('Variables at breakpoints', style: TextStyle(fontWeight: FontWeight.w700)),
            for (final s in ((_dbg!['snapshots'] as List<dynamic>?) ?? []))
              Text('line ${(s as Map)['line']} in ${s['function']}: ${s['variables']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5)),
            Text('robot.memory: ${_dbg!['memory']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5)),
          ],
          if (_info != null) Text('Live memory: ${_info!['memory']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5)),
        ]);
      default:
        final h = (_info?['history'] as List<dynamic>?) ?? [];
        return ListView(padding: const EdgeInsets.all(8), children: [
          Text(_dbgRobot == null ? 'Select a robot in the Robots tab.' : 'Recent actions of robot #$_dbgRobot', style: const TextStyle(fontSize: 12)),
          for (final e in h.reversed) Text('tick ${(e as List)[0]}: ${e[1]}', style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
        ]);
    }
  }
}
