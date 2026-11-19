import 'package:flutter_test/flutter_test.dart';
import 'package:code_wars/main.dart';

void main() {
  testWidgets('home screen shows Run button', (tester) async {
    await tester.pumpWidget(const CodeWarsApp());
    expect(find.text('Run'), findsOneWidget);
  });
}
