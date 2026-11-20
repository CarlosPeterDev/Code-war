import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const Set<String> kKeywords = {
  'def', 'if', 'elif', 'else', 'for', 'while', 'return', 'in', 'not', 'and', 'or', 'True', 'False', 'None',
  'break', 'continue', 'pass', 'import', 'from', 'as', 'lambda', 'try', 'except', 'is', 'raise', 'with',
};
const Set<String> kBuiltins = {
  'len', 'range', 'min', 'max', 'sum', 'abs', 'round', 'sorted', 'int', 'float', 'str', 'list', 'dict', 'tuple',
  'set', 'enumerate', 'zip', 'print', 'any', 'all', 'isinstance', 'reversed', 'map', 'filter', 'divmod', 'pow',
};
const Map<String, String> kBuiltinDocs = {
  'len': 'len(x) -> int  - number of items in a list, dict, tuple or string.',
  'range': 'range(stop) / range(start, stop, step) -> sequence of ints (max 100000 items in the sandbox).',
  'min': 'min(iterable, key=None) / min(a, b, ...) -> smallest item.',
  'max': 'max(iterable, key=None) / max(a, b, ...) -> largest item.',
  'sum': 'sum(iterable) -> total of numbers.',
  'abs': 'abs(x) -> absolute value.',
  'round': 'round(x, digits=0) -> rounded number.',
  'sorted': 'sorted(iterable, key=None, reverse=False) -> new sorted list.',
  'print': 'print(...) -> writes a line to the execution log.',
  'enumerate': 'enumerate(items) -> (index, item) pairs.',
  'zip': 'zip(a, b) -> pairs of items from two sequences.',
  'isinstance': 'isinstance(x, type) -> True if x has that type (int, float, str, list, dict, tuple, bool).',
};
const List<String> kMathNames = [
  'sqrt', 'sin', 'cos', 'tan', 'atan2', 'hypot', 'floor', 'ceil', 'pi', 'fabs', 'log', 'exp', 'dist', 'inf',
  'isclose', 'trunc', 'gcd', 'isqrt',
];
const List<String> kSnippets = [
  'def update(robot):',
  'def commander(base):',
  'for e in robot.enemies():',
  'if robot.energy < 20:',
  'while True:',
];

class Sug {
  Sug(this.label, this.insert, {this.back = 0});
  final String label;
  final String insert;
  final int back; // move cursor back this many chars after insert
}

/// TextEditingController that paints Python syntax colours and wavy error underlines.
class PyController extends TextEditingController {
  PyController({super.text});

  Set<int> errorLines = <int>{}; // 1-based
  static final RegExp _tok = RegExp(
      r'''(#.*$)|("(?:[^"\\]|\\.)*"?|'(?:[^'\\]|\\.)*'?)|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)''');

  @override
  TextSpan buildTextSpan({required BuildContext context, TextStyle? style, required bool withComposing}) {
    final base = style ?? const TextStyle();
    final spans = <InlineSpan>[];
    final lines = text.split('\n');
    for (var i = 0; i < lines.length; i++) {
      final bad = errorLines.contains(i + 1);
      TextStyle s(Color c, {FontWeight? w, FontStyle? it}) => base.copyWith(
            color: c,
            fontWeight: w,
            fontStyle: it,
            decoration: bad ? TextDecoration.underline : null,
            decorationStyle: bad ? TextDecorationStyle.wavy : null,
            decorationColor: bad ? Colors.redAccent : null,
          );
      final line = lines[i];
      var pos = 0;
      var prev = '';
      for (final m in _tok.allMatches(line)) {
        if (m.start > pos) spans.add(TextSpan(text: line.substring(pos, m.start), style: s(const Color(0xFFD7DEE8))));
        final t = m.group(0)!;
        if (m.group(1) != null) {
          spans.add(TextSpan(text: t, style: s(const Color(0xFF6B7A8C), it: FontStyle.italic)));
        } else if (m.group(2) != null) {
          spans.add(TextSpan(text: t, style: s(const Color(0xFFE6C07B))));
        } else if (m.group(3) != null) {
          spans.add(TextSpan(text: t, style: s(const Color(0xFFD19A66))));
        } else if (kKeywords.contains(t)) {
          spans.add(TextSpan(text: t, style: s(const Color(0xFFC678DD), w: FontWeight.w600)));
        } else if (t == 'robot' || t == 'base') {
          spans.add(TextSpan(text: t, style: s(const Color(0xFF56B6C2), w: FontWeight.w600)));
        } else if (kBuiltins.contains(t)) {
          spans.add(TextSpan(text: t, style: s(const Color(0xFF61AFEF))));
        } else if (prev == 'def') {
          spans.add(TextSpan(text: t, style: s(const Color(0xFF98C379), w: FontWeight.w600)));
        } else {
          spans.add(TextSpan(text: t, style: s(const Color(0xFFD7DEE8))));
        }
        pos = m.end;
        prev = t;
      }
      if (pos < line.length) spans.add(TextSpan(text: line.substring(pos), style: s(const Color(0xFFD7DEE8))));
      if (i < lines.length - 1) spans.add(TextSpan(text: '\n', style: base));
    }
    return TextSpan(style: base, children: spans);
  }
}

