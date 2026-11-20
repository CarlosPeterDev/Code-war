import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../engine.dart';
import '../store.dart';
import '../widgets/code_editor.dart';
import '../widgets/common.dart';

class LearnScreen extends StatelessWidget {
  const LearnScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Column(children: [
        const TabBar(isScrollable: true, tabs: [
          Tab(text: 'Lessons'),
          Tab(text: 'API reference'),
          Tab(text: 'Puzzles'),
          Tab(text: 'Sandbox & Python'),
        ]),
        const Expanded(child: TabBarView(children: [_LessonsTab(), _ApiTab(), _PuzzlesTab(), _GuideTab()])),
      ]),
    );
  }
}

class _LessonsTab extends StatelessWidget {
  const _LessonsTab();
  @override
  Widget build(BuildContext context) {
    return EngineLoader<List<dynamic>>(
      load: () async => (await Engine.I.call('lesson_list')) as List<dynamic>,
      builder: (context, ls) => ListenableBuilder(
        listenable: Store.I,
        builder: (context, _) {
          String? last;
          final children = <Widget>[];
          for (final l in ls) {
            final m = l as Map<String, dynamic>;
            if (m['section'] != last) {
              last = m['section'] as String;
              children.add(Padding(padding: const EdgeInsets.fromLTRB(4, 14, 4, 4), child: Text(last, style: Theme.of(context).textTheme.titleMedium)));
            }
            final done = Store.I.lessonsDone.contains(m['id']);
            children.add(Card(
              child: ListTile(
                leading: Icon(done ? Icons.check_circle : Icons.play_circle_outline, color: done ? Colors.greenAccent : null),
                title: Text('${m['title']}'),
                subtitle: Text(m['kind'] == 'sim' ? 'Interactive: runs in the game' : 'Python exercise'),
                onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                  builder: (_) => ExerciseScreen(
                    title: m['title'] as String,
                    text: m['text'] as String,
                    starter: m['starter'] as String,
                    hint: null,
                    run: (src) async => (await Engine.I.call('run_lesson', [m['id'], src])) as Map<String, dynamic>,
                    onPassed: () => Store.I.markLesson(m['id'] as String),
                  ),
                )),
              ),
            ));
          }
          return ListView(padding: const EdgeInsets.all(12), children: children);
        },
      ),
    );
  }
}

class _PuzzlesTab extends StatelessWidget {
  const _PuzzlesTab();
  @override
  Widget build(BuildContext context) {
    return EngineLoader<List<dynamic>>(
      load: () async => (await Engine.I.call('puzzle_list')) as List<dynamic>,
      builder: (context, ps) => ListenableBuilder(
        listenable: Store.I,
        builder: (context, _) => ListView(padding: const EdgeInsets.all(12), children: [
          const Padding(padding: EdgeInsets.all(4), child: Text('Programming challenges: write a function, the engine runs it against hidden test cases inside the sandbox.')),
          for (final p in ps)
            Card(
              child: ListTile(
                leading: Icon(Store.I.puzzlesDone.contains((p as Map)['id']) ? Icons.check_circle : Icons.extension, color: Store.I.puzzlesDone.contains(p['id']) ? Colors.greenAccent : null),
                title: Text('${p['title']}'),
                subtitle: Text('Level ${p['level']} - ${p['topic']} - ${p['tests']} tests'),
                onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                  builder: (_) => ExerciseScreen(
                    title: p['title'] as String,
                    text: p['statement'] as String,
                    starter: p['starter'] as String,
                    hint: p['hint'] as String?,
                    run: (src) async => (await Engine.I.call('run_puzzle', [p['id'], src])) as Map<String, dynamic>,
                    onPassed: () => Store.I.markPuzzle(p['id'] as String),
                  ),
                )),
              ),
            ),
        ]),
      ),
    );
  }
}

/// One exercise: description, editor, Run and result list.
class ExerciseScreen extends StatefulWidget {
  const ExerciseScreen({super.key, required this.title, required this.text, required this.starter, required this.run, required this.onPassed, this.hint});
  final String title, text, starter;
  final String? hint;
  final Future<Map<String, dynamic>> Function(String) run;
  final Future<void> Function() onPassed;
  @override
  State<ExerciseScreen> createState() => _ExerciseScreenState();
}

class _ExerciseScreenState extends State<ExerciseScreen> {
  late final PyController _c = PyController(text: widget.starter);
  List<dynamic> _api = [];
  Map<String, dynamic>? _res;
  bool _busy = false;
  bool _hint = false;

