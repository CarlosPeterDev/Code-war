import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() => runApp(const CodeWarsApp());

class CodeWarsApp extends StatelessWidget {
  const CodeWarsApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Code Wars',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.cyan, brightness: Brightness.dark),
          useMaterial3: true,
        ),
        home: const PythonProbeScreen(),
      );
}

/// Phase 1 screen: proves real Python executes natively and is budgeted.
class PythonProbeScreen extends StatefulWidget {
  const PythonProbeScreen({super.key});

  @override
  State<PythonProbeScreen> createState() => _PythonProbeScreenState();
}

class _PythonProbeScreenState extends State<PythonProbeScreen> {
  static const _channel = MethodChannel('codewars/python');
  final _controller = TextEditingController(
    text: 'def update(robot):\n    print("hello from python")\n    return sum(range(10))\n',
  );
  String _log = '';

  Future<void> _run() async {
    try {
      final raw = await _channel.invokeMethod<String>('run', {'source': _controller.text});
      final m = jsonDecode(raw ?? '{}') as Map<String, dynamic>;
      setState(() => _log =
          '${m['ok'] == true ? 'OK' : 'ERROR'}\n${m['output'] ?? ''}${m['error'] ?? ''}\nresult: ${m['result']}  steps: ${m['steps']}');
    } on PlatformException catch (e) {
      setState(() => _log = 'Platform error: ${e.message}');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Code Wars — Python runtime check')),
        body: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(children: [
            Expanded(
              child: TextField(
                controller: _controller,
                maxLines: null,
                expands: true,
                style: const TextStyle(fontFamily: 'monospace'),
                decoration: const InputDecoration(border: OutlineInputBorder()),
              ),
            ),
            const SizedBox(height: 8),
            FilledButton(onPressed: _run, child: const Text('Run')),
            const SizedBox(height: 8),
            Expanded(child: SingleChildScrollView(child: Text(_log))),
          ]),
        ),
      );
}
