import 'package:flutter/material.dart';

import 'engine.dart';
import 'screens/shell.dart';
import 'store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Store.I.init();
  String? bootError;
  try {
    await Engine.I.ensureDefaults();
  } catch (e) {
    bootError = e.toString();
  }
  runApp(CodeWarsApp(bootError: bootError));
}

class CodeWarsApp extends StatelessWidget {
  const CodeWarsApp({super.key, this.bootError});
  final String? bootError;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Store.I,
      builder: (context, _) {
        final scheme = ColorScheme.fromSeed(
            seedColor: const Color(0xFF22D3EE), brightness: Brightness.dark, surface: const Color(0xFF0E141B));
        return MaterialApp(
          title: 'Code Wars',
          debugShowCheckedModeBanner: false,
          theme: ThemeData(useMaterial3: true, colorScheme: scheme, scaffoldBackgroundColor: const Color(0xFF0B1016)),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(Store.I.textScale)),
            child: child!,
          ),
          home: Shell(bootError: bootError),
        );
      },
    );
  }
}