class _Snap {
  _Snap(this.text, this.selection);
  final String text;
  final TextSelection selection;
}

/// Full-featured mobile Python editor core: gutter with breakpoints, auto-indent, undo/redo,
/// autocomplete chips, symbol row and contextual API help. Use a GlobalKey<CodeEditorState> for commands.
class CodeEditor extends StatefulWidget {
  const CodeEditor({
    super.key,
    required this.controller,
    required this.api,
    required this.guided,
    this.onChanged,
    this.breakpoints = const <int>{},
    this.traceLines = const <int>{},
    this.onToggleBreakpoint,
    this.showHelp = true,
  });

  final PyController controller;
  final List<dynamic> api;
  final bool guided;
  final VoidCallback? onChanged;
  final Set<int> breakpoints;
  final Set<int> traceLines;
  final void Function(int line)? onToggleBreakpoint;
  final bool showHelp;

  @override
  State<CodeEditor> createState() => CodeEditorState();
}

class CodeEditorState extends State<CodeEditor> {
  static const double fontSize = 14;
  static const double lineH = 1.45;
  static const double charW = 8.6;

  final List<_Snap> _undo = <_Snap>[];
  final List<_Snap> _redo = <_Snap>[];
  String _prevText = '';
  TextSelection _prevSel = const TextSelection.collapsed(offset: 0);
  DateTime _lastPush = DateTime.fromMillisecondsSinceEpoch(0);
  bool _applying = false;
  List<Sug> _sugs = <Sug>[];
  Map<String, dynamic>? _doc;
  String? _builtinDoc;
  final FocusNode focus = FocusNode();
  final ScrollController _vScroll = ScrollController();
  final ScrollController _hScroll = ScrollController();
  Map<String, List<Map<String, dynamic>>> _members = <String, List<Map<String, dynamic>>>{};

  bool get canUndo => _undo.isNotEmpty;
  bool get canRedo => _redo.isNotEmpty;

  @override
  void initState() {
    super.initState();
    _index();
    _prevText = widget.controller.text;
    widget.controller.addListener(_onController);
  }

