# Ekran powitalny Horyzont — menedżer logowania dla Fedory

Ekran logowania w stylu klasycznego pulpitu z początku lat 2000, dopasowany do środowiska
[Horyzont](https://github.com/Novicek000/HoryzontDesktop): ciemne pasy u góry i u dołu, logo ze wschodzącym
słońcem po lewej, lista kont z obrazami po prawej, pole hasła z zieloną strzałką, „Wyłącz komputer” w lewym
dolnym rogu i „Zapraszamy” po zalogowaniu. Cała grafika jest oryginalna i rysowana w kodzie (te same ikony
i obrazy kont co w Horyzoncie), w schematach kolorów Horyzontu: morskim, grafitowym, śliwkowym i niebieskim.

Działa jako greeter dla **greetd** (demon logowania z PAM) w kompozytorze **labwc**; interfejs to
**Python + Qt (PySide6)**. Nie wymaga środowiska Horyzont — pozwala zalogować się do dowolnej sesji
(Horyzont, GNOME, KDE, Sway…).

## Co potrafi

* **Lista kont** z obrazami z Panelu sterowania Horyzontu (AccountsService) i pełnymi nazwami;
  „Zalogowany” pod kontem, które ma otwartą sesję. Kliknięcie konta bez hasła od razu loguje.
* **Pole hasła** z ostrzeżeniem o włączonym **Caps Lock**, dymkiem „Nie pamiętasz hasła?” po złym haśle
  i przyciskiem **?** ze wskazówką do hasła (gdy jest ustawiona w AccountsService).
* **Wybór sesji** w dolnym pasku (zapamiętywany osobno dla każdego konta), domyślnie Horyzont.
* **Wyłącz komputer**: Stan wstrzymania (z klawiszem Shift — Hibernacja), Wyłącz, Uruchom ponownie.
* **Klasyczne okno logowania** (nazwa użytkownika + hasło, Opcje >> z wyborem sesji): styl `classic`
  albo dwukrotne **Ctrl+Alt+Del** na ekranie powitalnym.
* Dodatkowe pytania PAM (kod weryfikacyjny, zmiana wygasłego hasła) w osobnym okienku.
* Układ klawiatury systemu (`localectl`), wskaźniki myszy Horyzontu, skalowanie do rozdzielczości,
  wygaszanie ekranu po bezczynności, kilka monitorów.
* **Automatyczne logowanie** po starcie komputera (`horyzont-greeter-config autologin jan`).
* **Zabezpieczenie**: jeśli ekran powitalny trzy razy z rzędu nie wystartuje, pojawia się tekstowe logowanie
  (agreety), więc zawsze da się zalogować i naprawić system.

## Instalacja

Pobierz najnowsze wydanie z <https://github.com/Novicek000/HoryzontLogon/releases> (albo
`git clone https://github.com/Novicek000/HoryzontLogon`) i uruchom instalator:

```bash
tar xzf horyzont-greeter-*.tar.gz
cd horyzont-greeter-*
./install.sh
```

Instalator pobiera przez dnf wszystko, czego potrzeba (greetd, labwc, PySide6, qt6-qtwayland i dodatki),
kopiuje pliki do `/usr/local` i — po pytaniu — ustawia ekran powitalny jako ekran logowania zamiast obecnego
(np. GDM). Zmiana działa po ponownym uruchomieniu komputera.

* `./install.sh --no-enable` — tylko instalacja; podgląd: `horyzont-greeter --preview`
* `sudo horyzont-greeter-config disable` — powrót do poprzedniego ekranu logowania
* `./uninstall.sh` — usunięcie (przywraca poprzedni ekran logowania)

## Ustawienia

```
horyzont-greeter-config status
sudo horyzont-greeter-config style classic          # albo welcome
sudo horyzont-greeter-config scheme graphite        # teal / graphite / plum / blue
sudo horyzont-greeter-config hide gosc              # ukryj konto na liście
sudo horyzont-greeter-config session gnome          # sesja domyślna
sudo horyzont-greeter-config autologin jan          # automatyczne logowanie (autologin off — wyłącz)
sudo horyzont-greeter-config set screen_blank_minutes 5
```

Ustawienia są w `/etc/horyzont-greeter/greeter.json`, konfiguracja greetd w `/etc/greetd/config.toml`
(poprzednia zostaje w `config.toml.horyzont-orig`), dziennik ekranu powitalnego w
`/var/lib/horyzont-greeter/greeter.log`.

## Aktualizacje

Tak jak w Horyzoncie: nowa wersja to wydanie na GitHubie (archiwum `.tar.gz` + `SHA256SUMS`), a gdy wydań
nie ma — najnowszy tag albo wersja z pliku `horyzont_greeter/config.py` w gałęzi `main`.

* Gdy jest zainstalowany **Horyzont 0.4.5+**, aktualizacje ekranu powitalnego pojawiają się w
  **Horyzont Updates** (Panel sterowania) razem z aktualizacjami systemu i Horyzontu, i instalują się tak samo.
* Bez Horyzontu codziennie sprawdza je timer `horyzont-greeter-updates.timer` i instaluje automatycznie.
* Ręcznie: `horyzont-greeter-config check-updates`, `sudo horyzont-greeter-config update`.
* Tryb: `sudo horyzont-greeter-config updates auto|notify|off|horyzont|default`.

Aktualizacja nie zmienia ekranu logowania ani ustawień; nowa wersja pojawia się przy następnym wylogowaniu.

Wydanie: `tools/make-release.sh`, potem `gh release create v<wersja> dist/*.tar.gz dist/SHA256SUMS`.

## Jak to działa

greetd uruchamia jako użytkownik `greetd` skrypt `start-greeter`, który przygotowuje konfigurację labwc
(bez skrótów, menu i terminala) i uruchamia w nim program ekranu powitalnego. Program rozmawia z greetd przez
gniazdo (`GREETD_SOCK`): `create_session` → odpowiedź na pytanie PAM o hasło → `start_session` z poleceniem
sesji z pliku `.desktop`. Po zamknięciu ekranu powitalnego greetd uruchamia sesję użytkownika
(przez `session-wrapper`, który wczytuje środowisko powłoki logowania).

Licencja: GPL-3.0-or-later.
