import 'package:flutter/material.dart';

import '../widgets/common.dart';
import 'campaign_screen.dart';
import 'editor_screen.dart';
import 'home_screen.dart';
import 'lab_screen.dart';
import 'learn_screen.dart';
import 'missions_screen.dart';
import 'play_screen.dart';
import 'robot_wars_screen.dart';
import 'robots_screen.dart';
import 'settings_screen.dart';
import 'worlds_screen.dart';

class NavItem {
  const NavItem(this.title, this.icon);
  final String title;
  final IconData icon;
}

const List<NavItem> kNav = [
  NavItem('Home', Icons.home_rounded),
  NavItem('Play', Icons.sports_esports_rounded),
  NavItem('Campaign', Icons.flag_rounded),
  NavItem('Robot Wars', Icons.precision_manufacturing_rounded),
  NavItem('Worlds', Icons.public_rounded),
  NavItem('Robots', Icons.smart_toy_rounded),
  NavItem('Python Editor', Icons.code_rounded),
  NavItem('Robot Lab', Icons.science_rounded),
  NavItem('Learning Center', Icons.school_rounded),
  NavItem('Missions', Icons.assignment_rounded),
  NavItem('Settings', Icons.settings_rounded),
];

/// Global navigation: any screen can call `Nav.go(index)`.
class Nav {
  static final ValueNotifier<int> index = ValueNotifier<int>(0);
  static void go(int i) => index.value = i;
  static const int home = 0, play = 1, campaign = 2, wars = 3, worlds = 4, robots = 5, editor = 6, lab = 7, learn = 8, missions = 9, settings = 10;
}

class Shell extends StatelessWidget {
  const Shell({super.key, this.bootError});
  final String? bootError;

  Widget _page(int i) {
    switch (i) {
      case 0:
        return HomeScreen(bootError: bootError);
      case 1:
        return const PlayScreen();
      case 2:
        return const CampaignScreen();
      case 3:
        return const RobotWarsScreen();
      case 4:
        return const WorldsScreen();
      case 5:
        return const RobotsScreen();
      case 6:
        return const EditorScreen();
      case 7:
        return const LabScreen();
      case 8:
        return const LearnScreen();
      case 9:
        return const MissionsScreen();
      default:
        return const SettingsScreen();
    }
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: Nav.index,
      builder: (context, idx, _) {
        final wide = MediaQuery.of(context).size.width >= 720;
        final body = SafeArea(child: KeyedSubtree(key: ValueKey<int>(idx), child: _page(idx)));
        if (wide) {
          return Scaffold(
            body: Row(children: [
              SafeArea(
                child: NavigationRail(
                  selectedIndex: idx,
                  onDestinationSelected: Nav.go,
                  labelType: NavigationRailLabelType.all,
                  scrollable: true,
                  destinations: [
                    for (final n in kNav)
                      NavigationRailDestination(icon: Icon(n.icon), label: Text(n.title, textAlign: TextAlign.center)),
                  ],
                ),
              ),
              const VerticalDivider(width: 1),
              Expanded(child: body),
            ]),
          );
        }
        return Scaffold(
          appBar: AppBar(title: Text(kNav[idx].title)),
          drawer: Drawer(
            child: SafeArea(
              child: ListView(children: [
                const ListTile(title: Text('CODE WARS', style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: 2))),
                for (var i = 0; i < kNav.length; i++)
                  ListTile(
                    leading: Icon(kNav[i].icon),
                    title: Text(kNav[i].title),
                    selected: i == idx,
                    onTap: () {
                      Navigator.of(context).pop();
                      Nav.go(i);
                    },
                  ),
              ]),
            ),
          ),
          body: body,
        );
      },
    );
  }
}

Widget screenTitle(BuildContext context, String t, {String? sub}) => Padding(
      padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(t, style: Theme.of(context).textTheme.headlineSmall),
        if (sub != null) Text(sub, style: Theme.of(context).textTheme.bodyMedium),
      ]),
    );

// Re-export for screens that only need the common widgets.
typedef PanelWidget = Panel;