  @override
  void didUpdateWidget(covariant CodeEditor old) {
    super.didUpdateWidget(old);
    if (old.controller != widget.controller) {
      old.controller.removeListener(_onController);
      widget.controller.addListener(_onController);
      _prevText = widget.controller.text;
      _undo.clear();
      _redo.clear();
    }
    if (old.api != widget.api) _index();
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onController);
    focus.dispose();
    _vScroll.dispose();
    _hScroll.dispose();
    super.dispose();
  }

  void _index() {
    final m = <String, List<Map<String, dynamic>>>{};
    for (final e in widget.api) {
      final o = (e as Map<String, dynamic>)['owner'] as String;
      m.putIfAbsent(o, () => <Map<String, dynamic>>[]).add(e);
    }
    _members = m;
  }

  // ---------------------------------------------------------------- editing helpers
  void _setValue(String text, TextSelection sel) {
    _applying = true;
    widget.controller.value = TextEditingValue(text: text, selection: sel);
    _prevText = text;
    _prevSel = sel;
    _applying = false;
  }

  void undo() {
    if (_undo.isEmpty) return;
    final cur = _Snap(widget.controller.text, widget.controller.selection);
    final s = _undo.removeLast();
    _redo.add(cur);
    _setValue(s.text, s.selection);
    _afterChange();
  }

  void redo() {
    if (_redo.isEmpty) return;
    final cur = _Snap(widget.controller.text, widget.controller.selection);
    final s = _redo.removeLast();
    _undo.add(cur);
    _setValue(s.text, s.selection);
    _afterChange();
  }

  void insertAtCursor(String s, {int back = 0}) {
    final c = widget.controller;
    final sel = c.selection;
    final start = sel.isValid ? sel.start : c.text.length;
    final end = sel.isValid ? sel.end : c.text.length;
    final t = c.text.replaceRange(start, end, s);
    final off = start + s.length - back;
    c.value = TextEditingValue(text: t, selection: TextSelection.collapsed(offset: off));
  }

  void _onController() {
    if (_applying) return;
    final c = widget.controller;
    final text = c.text;
    final sel = c.selection;
    if (text != _prevText) {
      // auto-indent after a pure newline insertion
      if (sel.isValid && sel.isCollapsed && text.length == _prevText.length + 1) {
        final off = sel.baseOffset;
        if (off > 0 &&
            text[off - 1] == '\n' &&
            _prevText == text.substring(0, off - 1) + text.substring(off)) {
          final ls = text.lastIndexOf('\n', math.max(0, off - 2)) + 1;
          final prevLine = off - 1 >= ls ? text.substring(ls, off - 1) : '';
          var indent = prevLine.length - prevLine.trimLeft().length;
          if (prevLine.trimRight().endsWith(':')) indent += 4;
          if (indent > 0) {
            final nt = text.replaceRange(off, off, ' ' * indent);
            _pushUndo();
            _setValue(nt, TextSelection.collapsed(offset: off + indent));
            _afterChange();
            return;
          }
        }
      }
      _pushUndo();
      _redo.clear();
      _prevText = text;
      _prevSel = sel;
      _afterChange();
    } else {
      _prevSel = sel;
      _refreshAssist();
    }
  }

  void _pushUndo() {
    final now = DateTime.now();
    if (_undo.isEmpty || now.difference(_lastPush).inMilliseconds > 450) {
      _undo.add(_Snap(_prevText, _prevSel));
      if (_undo.length > 200) _undo.removeAt(0);
    }
    _lastPush = now;
  }

  void _afterChange() {
    _refreshAssist();
    widget.onChanged?.call();
    if (mounted) setState(() {});
  }

  // ---------------------------------------------------------------- assist
  void _refreshAssist() {
    final c = widget.controller;
    final sel = c.selection;
    if (!sel.isValid) return;
    final off = math.min(sel.baseOffset, c.text.length);
    final ls = c.text.lastIndexOf('\n', math.max(0, off - 1)) + 1;
    final before = c.text.substring(off > ls ? ls : off, off);
    _sugs = _suggest(before);
    _doc = null;
    _builtinDoc = null;
    _contextHelp(before, c.text, off);
    if (mounted) setState(() {});
  }

  List<Sug> _suggest(String before) {
    final m = RegExp(r'([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_0-9]*))?$').firstMatch(before);
    if (m == null) return <Sug>[];
    final owner = m.group(1)!;
    final frag = m.group(2);
    final out = <Sug>[];
    if (frag != null) {
      if (owner == 'math') {
        for (final n in kMathNames) {
          if (n.startsWith(frag) && n != frag) out.add(Sug(n, n.substring(frag.length)));
        }
        return out.take(14).toList();
      }
      final key = owner == 'robot' ? 'robot' : (owner == 'base' ? 'base' : 'entity');
      for (final e in _members[key] ?? <Map<String, dynamic>>[]) {
        final n = e['name'] as String;
        if (n.startsWith(frag) && n != frag) {
          final isM = e['kind'] == 'method';
          out.add(Sug(isM ? '$n()' : n, isM ? '${n.substring(frag.length)}()' : n.substring(frag.length),
              back: isM && (e['params'] as List).isNotEmpty ? 1 : 0));
        }
      }
      return out.take(14).toList();
    }
    final w = owner;
    if (w.length < 2) return out;
    for (final k in kKeywords) {
      if (k.startsWith(w) && k != w) out.add(Sug(k, k.substring(w.length)));
    }
    for (final k in kBuiltins) {
      if (k.startsWith(w) && k != w) out.add(Sug('$k()', '${k.substring(w.length)}()', back: 1));
    }
    for (final k in const ['robot', 'base', 'math']) {
      if (k.startsWith(w) && k != w) out.add(Sug(k, k.substring(w.length)));
    }
    for (final s in kSnippets) {
      if (s.startsWith(w)) out.add(Sug(s, s.substring(w.length) + '\n    '));
    }
    return out.take(14).toList();
  }

  void _contextHelp(String before, String all, int off) {
    // innermost unmatched '(' on this line
    var depth = 0;
    for (var i = before.length - 1; i >= 0; i--) {
      final ch = before[i];
      if (ch == ')') {
        depth++;
      } else if (ch == '(') {
        if (depth == 0) {
          final head = before.substring(0, i);
          final mm = RegExp(r'([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?$').firstMatch(head);
          if (mm != null) {
            _lookup(mm.group(1)!, mm.group(2));
            if (_doc != null || _builtinDoc != null) return;
          }
          break;
        }
        depth--;
      }
    }
    // word under cursor
    final left = RegExp(r'([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?$').firstMatch(before);
    if (left != null) {
      final right = RegExp(r'^[A-Za-z0-9_]*').firstMatch(all.substring(off))!.group(0) ?? '';
      if (left.group(2) != null) {
        _lookup(left.group(1)!, left.group(2)! + right);
      } else {
        _lookup(null, left.group(1)! + right);
      }
    }
  }

  void _lookup(String? a, String? b) {
    String? owner;
    String name;
    if (b != null) {
      owner = a;
      name = b;
    } else {
      name = a ?? '';
    }
    if (owner == null) {
      if (kBuiltinDocs.containsKey(name)) _builtinDoc = kBuiltinDocs[name];
      return;
    }
    final key = owner == 'robot' ? 'robot' : (owner == 'base' ? 'base' : 'entity');
    for (final e in _members[key] ?? <Map<String, dynamic>>[]) {
      if (e['name'] == name) {
        _doc = e;
        return;
      }
    }
  }

  // ---------------------------------------------------------------- build
  @override
  Widget build(BuildContext context) {
    final text = widget.controller.text;
    final lines = text.split('\n');
    final longest = lines.fold<int>(0, (a, l) => math.max(a, l.length));
    final kb = MediaQuery.of(context).viewInsets.bottom > 0;
    const mono = TextStyle(fontFamily: 'monospace', fontSize: fontSize, height: lineH);
    const strut = StrutStyle(fontSize: fontSize, height: lineH, forceStrutHeight: true);
    return LayoutBuilder(builder: (context, c) {
      const gutterW = 46.0;
      final fieldW = math.max(c.maxWidth - gutterW, longest * charW + 80);
      final gutter = Column(
        children: [
          for (var i = 1; i <= lines.length; i++)
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: widget.onToggleBreakpoint == null ? null : () => widget.onToggleBreakpoint!(i),
              child: Container(
                width: gutterW,
                height: fontSize * lineH,
                alignment: Alignment.centerRight,
                padding: const EdgeInsets.only(right: 6),
                color: widget.traceLines.contains(i) ? const Color(0x3356B6C2) : null,
                child: Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                  if (widget.breakpoints.contains(i))
                    const Icon(Icons.circle, size: 9, color: Colors.redAccent)
                  else
                    const SizedBox(width: 9),
                  const SizedBox(width: 3),
                  Text('$i',
                      style: TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 11,
                          color: widget.controller.errorLines.contains(i)
                              ? Colors.redAccent
                              : const Color(0xFF6B7A8C))),
                ]),
              ),
            ),
        ],
      );
      final editor = Scrollbar(
        controller: _vScroll,
        child: SingleChildScrollView(
          controller: _vScroll,
          child: SingleChildScrollView(
            controller: _hScroll,
            scrollDirection: Axis.horizontal,
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Padding(padding: const EdgeInsets.only(top: 8), child: gutter),
              SizedBox(
                width: fieldW,
                child: TextField(
                  controller: widget.controller,
                  focusNode: focus,
                  maxLines: null,
                  keyboardType: TextInputType.multiline,
                  autocorrect: false,
                  enableSuggestions: false,
                  smartDashesType: SmartDashesType.disabled,
                  smartQuotesType: SmartQuotesType.disabled,
                  textCapitalization: TextCapitalization.none,
                  style: mono,
                  strutStyle: strut,
                  cursorColor: Colors.cyanAccent,
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.fromLTRB(6, 8, 12, 80),
                  ),
                ),
              ),
            ]),
          ),
        ),
      );
      return Column(children: [
        Expanded(child: Container(color: const Color(0xFF0F151D), child: editor)),
        if (widget.showHelp) _helpCard(kb),
        _suggestionRow(),
        _symbolRow(),
      ]);
    });
  }

  Widget _helpCard(bool compact) {
    final d = _doc;
    final b = _builtinDoc;
    if (d == null && b == null) return const SizedBox.shrink();
    final theme = Theme.of(context);
    if (b != null) {
      return Container(
        width: double.infinity,
        color: theme.colorScheme.surfaceContainerHigh,
        padding: const EdgeInsets.all(8),
        child: Text(b, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
      );
    }
    final m = d!;
    final params = (m['params'] as List<dynamic>).cast<Map<String, dynamic>>();
    final errors = (m['errors'] as List<dynamic>).cast<String>();
    final oneLine = compact || !widget.guided;
    return Container(
      width: double.infinity,
      constraints: BoxConstraints(maxHeight: oneLine ? 64 : 170),
      color: theme.colorScheme.surfaceContainerHigh,
      padding: const EdgeInsets.fromLTRB(10, 6, 10, 6),
      child: SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${m['signature']}  ->  ${m['returns']}',
              style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5, fontWeight: FontWeight.w700)),
          Text(m['description'] as String, style: const TextStyle(fontSize: 12.5), maxLines: oneLine ? 1 : null,
              overflow: oneLine ? TextOverflow.ellipsis : null),
          if (!oneLine) ...[
            for (final p in params)
              Text('  ${p['name']} (${p['type']}): ${p['valid']}', style: const TextStyle(fontSize: 12)),
            Text('Cost: ${m['cost']}', style: const TextStyle(fontSize: 12)),
            for (final e in errors) Text('! $e', style: const TextStyle(fontSize: 12, color: Color(0xFFE5C07B))),
          ],
        ]),
      ),
    );
  }

  Widget _suggestionRow() {
    if (_sugs.isEmpty) return const SizedBox.shrink();
    return SizedBox(
      height: 40,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 6),
        children: [
          for (final s in _sugs)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 4),
              child: ActionChip(
                visualDensity: VisualDensity.compact,
                label: Text(s.label, style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5)),
                onPressed: () => insertAtCursor(s.insert, back: s.back),
              ),
            ),
        ],
      ),
    );
  }

  Widget _symbolRow() {
    Widget key(String label, String ins, {int back = 0}) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 3),
          child: SizedBox(
            width: label.length > 2 ? 52 : 38,
            child: TextButton(
              style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(34, 34)),
              onPressed: () => insertAtCursor(ins, back: back),
              child: Text(label, style: const TextStyle(fontFamily: 'monospace', fontSize: 14)),
            ),
          ),
        );
    return Container(
      height: 42,
      color: Theme.of(context).colorScheme.surfaceContainer,
      child: ListView(scrollDirection: Axis.horizontal, children: [
        key('Tab', '    '),
        key('(', '()', back: 1),
        key(')', ')'),
        key('[', '[]', back: 1),
        key(']', ']'),
        key('{', '{}', back: 1),
        key(':', ':'),
        key('=', ' = '),
        key('"', '""', back: 1),
        key("'", "''", back: 1),
        key('#', '# '),
        key('_', '_'),
        key('.', '.'),
        key(',', ', '),
        key('+', ' + '),
        key('-', ' - '),
        key('*', ' * '),
        key('/', ' / '),
        key('<', ' < '),
        key('>', ' > '),
        key('==', ' == '),
        key('!=', ' != '),
      ]),
    );
  }

  /// Search helpers used by the editor screen.
  int findNext(String query, {bool backwards = false, bool caseSensitive = false}) {
    if (query.isEmpty) return -1;
    final c = widget.controller;
    final hay = caseSensitive ? c.text : c.text.toLowerCase();
    final q = caseSensitive ? query : query.toLowerCase();
    final sel = c.selection;
    int idx;
    if (backwards) {
      final from = sel.isValid ? sel.start - 1 : hay.length;
      idx = from < 0 ? hay.lastIndexOf(q) : hay.lastIndexOf(q, from);
      if (idx < 0) idx = hay.lastIndexOf(q);
    } else {
      final from = sel.isValid ? sel.end : 0;
      idx = hay.indexOf(q, from);
      if (idx < 0) idx = hay.indexOf(q);
    }
    if (idx >= 0) {
      c.selection = TextSelection(baseOffset: idx, extentOffset: idx + q.length);
      focus.requestFocus();
    }
    return idx;
  }

  bool replaceCurrent(String query, String with_) {
    final c = widget.controller;
    final sel = c.selection;
    if (!sel.isValid || sel.isCollapsed) return false;
    if (c.text.substring(sel.start, sel.end).toLowerCase() != query.toLowerCase()) return false;
    final t = c.text.replaceRange(sel.start, sel.end, with_);
    c.value = TextEditingValue(text: t, selection: TextSelection.collapsed(offset: sel.start + with_.length));
    return true;
  }

  int replaceAll(String query, String with_) {
    if (query.isEmpty) return 0;
    final c = widget.controller;
    final re = RegExp(RegExp.escape(query), caseSensitive: false);
    final n = re.allMatches(c.text).length;
    if (n > 0) {
      c.value = TextEditingValue(
          text: c.text.replaceAll(re, with_), selection: const TextSelection.collapsed(offset: 0));
    }
    return n;
  }

  Future<void> copyAll() async => Clipboard.setData(ClipboardData(text: widget.controller.text));
}
