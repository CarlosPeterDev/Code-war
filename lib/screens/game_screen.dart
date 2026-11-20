import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/common.dart';

class GameArgs {
  const GameArgs({this.title = 'Match', this.config, this.campaignId, this.saveBlob, this.starKey, this.assignOverride});
  final String title;
  final Map<String, dynamic>? config;
  final String? campaignId;
  final String? saveBlob;
  final String? starKey;
  final Map<String, String>? assignOverride;
}

class GameScreen extends StatefulWidget {
  const GameScreen({super.key, required this.args});
  final GameArgs args;
  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  WebViewController? _web;
  String? _error;
  Map<String, dynamic>? _world;
  Map<String, dynamic> _snap = {};
  List<dynamic> _problems = [];
  bool _jsReady = false;
  bool _paused = false;
  bool _over = false;
  bool _disposed = false;
  bool _showingResult = false;
  int _speed = 1;
  int? _selId;
  String? _selKind;
  String? _panel = 'goals';
  Map<String, dynamic>? _info;
  Map<String, dynamic>? _debug;
  Map<String, dynamic>? _catalog;
  String _quality = Store.I.quality;
  final List<Map<String, dynamic>> _logsSeen = [];

  @override
  void initState() {
    super.initState();
    SystemChrome.setPreferredOrientations([DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    _boot();
  }

  @override
  void dispose() {
    _disposed = true;
    SystemChrome.setPreferredOrientations(DeviceOrientation.values);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    super.dispose();
  }

  Future<void> _boot() async {
    try {
      _catalog = await Engine.I.catalog();
      final a = widget.args;
      final scripts = jsonEncode(Store.I.scripts);
      final assign = jsonEncode(a.assignOverride ?? Store.I.assign);
      String raw;
      if (a.saveBlob != null) {
        raw = await Engine.I.raw('load_game', [a.saveBlob]);
      } else if (a.campaignId != null) {
        raw = await Engine.I.raw('start_campaign', [a.campaignId, scripts, assign, !Store.I.guided]);
      } else {
        raw = await Engine.I.raw('new_game', [jsonEncode(a.config), scripts, assign]);
      }
      final d = jsonDecode(raw) as Map<String, dynamic>;
      _world = d['world'] as Map<String, dynamic>;
      _snap = d['snapshot'] as Map<String, dynamic>;
      _problems = (d['problems'] is List) ? d['problems'] as List<dynamic> : <dynamic>[];
      final c = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(const Color(0xFF0B1016))
        ..addJavaScriptChannel('CWChannel', onMessageReceived: (m) => _onJs(m.message))
        ..loadFlutterAsset('assets/renderer/index.html');
      if (!mounted) return;
      setState(() => _web = c);
      unawaited(_loop());
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  void _onJs(String msg) {
    Map<String, dynamic> m;
    try {
      m = jsonDecode(msg) as Map<String, dynamic>;
    } catch (_) {
      return;
    }
    switch (m['type']) {
      case 'ready':
        _initRenderer();
        break;
      case 'error':
        if (mounted) setState(() => _error = 'Renderer: ${m['message']}');
        break;
      case 'select':
        _select(m['kind'] as String?, (m['id'] as num?)?.toInt());
        break;
    }
  }

  Future<void> _initRenderer() async {
    final w = jsonEncode(_world);
    await _web!.runJavaScript('CW.setQuality(${jsonEncode(_quality)});');
    await _web!.runJavaScript('CW.init($w).then(function(){CW.update(${jsonEncode(_snap)}, 250);});');
    _jsReady = true;
  }

  Future<void> _loop() async {
    while (!_disposed) {
      if (_jsReady && !_paused && !_over && _error == null) {
        try {
          final raw = await Engine.I.raw('step', [_speed]);
          if (_disposed) return;
          final s = jsonDecode(raw) as Map<String, dynamic>;
          _snap = s;
          for (final l in (s['logs'] as List<dynamic>? ?? [])) {
            final lm = l as Map<String, dynamic>;
            if (_logsSeen.isEmpty || (lm['tick'] as int) > (_logsSeen.last['tick'] as int) || !_sameLog(lm)) {
              if (_logsSeen.isEmpty || (lm['tick'] as int) >= (_logsSeen.last['tick'] as int)) {
                if (!_logsSeen.any((x) => x['tick'] == lm['tick'] && x['text'] == lm['text'] && x['robot'] == lm['robot'])) {
                  _logsSeen.add(lm);
                }
              }
            }
          }
          if (_logsSeen.length > 300) _logsSeen.removeRange(0, _logsSeen.length - 300);
          unawaited(_web!.runJavaScript('CW.update($raw, 250);'));
          if (_selId != null && _selKind == 'robot' && _panel == 'robot') await _refreshInfo();
          if (mounted) setState(() {});
          if (s['result'] != null) {
            _over = true;
            _finish(s['result'] as Map<String, dynamic>);
          }
        } catch (e) {
          if (mounted) setState(() => _error = e.toString());
        }
      }
      await Future<void>.delayed(const Duration(milliseconds: 250));
    }
  }

  bool _sameLog(Map<String, dynamic> l) =>
      _logsSeen.any((x) => x['tick'] == l['tick'] && x['text'] == l['text'] && x['robot'] == l['robot']);

  void _select(String? kind, int? id) {
    _selId = id;
    _selKind = kind;
    _debug = null;
    if (kind == 'robot' && id != null) {
      _panel = 'robot';
      _web?.runJavaScript('CW.select($id);');
      _refreshInfo();
    } else {
      _web?.runJavaScript('CW.select(null);');
      _info = null;
    }
    if (mounted) setState(() {});
  }

  Future<void> _refreshInfo() async {
    if (_selId == null) return;
    try {
      final d = await Engine.I.call('robot_info', [_selId]);
      if (mounted) setState(() => _info = d as Map<String, dynamic>?);
    } catch (_) {}
  }

  Map<String, dynamic> get _team => (_snap['team'] as Map<String, dynamic>?) ?? {};
  List<dynamic> get _robots => (_snap['robots'] as List<dynamic>?) ?? [];

  Future<void> _finish(Map<String, dynamic> result) async {
    if (_showingResult) return;
    _showingResult = true;
    Map<String, dynamic>? report;
    try {
      report = (await Engine.I.call('analysis_report')) as Map<String, dynamic>;
    } catch (_) {}
    final won = result['winner'] == 0;
    final stars = (report?['stars'] as num?)?.toInt() ?? 0;
    if (widget.args.starKey != null && won) await Store.I.recordStars(widget.args.starKey!, stars < 1 ? 1 : stars);
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: Text(won ? 'Victory' : (result['winner'] == null ? 'Time up' : 'Defeat')),
        content: SizedBox(
          width: 520,
          child: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text('${result['reason']}'),
              const SizedBox(height: 8),
              if (report != null) ...[
                Row(children: [Stars(won ? (stars < 1 ? 1 : stars) : 0, size: 26), const SizedBox(width: 12), Text('Score ${report['score']}')]),
                const Divider(),
                const Text('Post-match analysis', style: TextStyle(fontWeight: FontWeight.w700)),
                for (final it in (report['items'] as List<dynamic>))
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Icon(_kindIcon((it as Map<String, dynamic>)['kind'] as String), size: 16, color: _kindColor(it['kind'] as String)),
                      const SizedBox(width: 6),
                      Expanded(child: Text('${it['text']}', style: const TextStyle(fontSize: 13))),
                    ]),
                  ),
              ],
            ]),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Watch scene')),
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).pop();
            },
            child: const Text('Exit'),
          ),
        ],
      ),
    );
  }

  IconData _kindIcon(String k) => k == 'good' ? Icons.check_circle : (k == 'bad' ? Icons.error : (k == 'tip' ? Icons.lightbulb : Icons.info));
  Color _kindColor(String k) => k == 'good' ? Colors.greenAccent : (k == 'bad' ? Colors.redAccent : (k == 'tip' ? Colors.amber : Colors.lightBlueAccent));

  Future<void> _hotReload() async {
    try {
      final p = await Engine.I.call('set_scripts', [jsonEncode(Store.I.scripts), jsonEncode(Store.I.assign)]);
      if (mounted) {
        toast(context, (p is Map && p.isNotEmpty) ? 'Reloaded with ${p.length} script problem(s)' : 'Scripts reloaded');
      }
    } catch (e) {
      if (mounted) toast(context, '$e');
    }
  }

  Future<void> _save(int slot) async {
    try {
      final blob = await Engine.I.raw('save_game');
      await Store.I.writeSave(slot, blob, {
        'title': widget.args.title,
        'tick': _snap['tick'],
        'time': DateTime.now().toIso8601String(),
      });
      if (mounted) toast(context, 'Saved to slot ${slot + 1}');
    } catch (e) {
      if (mounted) toast(context, 'Save failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Code Wars')),
        body: Center(child: Padding(padding: const EdgeInsets.all(24), child: ErrorBox(_error!))),
      );
    }
    if (_web == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      body: Stack(children: [
        Positioned.fill(child: WebViewWidget(controller: _web!)),
        if (!_jsReady) const Center(child: Text('Loading 3D engine...')),
        SafeArea(child: Column(children: [_topBar(), Expanded(child: _body())])),
      ]),
    );
  }

  Widget _chip(IconData i, String t, {Color? color}) => Container(
        margin: const EdgeInsets.only(right: 6),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(color: const Color(0xCC0E141B), borderRadius: BorderRadius.circular(12)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(i, size: 15, color: color ?? Colors.white70),
          const SizedBox(width: 4),
          Text(t, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
        ]),
      );

  Widget _topBar() {
    final tick = (_snap['tick'] as num?)?.toInt() ?? 0;
    final maxT = (_snap['max_ticks'] as num?)?.toInt() ?? 0;
    final mine = _robots.where((r) => (r as Map)['team'] == 0).length;
    final maxPop = (_catalog?['max_pop'] as num?)?.toInt() ?? 40;
    final secs = tick ~/ 4;
    return Container(
      color: const Color(0x990B1016),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          IconButton(icon: const Icon(Icons.arrow_back), tooltip: 'Exit', onPressed: _confirmExit),
          _chip(Icons.timer, '${secs ~/ 60}:${(secs % 60).toString().padLeft(2, '0')}${maxT < 100000 ? ' / ${(maxT ~/ 4) ~/ 60}:${((maxT ~/ 4) % 60).toString().padLeft(2, '0')}' : ''}'),
          _chip(Icons.toll, '${(_team['credits'] as num?)?.round() ?? 0}', color: const Color(0xFFFFC233)),
          _chip(Icons.diamond, '${(_team['alloy'] as num?)?.round() ?? 0}', color: Colors.lightBlueAccent),
          _chip(Icons.groups, '$mine / $maxPop'),
          IconButton(
            icon: Icon(_paused ? Icons.play_arrow : Icons.pause),
            tooltip: _paused ? 'Resume' : 'Pause',
            onPressed: () => setState(() => _paused = !_paused),
          ),
          for (final s in const [1, 2, 4, 8])
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: ChoiceChip(
                label: Text('${s}x'),
                selected: _speed == s,
                visualDensity: VisualDensity.compact,
                onSelected: (_) => setState(() => _speed = s),
              ),
            ),
          const SizedBox(width: 6),
          for (final p in const [
            ['goals', Icons.flag, 'Goals'],
            ['robot', Icons.smart_toy, 'Robot'],
            ['base', Icons.home_work, 'Base'],
            ['log', Icons.terminal, 'Log'],
            ['tools', Icons.build, 'Tools'],
          ])
            IconButton(
              icon: Icon(p[1] as IconData, color: _panel == p[0] ? const Color(0xFF22D3EE) : null),
              tooltip: p[2] as String,
              onPressed: () => setState(() => _panel = _panel == p[0] ? null : p[0] as String),
            ),
          IconButton(icon: const Icon(Icons.center_focus_strong), tooltip: 'Focus HQ', onPressed: () => _web?.runJavaScript('CW.focusHome();')),
        ]),
      ),
    );
  }

  Future<void> _confirmExit() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Leave match?'),
        content: const Text('Progress of this match is lost unless you saved it from the Tools panel.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Stay')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Leave')),
        ],
      ),
    );
    if (ok == true && mounted) Navigator.of(context).pop();
  }

  Widget _body() {
    return Row(children: [
      Expanded(
        child: Align(
          alignment: Alignment.bottomLeft,
          child: _problems.isNotEmpty
              ? Padding(padding: const EdgeInsets.all(8), child: _chip(Icons.warning, 'Script problems: see Log', color: Colors.amber))
              : const SizedBox.shrink(),
        ),
      ),
      if (_panel != null)
        Container(
          width: 330,
          margin: const EdgeInsets.fromLTRB(0, 4, 6, 6),
          decoration: BoxDecoration(color: const Color(0xEE0E141B), borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white12)),
          child: ClipRRect(borderRadius: BorderRadius.circular(12), child: _panelBody()),
        ),
    ]);
  }

  Widget _panelBody() {
    switch (_panel) {
      case 'robot':
        return _robotPanel();
      case 'base':
        return _basePanel();
      case 'log':
        return _logPanel();
      case 'tools':
        return _toolsPanel();
      default:
        return _goalsPanel();
    }
  }

  Widget _goalsPanel() {
    final obj = (_snap['objectives'] as List<dynamic>?) ?? [];
    return ListView(padding: const EdgeInsets.all(10), children: [
      Text(widget.args.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
      const SizedBox(height: 6),
      if (obj.isEmpty) const Text('Sandbox: no objectives. Experiment freely.'),
      for (final o in obj)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(children: [
            Icon((o as Map)['done'] == true ? Icons.check_circle : Icons.radio_button_unchecked, size: 18, color: o['done'] == true ? Colors.greenAccent : Colors.white54),
            const SizedBox(width: 8),
            Expanded(child: Text('${o['title']}  (${_fmt(o['current'])} / ${_fmt(o['goal'])})', style: const TextStyle(fontSize: 13))),
          ]),
        ),
      const Divider(),
      Text('Tap a robot in the 3D view to inspect it. Drag to rotate, pinch to zoom, two fingers to pan.',
          style: Theme.of(context).textTheme.bodySmall),
    ]);
  }

  String _fmt(dynamic v) => v is num ? (v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(1)) : '$v';

  Widget _robotPanel() {
    final i = _info;
    if (_selId == null || i == null) {
      return const Padding(padding: EdgeInsets.all(14), child: Text('No robot selected. Tap one of your robots in the 3D view.'));
    }
    final mine = i['team'] == 0;
    final stats = i['stats'] as Map<String, dynamic>;
    final scripts = Store.I.scripts.keys.toList()..sort();
    final hist = (i['history'] as List<dynamic>);
    return ListView(padding: const EdgeInsets.all(10), children: [
      Row(children: [
        Icon(clsIcon(i['cls'] as String), size: 20),
        const SizedBox(width: 6),
        Text('${clsTitle(i['cls'] as String)} #${i['id']}  ${mine ? '' : '(enemy)'}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
      ]),
      Text('${i['desc']}', style: const TextStyle(fontSize: 12, color: Colors.white60)),
      const SizedBox(height: 6),
      Text('HP ${i['hp']}   Energy ${i['energy']}   Cargo ${i['cargo']}   at (${i['x']}, ${i['y']})', style: const TextStyle(fontSize: 12.5)),
      Text('Damage ${stats['damage']}  Armor ${stats['armor']}  Speed ${stats['speed']}  Vision ${stats['vision']}  Cap ${stats['capacity']}  Range ${stats['range']}',
          style: const TextStyle(fontSize: 12)),
      if (mine) ...[
        const Divider(),
        Row(children: [
          const Text('Script: '),
          Expanded(
            child: DropdownButton<String>(
              isExpanded: true,
              value: scripts.contains(i['script']) ? i['script'] as String : null,
              hint: Text('${i['script'] ?? 'none'}'),
              items: [for (final s in scripts) DropdownMenuItem(value: s, child: Text(s, overflow: TextOverflow.ellipsis))],
              onChanged: (v) async {
                if (v == null) return;
                Store.I.assign['robot:${i['id']}'] = v;
                await Store.I.saveScripts();
                await Engine.I.call('assign', ['robot:${i['id']}', v]);
                _refreshInfo();
              },
            ),
          ),
        ]),
        Row(children: [
          const Text('Group: '),
          Expanded(
            child: TextField(
              controller: TextEditingController(text: '${i['group']}'),
              decoration: const InputDecoration(isDense: true, hintText: 'e.g. alpha'),
              onSubmitted: (v) async {
                await Engine.I.call('set_group', [i['id'], v.trim()]);
                _refreshInfo();
              },
            ),
          ),
        ]),
        const SizedBox(height: 6),
        Wrap(spacing: 6, children: [
          OutlinedButton(onPressed: _debugOne, child: const Text('Debug 1 tick')),
          OutlinedButton(
            onPressed: () => _web?.runJavaScript('CW.focus(${i['x']}, ${i['y']}, 10);'),
            child: const Text('Focus'),
          ),
        ]),
      ],
      if ((i['error'] ?? '').toString().isNotEmpty)
        Padding(padding: const EdgeInsets.only(top: 6), child: Text('Last error: ${i['error']}', style: const TextStyle(color: Colors.amber, fontSize: 12.5))),
      if (_debug != null) ...[
        const Divider(),
        const Text('Debugger', style: TextStyle(fontWeight: FontWeight.w700)),
        Text('ok: ${_debug!['ok']}  script: ${_debug!['script']}  lines: ${_debug!['lines']}  action: ${_debug!['action']}', style: const TextStyle(fontSize: 12)),
        if (_debug!['error'] != null) Text('${_debug!['error']}', style: const TextStyle(color: Colors.amber, fontSize: 12)),
        Text('Line trace: ${((_debug!['trace'] as List<dynamic>?) ?? []).take(40).join(', ')}', style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace')),
        for (final s in ((_debug!['snapshots'] as List<dynamic>?) ?? []).take(6))
          Text('line ${s['line']}: ${s['variables']}', style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace')),
        Text('memory: ${_debug!['memory']}', style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace')),
      ],
      const Divider(),
      const Text('Recent actions', style: TextStyle(fontWeight: FontWeight.w700)),
      for (final h in hist.reversed.take(8)) Text('t${(h as List)[0]}: ${h[1]}', style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
      const Text('Memory', style: TextStyle(fontWeight: FontWeight.w700)),
      Text('${i['memory']}', style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
    ]);
  }

  Future<void> _debugOne() async {
    if (_selId == null) return;
    try {
      final bps = <int>[];
      final d = await Engine.I.call('debug_robot', [_selId, jsonEncode(bps)]);
      if (mounted) setState(() => _debug = d as Map<String, dynamic>);
    } catch (e) {
      if (mounted) toast(context, '$e');
    }
  }

  Widget _basePanel() {
    final classes = (_catalog?['classes'] as Map<String, dynamic>?) ?? {};
    final tech = (_catalog?['tech'] as Map<String, dynamic>?) ?? {};
    final structs = (_catalog?['structures'] as Map<String, dynamic>?) ?? {};
    final credits = (_team['credits'] as num?)?.toDouble() ?? 0;
    final lv = (_team['tech'] as Map<String, dynamic>?) ?? {};
    final queue = (_team['queue'] as List<dynamic>?) ?? [];
    final research = _team['research'] as List<dynamic>?;
    final myStructs = ((_snap['structures'] as List<dynamic>?) ?? []).where((s) => (s as Map)['team'] == 0).toList();
    return ListView(padding: const EdgeInsets.all(10), children: [
      const Text('Produce robots', style: TextStyle(fontWeight: FontWeight.w800)),
      for (final e in classes.entries)
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(clsIcon(e.key)),
          title: Text('${clsTitle(e.key)}  -  ${(e.value as Map)['cost']} credits'),
          subtitle: Text('${(e.value as Map)['desc']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5)),
          trailing: FilledButton.tonal(
            onPressed: credits >= ((e.value as Map)['cost'] as num) ? () => _build(e.key) : null,
            child: const Text('Build'),
          ),
        ),
      if (queue.isNotEmpty) Text('Queue: ${queue.map((q) => '${(q as List)[0]} (${q[1]})').join(', ')}', style: const TextStyle(fontSize: 12)),
      const Divider(),
      const Text('Research', style: TextStyle(fontWeight: FontWeight.w800)),
      if (research != null) Text('Researching ${research[0]} (${research[1]} ticks left)', style: const TextStyle(fontSize: 12.5)),
      for (final e in tech.entries)
        Builder(builder: (_) {
          final level = (lv[e.key] as num?)?.toInt() ?? 0;
          final t = e.value as Map<String, dynamic>;
          final max = (t['levels'] as num).toInt();
          final costs = (t['costs'] as List<dynamic>);
          final next = level < max ? (costs[level] as num) : null;
          return ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('${clsTitle(e.key)}  Lv $level/$max'),
            subtitle: Text('${t['desc']}', style: const TextStyle(fontSize: 11.5)),
            trailing: next == null
                ? const Text('MAX')
                : FilledButton.tonal(onPressed: (research == null && credits >= next) ? () => _research(e.key) : null, child: Text('$next')),
          );
        }),
      const Divider(),
      const Text('Structures', style: TextStyle(fontWeight: FontWeight.w800)),
      Text('Builders create structures from script: robot.build(kind, x, y). Kinds: ${structs.keys.join(', ')}.', style: const TextStyle(fontSize: 12)),
      for (final s in myStructs)
        Text('${(s as Map)['kind']} #${s['id']}  hp ${s['hp']}/${s['maxhp']}${s['built'] == true ? '' : '  (under construction)'}', style: const TextStyle(fontSize: 12)),
    ]);
  }

  Future<void> _build(String cls) async {
    final ok = await Engine.I.call('build_robot', [cls]);
    if (mounted) toast(context, ok == true ? 'Queued $cls' : 'Cannot build $cls now (credits, queue or population limit)');
  }

  Future<void> _research(String name) async {
    final ok = await Engine.I.call('research', [name]);
    if (mounted) toast(context, ok == true ? 'Researching $name' : 'Cannot research $name now');
  }

  Widget _logPanel() {
    return ListView(padding: const EdgeInsets.all(10), reverse: false, children: [
      if (_problems.isNotEmpty) ...[
        const Text('Script problems', style: TextStyle(fontWeight: FontWeight.w800, color: Colors.amber)),
        Text('$_problems', style: const TextStyle(fontSize: 12)),
        const Divider(),
      ],
      const Text('Execution log (print / robot.log)', style: TextStyle(fontWeight: FontWeight.w800)),
      if (_logsSeen.isEmpty) const Text('Nothing logged yet.', style: TextStyle(fontSize: 12)),
      for (final l in _logsSeen.reversed.take(120))
        Text('t${l['tick']} ${l['robot'] != null ? '#${l['robot']} ' : ''}${l['text']}',
            style: TextStyle(fontSize: 11.5, fontFamily: 'monospace', color: l['level'] == 'error' ? Colors.amber : Colors.white70)),
    ]);
  }

  Widget _toolsPanel() {
    return ListView(padding: const EdgeInsets.all(10), children: [
      const Text('Scripts', style: TextStyle(fontWeight: FontWeight.w800)),
      const Text('Edit scripts in the Python Editor, then reload them here without restarting the match.', style: TextStyle(fontSize: 12)),
      FilledButton.icon(onPressed: _hotReload, icon: const Icon(Icons.refresh), label: const Text('Reload scripts now')),
      const Divider(),
      const Text('Graphics quality', style: TextStyle(fontWeight: FontWeight.w800)),
      SegmentedButton<String>(
        segments: const [
          ButtonSegment(value: 'low', label: Text('Low')),
          ButtonSegment(value: 'medium', label: Text('Med')),
          ButtonSegment(value: 'high', label: Text('High')),
        ],
        selected: {_quality},
        onSelectionChanged: (s) {
          setState(() => _quality = s.first);
          _web?.runJavaScript('CW.setQuality(${jsonEncode(s.first)});');
        },
      ),
      const Divider(),
      const Text('Save game', style: TextStyle(fontWeight: FontWeight.w800)),
      for (var s = 0; s < 3; s++)
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text('Slot ${s + 1}'),
          subtitle: Text(Store.I.saveMeta(s) == null ? 'empty' : '${Store.I.saveMeta(s)!['title']} - tick ${Store.I.saveMeta(s)!['tick']}'),
          trailing: OutlinedButton(onPressed: () => _save(s), child: const Text('Save')),
        ),
      const Divider(),
      OutlinedButton.icon(
        onPressed: () async {
          final r = await _statsText();
          if (mounted) {
            showDialog<void>(context: context, builder: (c) => AlertDialog(title: const Text('Render stats'), content: Text(r), actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('OK'))]));
          }
        },
        icon: const Icon(Icons.speed),
        label: const Text('Render statistics'),
      ),
    ]);
  }

  Future<String> _statsText() async {
    try {
      final r = await _web!.runJavaScriptReturningResult('JSON.stringify(CW.stats())');
      var s = r.toString();
      if (s.startsWith('"')) s = jsonDecode(s) as String;
      final m = jsonDecode(s) as Map<String, dynamic>;
      return m.entries.map((e) => '${e.key}: ${e.value}').join('\n');
    } catch (e) {
      return 'Unavailable: $e';
    }
  }
}
