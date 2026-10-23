# Ortsnetz-Auslastung Beta für Home-Assistant-Admins

> **Beta 0.6.0b1:** Entwicklungsstand zum Testen der neuen optionalen Messfelder. Die stabile Integration bleibt unter [ha_ortsnetz_auslastung](https://github.com/thomaslehmann1234/ha_ortsnetz_auslastung) verfügbar.

Für den regulären Einsatz empfehlen wir die [stabile Integration](https://github.com/thomaslehmann1234/ha_ortsnetz_auslastung#readme). Suche im HACS-Standardkatalog nach **Ortsnetz-Auslastung**; ein benutzerdefiniertes Repository ist dafür nicht erforderlich. Dieses Beta-Repository ist ein optionaler Testkanal und nicht der empfohlene Installationsweg.

## Hinweise zum Beta-Test

- Vor der Installation die Home-Assistant-Konfiguration und die bisherigen Integrationsdateien sichern. Eine separate HA-Testinstanz ist empfohlen.
- Beta und Stable verwenden denselben Ordner und dieselbe Domain `ortsnetz_auslastung`. Sie können nicht parallel in derselben HA-Instanz installiert sein. Die bestehende Integration nicht löschen; ihre Konfiguration und Entitäts-IDs sollen erhalten bleiben.
- HACS darf nicht beide Repositories gleichzeitig als Installationsquelle derselben Integration verwalten. Beim Wechsel die Installationsquelle gezielt auf Beta umstellen; nicht beide Versionen übereinander aktualisieren lassen.
- Ohne GitHub-Releases verwendet HACS den Standardbranch `main`. Für den Test ist kein Release erforderlich; nach Aktualisierungen der Beta-Dateien Home Assistant neu starten.
- Die Integration sendet sofort nach dem Start und danach alle fünf Minuten an die konfigurierte API. Nur reale Messwerte senden und pro Messquelle nur einen aktiven Sender betreiben. Keine Testwerte an die produktive API schicken.
- Zum Rückwechsel die stabile Installationsquelle und die gesicherten Dateien wiederherstellen und Home Assistant neu starten. Die bestehende Integration und ihre Entitäten nicht löschen.

Domain, Sensor-IDs und gespeicherte Einstellungen bleiben unverändert. Der Beta-Name kennzeichnet nur den installierten Entwicklungsstand.

Diese Anleitung richtet sich an Personen, die eine Home-Assistant-Instanz betreuen. Die HACS-Integration sendet die drei Phasenspannungen L1, L2 und L3 sowie den Standort deiner Instanz an die Ortsnetz-Auslastung-API. Nach dem ersten Senden werden die Werte alle fünf Minuten übertragen.

## Ortsnetz-Auslastung

[Ortsnetz-Auslastung](https://www.ortsnetz-auslastung.de) visualisiert Spannungsmessungen, Netzfrequenzen und standortübergreifende Statistiken aus freiwillig teilnehmenden PV-Anlagen in Deutschland.

Für eine Karte der öffentlichen Messpunkte steht zusätzlich das Community-Projekt [Ortsnetz Map](https://github.com/BeGiBue/ha-ortsnetz-auslastung) bereit.

## Voraussetzungen

- Home Assistant mit installiertem [HACS](https://hacs.xyz/)
- Drei numerische `sensor`-Entitäten für L1, L2 und L3; die Zustände müssen Voltwerte enthalten, z. B. `229.8`

Beim Einrichten legt die Integration zusätzlich die Entitäten **Netzspannungsstatus** und **Batteriespeicherempfehlung** an; ihre Werte erscheinen nach der ersten erfolgreichen Übertragung. Der Netzspannungsstatus ist der jeweils schlechteste Phasenstatus (`Normal`, `Warnung` oder `Kritisch`); die Attribute `L1`, `L2` und `L3` zeigen die Einzelbewertungen. Die Batteriespeicherempfehlung ist bei Überspannung `Laden`, bei Unterspannung `Entladen` und bei normaler Spannung `Keine Aktion`. Bei gleichzeitiger Über- und Unterspannung hat `Entladen` Vorrang. Beide Werte kommen in der Antwort der bestehenden Messübertragung zurück und erzeugen keinen zusätzlichen API-Aufruf. Schlägt eine Übertragung auch im zweiten Versuch fehl oder wird sie wegen eines fehlenden oder unplausiblen Spannungswerts übersprungen, sind beide Entitäten nicht verfügbar, bis die API wieder einen gültigen Wert liefert.

- Optional: Eine numerische Forecast-Sensor-Entität mit dem erwarteten PV-Tagesertrag in kWh
- Eine numerische Sensor-Entität für die Netzfrequenz in Hz, z. B. `50.01`
- Vom Server-Admin bereitgestellte öffentliche API-Adresse per HTTPS

Die Integration ist nicht für Werte wie `unknown`, `unavailable` oder Text geeignet. In diesem Fall wird die betreffende Übertragung übersprungen und in den Home-Assistant-Protokollen vermerkt.

Gemessene Phasenspannungen müssen zwischen 150 und 300 V liegen. Liefert ein ausgewählter Sensor genau `-1`, wird diese Phase von der Auswertung ausgeschlossen. Mindestens eine Phase muss eine gültige Spannung liefern; andere ungültige oder nicht verfügbare Werte verhindern weiterhin die Übertragung. Ausgeschlossene Phasen erscheinen als `unavailable` in den Statusattributen `L1`, `L2` und `L3`. Gesamtstatus und Batteriespeicherempfehlung bleiben für die gemessenen Phasen verfügbar.

Die Sensorwerte `230`, `-1`, `-1` ergeben beispielsweise eine einphasige Messung. Alle drei Sensorfelder benötigen weiterhin eine Sensor-Entität; `-1` ist der Sensorzustand und keine Entitäts-ID für den Konfigurationsdialog.

> **Wichtig:** Wähle für L1, L2 und L3 immer die Spannungs-Sensoren des Smartmeters deiner PV-Anlage aus. Wähle auch die Netzfrequenz bevorzugt vom selben Smartmeter. Andere Spannungs- oder Frequenzwerte, etwa von Steckdosen, Wechselrichtern oder einzelnen Geräten, bilden die Netzqualität am Anschluss nicht zuverlässig ab und dürfen nicht verwendet werden.

## 1. Optionale Beta über HACS herunterladen

[![Beta-Repository in HACS öffnen.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thomaslehmann1234&repository=ha_ortsnetz_auslastung_beta&category=integration)

Fahre nur fort, wenn du Beta-Änderungen testen möchtest. Für die Beta ist ein benutzerdefiniertes Repository erforderlich. Nutze den Button oben oder füge es manuell hinzu:

1. Öffne **HACS** in Home Assistant.
2. Öffne das Drei-Punkte-Menü und wähle **Benutzerdefinierte Repositories**.
3. Trage diese Repository-URL ein:

   ```text
   https://github.com/thomaslehmann1234/ha_ortsnetz_auslastung_beta
   ```

4. Wähle als Kategorie **Integration** und bestätige mit **Hinzufügen**.
5. Suche nach **Ortsnetz-Auslastung Beta** und wähle **Herunterladen**.

Starte anschließend Home Assistant wie unten beschrieben neu.

Stable und Beta verwenden dieselbe Integrationsdomain. Installiere nicht beide gleichzeitig und lösche beim Wechsel weder die bestehende Konfiguration noch die Entitäten. Beachte die Hinweise zum Beta-Test oben.

## 2. Home Assistant neu starten

Nach dem Download ist ein Neustart erforderlich:

1. Öffne **Einstellungen → System**.
2. Wähle oben rechts das Ein/Aus-Menü.
3. Wähle **Home Assistant neu starten** und bestätige.

Warte, bis Home Assistant wieder vollständig erreichbar ist.

## 3. Integration einrichten

1. Öffne **Einstellungen → Geräte & Dienste**.
2. Klicke auf **Integration hinzufügen**.
3. Suche nach **Ortsnetz-Auslastung Beta**.
4. Fülle die Felder aus:

   | Feld | Wert |
   | --- | --- |
   | API-Adresse | `https://www.ortsnetz-auslastung.de` oder `https://www.ortsnetz-auslastung.de/v1/measurements` |
   | Sensor L1 | Sensor-Entität für Phase L1 |
   | Sensor L2 | Sensor-Entität für Phase L2 |
   | Sensor L3 | Sensor-Entität für Phase L3 |
   | Anlagengröße (kWp) | Optional, für die Forecast-Übertragung erforderlich. Tatsächlich installierte Nennleistung der PV-Anlage in Kilowatt-Peak, z. B. `9.8` mit Punkt als Trenner. |
   | PV-Forecast heute (kWh) | Optionaler Forecast-Sensor für den erwarteten PV-Ertrag des aktuellen Tages; wird nur mit konfigurierter Anlagengröße übertragen |
   | Smartmeter Hersteller / Typ | Optionales, durchsuchbares Dropdown mit freier Eingabe (maximal 120 Zeichen). Vorhandene eigene Einträge bleiben erhalten. Die Angabe wird nur im Adminbereich der Ortsnetz-Auslastung angezeigt. |
   | Netzfrequenz (Hz) | Frequenz-Sensor des Smartmeters, dessen Wert in Hertz geliefert wird |
   | Batterie-Ladezustand / SOC (%) | Optionaler Sensor für den aktuellen Ladezustand, 0 bis 100 % |
   | Nutzbare Batteriekapazität (kWh) | Optional. Tatsächliche nutzbare Kapazität eintragen, nicht den aktuellen Energieinhalt. Kein Wert ist vorbelegt. |
   | Netzleistung gesamt (W) | Optionaler Sensor für die gesamte Wirkleistung am Hausanschluss: positiv = Netzbezug, negativ = Einspeisung |
   | Breitengrad / Längengrad | Standardmäßig der Home-Assistant-Standort; bei Bedarf überschreiben |

5. Bestätige die Einrichtung.

Die Smartmeter-Auswahl wird lokal mit der Integration ausgeliefert und benötigt keine Online-Abfrage. Grundlage ist die bereinigte Stromzähler-Liste der [Tasmota Smart Meter Descriptors](https://tasmota.github.io/docs/Smart-Meter-Interface/#smart-meter-descriptors), ergänzt um gängige PV-Smartmeter. Die Liste ist keine Kompatibilitätsgarantie: Entscheidend sind weiterhin die verfügbaren Spannungs-Sensoren am Hausanschluss. Nicht gelistete Modelle können direkt im selben Feld eingegeben werden; das Feld darf auch leer bleiben.

SOC, Batteriekapazität und Netzleistung sind für alle Nutzer direkt sichtbar und ausdrücklich optional. Die übrigen neuen Angaben stehen im standardmäßig eingeklappten Bereich **Weitere Messfelder (optional)**. Dieser lässt sich bei der Einrichtung und später unter **Konfigurieren** aufklappen:

| Weitere Messfelder | Auswahl |
| --- | --- |
| Leistungsfaktor gesamt | Vorhandener Sensor mit einem Wert von 0 bis 1 oder in Prozent |
| Scheinleistung gesamt | Vorhandener Sensor in VA oder kVA |
| Stromstärke L1, L2, L3 | Je ein vorhandener Sensor in A oder mA |
| Spannung L1, L2, L3: Minimum, Maximum, Mittelwert | Je ein vorhandener 5-Minuten-Statistiksensor in V |
| Netzfrequenz: Minimum, Maximum, Mittelwert | Je ein vorhandener 5-Minuten-Statistiksensor in Hz |

Alle Felder können leer bleiben. Die Integration liest nur die zugeordneten Sensorzustände und fragt keine zusätzlichen Geräte ab. Sie berechnet keine eigenen Min/Max/Mittelwerte; die ausgewählten Statistiksensoren müssen diese über dasselbe fünfminütige Messintervall liefern. Netzleistung darf nicht durch Wechselrichterleistung oder die Leistung nur einer Phase ersetzt werden. Sensoren mit umgekehrtem Vorzeichen müssen vor der Auswahl passend umgerechnet werden. kW werden nach W, kVA nach VA, mA nach A und ein Leistungsfaktor in Prozent nach 0 bis 1 umgerechnet.

Fehlende oder ungültige optionale Werte werden mit einem Protokollhinweis ausgelassen, ohne die Spannungsübertragung zu verhindern. Das gilt auch für widersprüchliche Statistikwerte (`min <= avg <= max`); bei 0 VA wird der Leistungsfaktor weggelassen. Genau `-1` bleibt bei phasenbezogenen Spannungsstatistiken und Stromstärken der Marker für nicht gemessene Werte. Nicht verfügbare optionale Werte werden nicht durch `0` ersetzt; SOC und Netzleistung dürfen aber tatsächlich 0 sein.

Bei einer Basis-URL ergänzt die Integration automatisch `/v1/measurements`. Eine bereits vollständige Endpunkt-URL bleibt unverändert.

Die Integration sendet sofort einen ersten Datensatz und danach alle fünf Minuten. Die Kartenansicht aktualisiert sich im Live-Modus alle 15 Minuten; ein manuelles Neuladen zeigt den neuen Standort sofort.

PV-Forecast und Anlagengröße können leer bleiben. Ohne konfigurierte Anlagengröße lässt die Integration einen ausgewählten Forecast weg und schreibt einen Hinweis ins Protokoll; die Spannungswerte werden weiterhin übertragen. Dasselbe gilt für Forecasts über dem API-Limit von 10 kWh je kWp pro Tag. Bei gültigen Angaben wird der spezifische Forecast-Ertrag als `Forecast (kWh) ÷ Anlagengröße (kWp) = kWh/kWp/Tag` berechnet. Die Integration verlässt sich nicht auf eine möglicherweise bereits serverseitig gespeicherte Anlagengröße, sondern sendet die konfigurierte Größe zusammen mit dem Forecast.

Wenn du unter **Konfigurieren** die Batteriekapazität, die PV-Anlagengröße oder
das Smartmeter-Modell leerst und speicherst, sendet die Integration mit der
nächsten gültigen Messung ausdrücklich JSON-`null`. Der gespeicherte Serverwert
wird dadurch gelöscht. Dafür ist der aktualisierte Server erforderlich; ältere
Server behalten den bisherigen Wert. Wird ein Feld im API-Request weggelassen,
bleibt sein gespeicherter Wert erhalten. Nach dem Leeren der PV-Anlagengröße
werden auch keine Forecasts mehr gesendet. Historische Messwerte und Forecasts
bleiben gespeichert.

## Prüfung und Fehlerbehebung

Bei HTTP `403` (Standortsperre) und `422` (abgelehnte Messung) erfolgt kein unmittelbarer Wiederholungsversuch. Beide Statussensoren werden sofort als nicht verfügbar markiert. Der nächste reguläre Sendeversuch erfolgt nach fünf Minuten. Bei anderen Übertragungsfehlern bleibt der zweite Versuch nach fünf Sekunden bestehen.

Nach der Einrichtung sollten die Daten nach spätestens fünf Minuten auf der Karte erscheinen. Home-Assistant-Protokolle findest du unter **Einstellungen → System → Protokolle**.

| Meldung | Ursache und Lösung |
| --- | --- |
| `403 Forbidden` | Dieser Standort wurde durch den Server-Admin gesperrt. Standortangaben prüfen oder den Server-Admin kontaktieren. |
| `422` / `Messung abgelehnt` | Die API hat die Messung abgelehnt. Sensorwerte und Konfiguration prüfen. |
| `Spannungssensor … ist nicht verfügbar` | Eine ausgewählte Sensor-Entität hat keinen numerischen Wert. Entität und Einheit prüfen. |
| `Netzfrequenz-Sensor … ist nicht verfügbar` | Der Frequenz-Sensor liefert keinen numerischen Hz-Wert. Entität und Einheit prüfen. |
| `PV-Forecast wird nicht gesendet: Anlagengröße (kWp) fehlt` | Unter **Konfigurieren** die tatsächliche PV-Anlagengröße eintragen oder den Forecast-Sensor entfernen. Spannungswerte werden weiterhin gesendet. |
| Kein Standort auf der Karte | Mindestens fünf Minuten warten, Karte neu laden und die HA-Protokolle prüfen. Besteht das Problem weiter, Zeitpunkt und Fehlermeldung an den Server-Admin geben. |

API-Adresse, Sensoren, Koordinaten und PV-Angaben können nach der Einrichtung unter **Einstellungen → Geräte & Dienste → Ortsnetz-Auslastung → Konfigurieren** angezeigt und geändert werden. Der Standort wird beim ersten Messwert automatisch aus den Koordinaten erkannt.

## Sensorübersetzungen und bestehende Automationen

Die Sensornamen und die Zustandsanzeige stehen auf Deutsch und Englisch zur Verfügung. Intern verwenden beide Sensoren sprachunabhängige Zustandswerte; Home Assistant übersetzt diese für die Anzeige. Die API-Ampelfarben `green`, `yellow` und `red` werden dazu in `normal`, `warning` und `critical` umgewandelt.

Beim Update bleiben bestehende Entitäts-IDs und selbst vergebene Namen erhalten. Automationen, Skripte und Templates, die bisher deutsche Zustandswerte vergleichen, müssen auf die folgenden Werte umgestellt werden:

| Bisheriger Wert | Neuer interner Wert |
| --- | --- |
| `Normal` | `normal` |
| `Warnung` | `warning` |
| `Kritisch` | `critical` |
| `Laden` | `charge` |
| `Entladen` | `discharge` |
| `Keine Aktion` | `none` |

Auch die Phasenattribute `L1`, `L2` und `L3` liefern jetzt `normal`, `warning` oder `critical`. Ihre Attributnamen bleiben unverändert. Vergleiche in Automationen verwenden die internen Werte, auch wenn die Oberfläche weiterhin die deutschen Texte anzeigt.

## Datenschutz

Die Integration übermittelt Koordinaten, Zeitstempel, die drei Spannungswerte, Netzfrequenz sowie Angaben zu PV-Anlage und Forecast. Nur bei entsprechender Konfiguration kommen SOC, Batteriekapazität, Netzleistung und die weiteren Messfelder hinzu. Optional wird Hersteller und Typ des Smartmeters übertragen; diese Angabe ist ausschließlich im geschützten Adminbereich sichtbar. Die öffentliche Karte zeigt Koordinaten nur gerastert mit etwa 100 Metern Genauigkeit. Die Integration sendet die eingetragenen Koordinaten jedoch ungerundet an den Server; die Rasterung betrifft nur die öffentliche Karte. Verwende bei Bedarf die überschreibbaren Koordinaten, um einen alternativen Standort zu senden.

## Kontakt

Fragen zur Integration, zur Datenübermittlung oder zu einem Standort bitte an [thomas.lehmann@gmx.info](mailto:thomas.lehmann@gmx.info).