  @override
  void initState() {
    super.initState();
    Engine.I.apiReference().then((a) {
      if (mounted) setState(() => _api = a);
    }).catchError((Object _) => <dynamic>[]);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  Future<void> _go() async {
    setState(() => _busy = true);
    try {
      final r = await widget.run(_c.text);
      _res = r;
      if (r['ok'] == true) await widget.onPassed();
    } catch (e) {
      _res = {'ok': false, 'message': '$e', 'results': [], 'problems': []};
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final r = _res;
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: SafeArea(
        child: Column(children: [
          Container(
            constraints: const BoxConstraints(maxHeight: 190),
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            child: SingleChildScrollView(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(widget.text),
                if (widget.hint != null) TextButton(onPressed: () => setState(() => _hint = !_hint), child: Text(_hint ? 'Hide hint' : 'Show hint')),
                if (_hint && widget.hint != null) Text(widget.hint!, style: const TextStyle(color: Colors.amber)),
              ]),
            ),
          ),
          Expanded(child: CodeEditor(controller: _c, api: _api, guided: true, showHelp: true)),
          if (r != null)
            Container(
              constraints: const BoxConstraints(maxHeight: 160),
              width: double.infinity,
              color: r['ok'] == true ? const Color(0xFF12301F) : const Color(0xFF2B1A1A),
              padding: const EdgeInsets.all(8),
              child: SingleChildScrollView(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${r['message']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  for (final p in ((r['problems'] as List<dynamic>?) ?? [])) Text('${p is Map ? 'Line ${p['line']}: ${p['message']}' : p}', style: const TextStyle(fontSize: 12, color: Colors.amber)),
                  for (final t in ((r['results'] as List<dynamic>?) ?? []))
                    Text('${(t as Map)['passed'] == true ? 'PASS' : 'FAIL'}  ${t['args'] ?? t['name'] ?? ''}  expected ${t['expected'] ?? ''}  got ${t['got'] ?? ''}', style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
                ]),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(6),
            child: Row(children: [
              Expanded(child: FilledButton.icon(onPressed: _busy ? null : _go, icon: const Icon(Icons.play_arrow), label: Text(_busy ? 'Running...' : 'Run and check'))),
              const SizedBox(width: 8),
              OutlinedButton(onPressed: () => setState(() { _c.text = widget.starter; _res = null; }), child: const Text('Reset')),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _ApiTab extends StatefulWidget {
  const _ApiTab();
  @override
  State<_ApiTab> createState() => _ApiTabState();
}

class _ApiTabState extends State<_ApiTab> {
  String _q = '';
  String _owner = 'all';

  @override
  Widget build(BuildContext context) {
    return EngineLoader<List<dynamic>>(
      load: Engine.I.apiReference,
      builder: (context, api) {
        final q = _q.toLowerCase();
        final list = api.where((e) {
          final m = e as Map<String, dynamic>;
          if (_owner != 'all' && m['owner'] != _owner) return false;
          return q.isEmpty || '${m['name']} ${m['signature']} ${m['description']}'.toLowerCase().contains(q);
        }).toList();
        return Column(children: [
          Padding(
            padding: const EdgeInsets.all(10),
            child: Row(children: [
              Expanded(
                child: TextField(
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search the API (name or description)', isDense: true, border: OutlineInputBorder()),
                  onChanged: (v) => setState(() => _q = v),
                ),
              ),
              const SizedBox(width: 8),
              DropdownButton<String>(
                value: _owner,
                items: const [
                  DropdownMenuItem(value: 'all', child: Text('All')),
                  DropdownMenuItem(value: 'robot', child: Text('robot')),
                  DropdownMenuItem(value: 'base', child: Text('base')),
                  DropdownMenuItem(value: 'entity', child: Text('entity')),
                ],
                onChanged: (v) => setState(() => _owner = v ?? 'all'),
              ),
            ]),
          ),
          Text('${list.length} of ${api.length} entries', style: const TextStyle(fontSize: 12, color: Colors.white54)),
          Expanded(
            child: ListView(children: [
              for (final e in list) _entry(context, e as Map<String, dynamic>),
            ]),
          ),
        ]);
      },
    );
  }

  Widget _entry(BuildContext context, Map<String, dynamic> m) {
    final params = (m['params'] as List<dynamic>).cast<Map<String, dynamic>>();
    final errors = (m['errors'] as List<dynamic>).cast<String>();
    return ExpansionTile(
      title: Text('${m['signature']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 13.5, fontWeight: FontWeight.w700)),
      subtitle: Text('${m['description']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      expandedCrossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('${m['description']}'),
        const SizedBox(height: 4),
        Text('Kind: ${m['kind']}   Returns: ${m['returns']}'),
        Text('Cost: ${m['cost']}'),
        if (params.isNotEmpty) const Padding(padding: EdgeInsets.only(top: 6), child: Text('Parameters', style: TextStyle(fontWeight: FontWeight.w700))),
        for (final p in params) Text('  ${p['name']} : ${p['type']}  -  ${p['valid']}', style: const TextStyle(fontSize: 12.5)),
        if (errors.isNotEmpty) const Padding(padding: EdgeInsets.only(top: 6), child: Text('Errors / failure cases', style: TextStyle(fontWeight: FontWeight.w700))),
        for (final er in errors) Text('  $er', style: const TextStyle(fontSize: 12.5, color: Colors.amber)),
        const Padding(padding: EdgeInsets.only(top: 6), child: Text('Example', style: TextStyle(fontWeight: FontWeight.w700))),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(8),
          color: const Color(0xFF0F151D),
          child: Text('${m['example']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5)),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: '${m['example']}'));
              if (context.mounted) toast(context, 'Example copied');
            },
            icon: const Icon(Icons.copy, size: 16),
            label: const Text('Copy example'),
          ),
        ),
      ],
    );
  }
}

class _GuideTab extends StatelessWidget {
  const _GuideTab();
  @override
  Widget build(BuildContext context) {
    return EngineLoader<Map<String, dynamic>>(
      load: () async {
        final c = await Engine.I.catalog();
        final v = await Engine.I.call('version') as Map<String, dynamic>;
        return {'catalog': c, 'version': v};
      },
      builder: (context, d) {
        final lim = (d['catalog'] as Map<String, dynamic>)['limits'] as Map<String, dynamic>;
        final diffs = (d['catalog'] as Map<String, dynamic>)['difficulties'] as Map<String, dynamic>;
        return ListView(padding: const EdgeInsets.all(14), children: [
          Panel(
            title: 'Python version',
            child: Text('Your scripts run on CPython ${(d['version'] as Map)['python']} embedded in the app (Chaquopy). Real Python syntax: functions, classes, comprehensions, f-strings, try/except, lambda, dicts, sets, tuples, slicing.'),
          ),
          Panel(
            title: 'Script structure',
            child: const Text('def update(robot):  - called once per tick for every robot of yours (4 ticks = 1 second).\n'
                'def commander(base):  - called once per tick for your base (queue robots, research, assign scripts).\n'
                'robot.memory is a dict that persists between ticks. Module-level variables are NOT shared between robots.'),
          ),
          Panel(
            title: 'Budgets (per call)',
            child: Text('Instruction budget: depends on difficulty (${diffs.entries.map((e) => '${kDifficultyNames[e.key]} ${(e.value as Map)['line_budget']}').join(', ')} lines per robot per tick).\n'
                'Wall-clock limit: a few tens of milliseconds per robot call, longer for the commander.\n'
                'Memory: sampled check against a ~16 MiB growth limit.\n'
                'Sequences/ranges: at most ${lim['max_seq']} items; ** exponent at most ${lim['max_pow_exp']}.\n'
                'Exceeding a budget stops that call, shows an error on the robot and the game continues.'),
          ),
          Panel(
            title: 'Allowed and blocked',
            child: Text('Importable modules: ${(lim['allowed_modules'] as List).join(', ')} (math is trimmed to safe functions).\n'
                'Blocked names: ${(lim['forbidden_names'] as List).join(', ')}.\n'
                'No file, network, process, threading, reflection or dynamic code (eval, exec, open, __import__ ...).'),
          ),
          Panel(
            title: 'Unsupported / different from normal Python',
            child: const Text('- No imports beyond math and random.\n'
                '- No file or network access, no threads, no async/await, no generators that leak frames, no str.format (use f-strings).\n'
                '- Names starting with double underscore and frame/code attributes are rejected.\n'
                '- Output goes through print() or robot.log() to the log panel.\n'
                '- This is an in-process sandbox, not an operating-system boundary.'),
          ),
        ]);
      },
    );
  }
}
