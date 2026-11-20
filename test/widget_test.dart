import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:code_wars/main.dart';
import 'package:code_wars/store.dart';
import 'package:code_wars/widgets/code_editor.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await Store.I.init();
  });

  testWidgets('app starts on Home and shows main actions', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(const CodeWarsApp(bootError: 'test: no python in unit tests'));
    await tester.pump();
    expect(find.text('CODE WARS'), findsOneWidget);
    expect(find.text('Campaign'), findsWidgets);
    expect(find.textContaining('Python runtime problem'), findsOneWidget);
  });

  testWidgets('navigation rail switches to Settings', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(const CodeWarsApp());
    await tester.pump();
    await tester.tap(find.text('Settings').first);
    await tester.pump();
    expect(find.text('Graphics quality'), findsOneWidget);
  });

  test('PyController highlights keywords and marks error lines', () {
    final c = PyController(text: 'def update(robot):\n    return 1  # hi');
    c.errorLines = {2};
    final span = c.buildTextSpan(context: _FakeContext(), style: const TextStyle(), withComposing: false);
    expect(span.toPlainText(), 'def update(robot):\n    return 1  # hi');
    expect(span.children!.length, greaterThan(5));
  });
}

class _FakeContext extends Fake implements BuildContext {}
