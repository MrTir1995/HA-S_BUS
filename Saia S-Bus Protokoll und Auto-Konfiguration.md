# **Technische Analyse und Implementierungsstrategien für das Saia S-Bus Protokoll in Linux-Umgebungen**

## **1\. Einführung in die Protokollarchitektur und Systemrelevanz**

Das Saia S-Bus Protokoll (SBC S-Bus) stellt das proprietäre, jedoch umfassend dokumentierte Rückgrat der Kommunikationsinfrastruktur von Saia-Burgess Controls (SBC) dar. Es wurde spezifisch entwickelt, um die einzigartige Speicherarchitektur der Saia PCD (Process Control Device) Steuerungen abzubilden, welche sich signifikant von den flachen Adressräumen anderer Industriestandards wie Modbus unterscheidet. Während generische Protokolle oft nur "Holding Register" und "Coils" kennen, differenziert der S-Bus nativ zwischen Registern, Merkern (Flags), Timern, Countern und Datenbausteinen (DBs). Diese Differenzierung ist entscheidend für die Effizienz der Datenübertragung in komplexen Gebäudeautomations- und Infrastrukturprojekten, da sie den Overhead bei der Adressumsetzung eliminiert.1  
Für Entwickler, die Integrationslösungen unter Linux anstreben, stellt der S-Bus eine interessante Dichotomie dar: Einerseits ist er durch seine binäre Effizienz und CRC-16-Absicherung extrem leistungsfähig, andererseits erfordert die historische Evolution des Protokolls – von seriellen Schnittstellen mit Paritäts-Bits hin zu UDP-Kapselung – ein tiefes Verständnis der verschiedenen Übertragungsmodi und Frame-Strukturen. Die Notwendigkeit, einen eigenen Decoder oder Management-Tools zu entwickeln, ergibt sich oft aus den Limitierungen generischer SCADA-Treiber, die spezifische Diagnosefunktionen oder die automatische Netzwerkerkennung (Auto-Discovery) nicht vollständig unterstützen.  
Diese Abhandlung bietet eine erschöpfende technische Analyse des S-Bus-Protokolls mit einem Fokus auf die Implementierung unter Linux. Sie beleuchtet die physikalischen Schichten, die mathematischen Grundlagen der Datenintegrität, die Nuancen der Linux-Kernel-Treiber für serielle Kommunikation sowie Strategien zur dynamischen Erkennung und Konfiguration von Busteilnehmern unter Verwendung undokumentierter oder wenig bekannter Systemregister.

## **2\. Physikalische Schicht und Übertragungsmodi**

Die physikalische Basis des S-Bus bestimmt maßgeblich die Struktur der darüberliegenden Sicherungsschicht (Data Link Layer). Das Verständnis dieser Abhängigkeiten ist für die Entwicklung robuster Linux-Treiber unerlässlich, da die Wahl des physikalischen Mediums (RS-485 vs. Ethernet) diktiert, welcher "Modus" (Parity, Data oder Break) für die Synchronisation verwendet werden muss.

### **2.1 Serielle Schnittstellenstandards (RS-485 / RS-232)**

Obwohl Ethernet in neuen Installationen dominiert, ist RS-485 aufgrund seiner Störfestigkeit und Multidrop-Fähigkeit in der Feldbusebene weiterhin allgegenwärtig. Ein S-Bus-Netzwerk auf RS-485-Basis folgt einer strengen Bus-Topologie.

| Parameter | Spezifikation | Implikation für Linux-Treiber |
| :---- | :---- | :---- |
| **Topologie** | Linienstruktur, terminiert (120-150Ω) | Reflexionen bei fehlender Terminierung führen zu CRC-Fehlern.2 |
| **Teilnehmerzahl** | Max. 32 pro Segment (ohne Repeater) | Adressraum 0-253 muss logisch verwaltet werden.1 |
| **Signalpegel** | Differenziell (Data A / Data B) | Hardware-Abstraktion durch TTY-Layer; Richtungsumschaltung (RTS) kritisch. |
| **Verkabelung** | Twisted Pair, geschirmt | Schirmung muss einseitig geerdet werden, um Erdschleifen zu vermeiden.3 |

Die Herausforderung unter Linux liegt hierbei oft nicht im Protokoll selbst, sondern in der Latenzsteuerung der USB-zu-RS485-Wandler (z.B. FTDI). Das S-Bus Protokoll definiert spezifische Turnaround-Zeiten (TN) und Training-Sequenzen (TS), die eingehalten werden müssen, um Kollisionen zu vermeiden, wenn der Master vom Senden in den Empfangsmodus wechselt.1

### **2.2 Analyse der Übertragungsmodi (S-Bus Modes)**

Der S-Bus definiert drei fundamentale Modi, um den Start eines Telegramms und die Unterscheidung zwischen Adress- und Datenbytes zu signalisieren. Für die Implementierung eines Decoders ist die korrekte Identifikation des Modus der erste und wichtigste Schritt.

#### **2.2.1 Parity Mode (SM1): Die historische Altlast**

Im Parity Mode (oft auch Multidrop Mode genannt) wird das 9\. Bit eines UART-Frames (das Paritätsbit) zweckentfremdet. Es dient nicht der Fehlererkennung, sondern der Signalisierung:

* **Mark Parity (Logisch 1):** Das Byte ist eine Stationsadresse.  
* **Space Parity (Logisch 0):** Das Byte ist ein Datenbyte oder Befehl.1

**Problematik unter Linux:** Die POSIX-Spezifikation für termios sieht keine "Stick Parity" (CMSPAR) vor. Zwar unterstützen viele Linux-Kernel das CMSPAR-Flag, um Mark/Space-Parität zu erzwingen, jedoch ist das Umschalten dieses Bits während der Laufzeit ("on the fly") extrem rechenintensiv und hardwareabhängig. Um ein Byte mit Mark-Parität zu senden und das nächste mit Space-Parität, muss der Treiber oft den Puffer leeren (drain), die Einstellungen ändern und dann weitersenden. Dies führt zu inakzeptablen Latenzen und Lücken im Datenstrom ("Inter-Byte Gaps"), die von strikten PCD-Timern als Timeout interpretiert werden können.4 Aus diesem Grund wird der Parity Mode für moderne Linux-basierte Implementierungen als obsolet betrachtet und sollte, wenn möglich, vermieden werden.

#### **2.2.2 Break Mode (SM0): Die Modem-Lösung**

Dieser Modus nutzt ein "Break"-Signal (Leitung wird länger als eine Frame-Dauer auf Low gezogen), um den Telegrammstart zu signalisieren. Dies war historisch für Modems notwendig, die keine 9-Bit-Datenübertragung unterstützten. Da moderne IP-basierte Kommunikation und auch die meisten RS-485-Treiber unter Linux besser mit reinem Datenstrom umgehen können, spielt dieser Modus in neuen Entwicklungen eine untergeordnete Rolle, muss aber bei der Analyse von Legacy-Systemen erkannt werden.1

#### **2.2.3 Data Mode (SM2): Der Standard für moderne Integration**

Der Data Mode (SM2) ist die präferierte Methode für alle modernen Anwendungen und die zwingende Voraussetzung für Ether-S-Bus. Er löst das Synchronisationsproblem rein auf Softwareebene durch Byte-Stuffing, was die Verwendung von Standard-8N1-Einstellungen (8 Datenbits, Keine Parität, 1 Stoppbit) ermöglicht. Dies garantiert maximale Kompatibilität mit Linux-TTY-Treibern und USB-Adaptern.

* **Synchronisation:** Jedes Telegramm beginnt zwingend mit dem Zeichen 0xB5 (Frame Synchronization, FS).  
* **Escaping (Byte Stuffing):** Da 0xB5 auch als regulärer Datenwert vorkommen kann, muss es im Datenstrom maskiert werden. Das Protokoll definiert hierfür Sequenzen:  
  * Wird 0xB5 im Datenstrom benötigt, sendet der Sender 0xC5 0x00.  
  * Wird das Escape-Zeichen 0xC5 selbst benötigt, sendet der Sender 0xC5 0x01.

Ein Linux-Decoder muss also einen State-Machine-Ansatz verfolgen: Er liest den Stream Byte für Byte, detektiert 0xB5 als Reset/Start, und verarbeitet nachfolgende 0xC5-Vorkommen durch Lookahead auf das nächste Byte, um den wahren Wert zu rekonstruieren.7

## **3\. Detaillierte Frame-Strukturen und Protokollaufbau**

Die Entwicklung eines Decoders erfordert eine präzise Kenntnis der Byte-Abfolge. Es muss zwischen dem reinen S-Bus-Telegramm (PDU) und der Kapselung (Header) unterschieden werden.

### **3.1 Struktur des Serial Data Mode (SM2)**

Ein Telegramm im Data Mode ist wie folgt aufgebaut. Wichtig ist, dass die Länge variabel ist und vom Befehl abhängt 7:

| Offset | Feldname | Größe | Beschreibung |
| :---- | :---- | :---- | :---- |
| 0 | **FS** | 1 Byte | 0xB5 – Frame Synchronization. |
| 1 | **AT** | 1 Byte | Attribute Byte. Definiert den Typ des Telegramms. |
| 2 | **Address** | 1 Byte | Zieladresse (Master-\>Slave) oder Quelladresse (Slave-\>Master). |
| 3 | **Command** | 1 Byte | S-Bus Opcode (z.B. 0x06 für Read Register). |
| 4...n | **Data** | Variable | Nutzdaten (Länge abhängig vom Command). Unterliegt dem Byte-Stuffing. |
| n+1 | **CRC H** | 1 Byte | High-Byte der CRC-16 Prüfsumme. |
| n+2 | **CRC L** | 1 Byte | Low-Byte der CRC-16 Prüfsumme. |

**Analyse des Attribute-Bytes (AT):**  
Das AT-Byte ist essenziell für den Decoder, um zu wissen, wie die nachfolgenden Daten zu interpretieren sind.

* 0x00: Request (Anfrage vom Master).  
* 0x01: Response (Antwort vom Slave mit Daten).  
* 0x02: Acknowledge (ACK) oder Negative Acknowledge (NAK). Eine Antwort ohne Daten, nur Bestätigung.8

### **3.2 Ether-S-Bus: UDP-Kapselung**

Ether-S-Bus verpackt das serielle Telegramm in ein UDP-Datagramm. Der Standard-Port ist **5050**. Hierbei entfallen das Startzeichen 0xB5 und das Byte-Stuffing, da das UDP-Paket bereits Längeninformationen liefert und die Integrität durch Ethernet-CRC (und S-Bus CRC) gesichert ist. Es kommt jedoch ein spezifischer Header hinzu.9

| Offset | Feld | Größe | Beschreibung |
| :---- | :---- | :---- | :---- |
| 0 | **Length** | 4 Bytes | Gesamtlänge des S-Bus Pakets (Header \+ PDU \+ CRC). Achtung: Endianness beachten (meist Big Endian). |
| 4 | **Version** | 1 Byte | Protokollversion, typischerweise 0x01. |
| 5 | **Type** | 1 Byte | Protokolltyp, 0x00 für Datentransfer. |
| 6 | **Sequence** | 2 Bytes | Sequenznummer. Wird vom Client inkrementiert. Der Server spiegelt diese Nummer in der Antwort. |
| 8 | **Attribute** | 1 Byte | Entspricht dem AT-Byte im seriellen Modus (0x00, 0x01, 0x02). |
| 9 | **Address** | 1 Byte | S-Bus Stationsadresse. |
| 10 | **Command** | 1 Byte | Opcode. |
| 11... | **Data** | Variable | Nutzdaten. |
| Ende | **CRC** | 2 Bytes | CRC-16 über den *gesamten* UDP-Payload (inkl. Header\!). |

**Wichtige Implementierungsnotiz für Linux:** Bei der Berechnung der CRC für Ether-S-Bus muss der *gesamte* Puffer ab Byte 0 (Length) bis zum letzten Datenbyte einbezogen werden. Dies unterscheidet sich von vielen anderen Protokollen, die Header oft ausschließen. Der Sequenzzähler ist kritisch für die Zuordnung von asynchronen Antworten in einem UDP-Socket-System.11

### **3.3 Das Befehlsregister (Opcodes)**

Der Decoder muss die Opcodes korrekt mappen, um die Länge und Struktur der Nutzdaten zu bestimmen. Die folgende Tabelle aggregiert die wichtigsten Befehle für die Prozessdatenkommunikation 8:

| Objekt | Lesen (Opcode) | Schreiben (Opcode) | Besonderheit |
| :---- | :---- | :---- | :---- |
| **Inputs** | 0x03 | – | Nur lesbar. Antwort liefert Bytes mit gepackten Bits. |
| **Outputs** | 0x05 | 0x0D | Antwort bei Read analog zu Inputs. |
| **Flags** | 0x02 | 0x0B | Merker, zentrales Speicherelement. |
| **Register** | 0x06 | 0x0E | 32-Bit Werte (Integer oder Float). Übertragung Big Endian. |
| **Timer** | 0x07 | 0x0F | Liefert aktuellen Wert (32-Bit) und Status (Bit). |
| **Counter** | 0x00 | 0x0A | Analog zu Timern. |
| **RTC** | 0x04 | 0x0C | Real Time Clock (Struktur mit Woche, Tag, Stunde etc.). |
| **Data Block** | 0x96 | 0x97 | Übertragung ganzer Speicherblöcke (DBs). |

**Analyse eines Hex-Dumps (Read Register):**  
Ein praktisches Beispiel verdeutlicht die Struktur. Wir lesen Register 100 von Station 10\.

* **Anfrage (Ether-S-Bus):** ...\[Addr=0A\]\[Cmd=06\]...  
  * Hier ist 00 64 die Adresse des Registers (100 dezimal) als 16-Bit Wert.  
* **Antwort:** ...\[Addr=0A\]\[Cmd=06\]...  
  * Der Opcode 06 wird in der Antwort wiederholt. Die Daten 00 00 30 39 entsprechen dem Wert 12345 dezimal.  
  * Zu beachten: Bei serieller Kommunikation würde hier noch das Byte-Stuffing greifen, falls z.B. der Wert 0xB5 enthalten wäre.1

## **4\. Datenintegrität: Der CRC-16 Algorithmus**

Ein häufiger Fehlerpunkt bei der Entwicklung eigener S-Bus-Treiber ist die korrekte Implementierung der Prüfsumme. Der S-Bus verwendet den Standard CRC-16-CCITT, jedoch gibt es Feinheiten bei der Initialisierung.

### **4.1 Algorithmische Spezifikation**

* **Polynom:** $x^{16} \+ x^{12} \+ x^5 \+ 1$ (Hexadezimal 0x1021).  
* **Initialisierung:** Historische Dokumente und Firmware-Versionen variieren. Während der Standard-CCITT oft mit 0xFFFF initialisiert wird, nutzen viele S-Bus-Implementierungen 0x0000. Bei Ether-S-Bus ist die Initialisierung oft 0x0000, aber die Berechnung umfasst den Header.  
* **Reflection:** Keine Eingabe- oder Ausgabe-Reflektion (Non-Reflected).  
* **Position:** Die CRC-Bytes werden Big-Endian (High Byte zuerst) angehängt.13

### **4.2 C-Code Implementierungsstrategie für Linux**

Für maximale Performance unter Linux sollte eine vorberechnete Lookup-Table (LUT) verwendet werden. Dies reduziert die CPU-Last im Vergleich zur bitweisen Berechnung erheblich, was besonders auf Embedded-Gateways (z.B. Raspberry Pi) relevant ist.

C

// Beispielhafte LUT-Generierung und Berechnung  
const uint16\_t crc16\_table \= { /\*... vorberechnete Werte für 0x1021... \*/ };

uint16\_t calculate\_sbus\_crc(const uint8\_t \*data, size\_t length) {  
    uint16\_t crc \= 0x0000; // Startwert prüfen: 0x0000 oder 0xFFFF je nach Generation  
    for (size\_t i \= 0; i \< length; i++) {  
        uint8\_t index \= (crc \>\> 8\) ^ data\[i\];  
        crc \= (crc \<\< 8\) ^ crc16\_table\[index\];  
    }  
    return crc;  
}

**Kritischer Hinweis zur Dekodierung:** Im **Seriellen Data Mode (SM2)** muss die CRC-Berechnung auf dem *bereinigten* Datenstrom erfolgen. Das bedeutet, der Decoder muss zuerst die Escape-Sequenzen (0xC5 0x00 \-\> 0xB5) auflösen und die rohen Bytes in einen temporären Puffer schreiben. Erst über diesen "destuffed" Puffer darf die CRC berechnet werden. Wird die CRC über den rohen seriellen Strom (inklusive Escapes) berechnet, wird sie fehlschlagen.7

## **5\. Linux-Entwicklungsumgebung und Bibliotheken**

Die Entwicklung eines S-Bus-Decoders unter Linux muss nicht bei Null beginnen. Es existieren sowohl High-Level-Bibliotheken als auch Low-Level-Referenzimplementierungen.

### **5.1 Python: Das digimat.saia Ökosystem**

Die Bibliothek digimat.saia ist die derzeit umfassendste Open-Source-Lösung für Ether-S-Bus. Sie abstrahiert die Komplexität der UDP-Header und des Sequenzmanagements vollständig.

* **Architektur:** Die Bibliothek ist objektorientiert aufgebaut. Ein SAIANode-Objekt repräsentiert die lokale Schnittstelle, während SAIAServer-Objekte entfernte SPSen darstellen.  
* **Feature-Set:**  
  * Unterstützung für symbolischen Zugriff durch Parsen von .map-Dateien (die vom Saia PG5 Compiler generiert werden). Dies erlaubt den Zugriff via Variablennamen statt Speicheradressen.15  
  * Integrierter Scanner für das Netzwerk (siehe Abschnitt Auto-Discovery).  
  * Automatische Typkonvertierung (Saia Float zu IEEE Float). Saia verwendet ein proprietäres Float-Format (FFP/Motorola Fast Floating Point), das binär nicht kompatibel zu IEEE 754 ist. Die Bibliothek übernimmt diese Konvertierung transparent.15

### **5.2 Wireshark als Referenz (packet-sbus.c)**

Für Entwickler, die einen C/C++ Decoder schreiben, ist der Quellcode des Wireshark-Dissectors (packet-sbus.c) die wertvollste Ressource.

* **Undokumentierte Befehle:** Der Dissector enthält Definitionen für Befehle, die in den offiziellen Handbüchern oft fehlen, wie z.B. 0xA0 (Write System Buffer) oder 0xAF (Web Server Communication). Diese sind essenziell für Deep Packet Inspection.16  
* **Strukturanalyse:** Der Code zeigt exakt, wie die variablen Längen verschiedener Telegrammtypen (z.B. Schreiben von Texten oder DBs) logisch geparst werden.

### **5.3 Low-Level C++ Socket-Programmierung**

Für performante Embedded-Anwendungen ist der direkte Zugriff via BSD-Sockets notwendig.

* **Socket-Konfiguration:** Verwendung von SOCK\_DGRAM. Das SO\_REUSEADDR-Flag sollte gesetzt werden, um schnelle Restarts des Daemons zu ermöglichen.  
* **Puffer-Management:** Ein Ringpuffer ist für TCP-Streams üblich, aber bei UDP (Ether-S-Bus) empfiehlt sich ein fester Puffer von ca. 2 KB pro Paket, da S-Bus Telegramme selten größer als 255 Bytes (plus Header) sind. Die maximale Nutzlast für Registerzugriffe liegt typischerweise bei 32 Registern pro Telegramm (32 \* 4 Bytes \= 128 Bytes Payload).11

## **6\. Automatische Erkennung (Auto-Discovery) und Konfiguration**

Die Anforderung der automatischen Erkennung ist komplex, da der S-Bus im Gegensatz zu modernen IT-Protokollen (wie mDNS) kein natives "Announcement" besitzt.

### **6.1 Der Broadcast-Mechanismus**

Adresse **255** (0xFF) ist im S-Bus fest als Broadcast-Adresse reserviert.

* **Verhalten:** Alle Slaves im Segment verarbeiten Telegramme an diese Adresse.  
* **Einschränkung:** Slaves senden **keine Antwort** auf Broadcasts. Dies dient der Vermeidung von Kollisionen auf dem Busmedium. Ein einfaches "Ping" an 255 führt also zu keinem Ergebnis und einem Timeout beim Master.8  
* **Anwendungsfall:** Broadcasts eignen sich daher primär zum *Setzen* von Werten (z.B. globale Zeitsynchronisation oder Reset), aber nicht zur direkten Erkennung.

### **6.2 Strategien zur Auto-Discovery**

Um Teilnehmer zu finden, muss eine aktive Scan-Strategie implementiert werden.

#### **6.2.1 Sequenzielles Scannen (Iterative Polling)**

Der zuverlässigste Weg unter Linux ist ein iterativer Scan.

1. Der Master sendet nacheinander ein harmloses Lesetelegramm (z.B. Read Status oder Read Register 0\) an die Adressen 0 bis 253\.  
2. Bei Ether-S-Bus (UDP) kann dies parallelisiert werden, indem Anfragen burst-artig gesendet werden. Da jede Anfrage eine Sequenznummer hat, können die asynchron eintreffenden Antworten den Anfragen zugeordnet werden.  
3. Die Bibliothek digimat.saia implementiert genau diesen Mechanismus im interaktiven Modus.15

#### **6.2.2 Identifikation über Systemregister**

Sobald ein Teilnehmer antwortet, muss der Decoder herausfinden, um was für ein Gerät es sich handelt. Die Saia PCDs stellen hierfür einen standardisierten Bereich an Systemregistern zur Verfügung, die ab Firmware-Version 1.x (z.B. E-Line Module) konsistent sind 1:

| Register Adresse | Inhalt | Format | Bedeutung für Decoder |
| :---- | :---- | :---- | :---- |
| **R 600** | Firmware Version | Decimal | Gibt Aufschluss über unterstützte Features. |
| **R 605 \- 608** | Produkt-Typ | ASCII String | Enthält den Modellnamen (z.B. "PCD1.M2120"). Dies muss über 4 Register à 4 Bytes gelesen und konkateniert werden. |
| **R 609** | Hardware Version | Hex | Revisionsstand der Hardware. |
| **R 611 \- 612** | Seriennummer | Hex | Eindeutige Identifikation des Geräts. |
| **R 620** | Protokollwahl | Integer | 1 \= S-Bus, 3 \= Modbus. |
| **R 621** | Baudrate | Integer | Aktuelle Baudrate der Schnittstelle. |

Ein intelligenter Auto-Discovery-Algorithmus liest nach dem ersten "Ping" sofort die Register R 605-608 aus, um dem Benutzer den Klarnamen des Geräts anzuzeigen.

### **6.3 Konfiguration der Busteilnehmer**

Das Ändern von Parametern wie der Stationsadresse ist eine kritische Operation, die oft undokumentiert bleibt.

#### **6.3.1 Adressänderung via SYSWR (System Write)**

Der Befehl SYSWR (System Write) ist das mächtigste Werkzeug im S-Bus-Arsenal. Er korrespondiert meist mit proprietären Opcodes oder Schreibzugriffen auf spezielle Adressbereiche.

* **Opcode:** Der S-Bus Opcode für SYSWR wird oft intern als Write Register (0x0E) auf hohe Adressen oder über den generischen "Write Configuration" Befehl abgebildet.  
* **Funktionsweise:** Um die Stationsadresse zu ändern, wird der Befehl SYSWR mit dem Funktionscode 6000 (oder ähnlich, je nach PCD-Serie) verwendet. Das Argument ist die neue Stationsadresse.1  
* **Broadcast-Konfiguration:** Um einem Gerät mit unbekannter Adresse eine neue Adresse zuzuweisen, muss der Master physisch Punkt-zu-Punkt verbunden sein (nur ein Slave am Bus). Dann kann ein Broadcast (an 255\) mit dem Befehl zur Adressänderung gesendet werden. Da alle Slaves hören, aber nur einer angeschlossen ist, wird die Adresse effektiv überschrieben.1

#### **6.3.2 Gateway-Funktionalität unter Linux**

Linux-Systeme fungieren oft als Gateway zwischen Ethernet und RS-485 S-Bus. Der Decoder muss hierbei das Konzept der "Zieladresse" verstehen. Im Ether-S-Bus Header steht die Zielstation. Das PCD-Gateway nimmt das Paket an, prüft die Adresse, und leitet es transparent auf den seriellen Bus weiter. Der Linux-Treiber muss hierbei Timeouts großzügig berechnen, da die Antwortzeit nun die langsame serielle Übertragung beinhaltet.1

## **7\. Zusammenfassung und Ausblick**

Die Entwicklung eines Linux-basierten S-Bus Decoders ist eine anspruchsvolle Aufgabe, die über das bloße Parsen von Bytes hinausgeht. Der Entwickler muss die historischen Altlasten (Parity Mode) umgehen, indem er konsequent auf den Data Mode (SM2) und Ether-S-Bus setzt. Die Nutzung von UDP Port 5050 ermöglicht performante Netzwerke, erfordert jedoch ein robustes Sequenzmanagement im Userspace-Treiber.  
Für die Auto-Discovery ist der iterative Scan in Kombination mit der Abfrage der Identifikationsregister (R 600+) der Industriestandard. Bibliotheken wie digimat.saia bieten hierfür hervorragende Vorlagen, während Wiresharks packet-sbus.c als ultimative Referenz für das Verständnis undokumentierter Telegrammstrukturen dient. Durch die korrekte Implementierung der CRC-16 und das Verständnis der Systemregister lässt sich eine Steuerungsintegration erreichen, die in Tiefe und Stabilität kommerziellen SCADA-Systemen in nichts nachsteht.

#### **Referenzen**

1. SAIA PCD Manual SAIA S-Bus, Zugriff am Januar 19, 2026, [https://www.dcsmodule.com/js/htmledit/kindeditor/attached/20220712/20220712134948\_56336.pdf](https://www.dcsmodule.com/js/htmledit/kindeditor/attached/20220712/20220712134948_56336.pdf)  
2. Saia S-Bus SIO Driver \- Pro-face, Zugriff am Januar 19, 2026, [http://www.pro-face.com/otasuke/files/manual/gpproex/new/device/data/saia\_sio.pdf](http://www.pro-face.com/otasuke/files/manual/gpproex/new/device/data/saia_sio.pdf)  
3. RTF RS485 S-Bus and Modbus RTU.pdf \- DigitalOcean, Zugriff am Januar 19, 2026, [https://xconnect.ams3.digitaloceanspaces.com/documentation/RTF%20RS485%20S-Bus%20and%20Modbus%20RTU.pdf](https://xconnect.ams3.digitaloceanspaces.com/documentation/RTF%20RS485%20S-Bus%20and%20Modbus%20RTU.pdf)  
4. Linux and MARK/SPACE Parity \- viereck.ch, Zugriff am Januar 19, 2026, [https://viereck.ch/linux-mark-space-parity/](https://viereck.ch/linux-mark-space-parity/)  
5. serial communication with mark and space parity \- Stack Overflow, Zugriff am Januar 19, 2026, [https://stackoverflow.com/questions/23466349/serial-communication-with-mark-and-space-parity](https://stackoverflow.com/questions/23466349/serial-communication-with-mark-and-space-parity)  
6. PARMRK termios behavior not working on Linux \- Stack Overflow, Zugriff am Januar 19, 2026, [https://stackoverflow.com/questions/20132316/parmrk-termios-behavior-not-working-on-linux](https://stackoverflow.com/questions/20132316/parmrk-termios-behavior-not-working-on-linux)  
7. S-BUS protocol for MORSE \- Racom, Zugriff am Januar 19, 2026, [https://www.racom.eu/download/sw/prot/free/eng/sbus.pdf](https://www.racom.eu/download/sw/prot/free/eng/sbus.pdf)  
8. S-BUS protocol for MORSE | RACOM, Zugriff am Januar 19, 2026, [https://www.racom.eu/eng/support/prot/sbus/index.html](https://www.racom.eu/eng/support/prot/sbus/index.html)  
9. Details of the S-Bus driver \- WinCC OA Portal, Zugriff am Januar 19, 2026, [https://www.winccoa.com/documentation/WinCCOA/3.18/en\_US/Treiber\_SBus/sbus\_details.html](https://www.winccoa.com/documentation/WinCCOA/3.18/en_US/Treiber_SBus/sbus_details.html)  
10. Details of the S-Bus driver \- WinCC OA, Zugriff am Januar 19, 2026, [https://www.winccoa.com/documentation/WinCCOA/latest/en\_US/Treiber\_SBus/sbus\_details.html](https://www.winccoa.com/documentation/WinCCOA/latest/en_US/Treiber_SBus/sbus_details.html)  
11. Help \- SBus Basics \- MBLogic, Zugriff am Januar 19, 2026, [https://mblogic.sourceforge.net/hmiserver/sbusbasics-en.html](https://mblogic.sourceforge.net/hmiserver/sbusbasics-en.html)  
12. PCD1.G5010-A20 \- Honeywell | Digital Assets, Zugriff am Januar 19, 2026, [https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/sbc/31-141\_ENG\_DS\_PCD1G5010-A20\_01.pdf](https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/sbc/31-141_ENG_DS_PCD1G5010-A20_01.pdf)  
13. AN204834 F²MC-16FX Family CRC16/Checksum Calculation for Flash, Zugriff am Januar 19, 2026, [https://www.infineon.com/dgdl/Infineon-AN204834\_F\_MC-16FX\_Family\_CRC16\_Checksum\_Calculation\_for\_Flash-ApplicationNotes-v03\_00-EN.pdf?fileId=8ac78c8c7cdc391c017d0d0cdbee5c72](https://www.infineon.com/dgdl/Infineon-AN204834_F_MC-16FX_Family_CRC16_Checksum_Calculation_for_Flash-ApplicationNotes-v03_00-EN.pdf?fileId=8ac78c8c7cdc391c017d0d0cdbee5c72)  
14. CRC-CCITT \-- 16-bit, Zugriff am Januar 19, 2026, [https://srecord.sourceforge.net/crc16-ccitt.html](https://srecord.sourceforge.net/crc16-ccitt.html)  
15. Python digimat.saia \- GitHub, Zugriff am Januar 19, 2026, [https://github.com/digimat/digimat-saia](https://github.com/digimat/digimat-saia)  
16. File: packet-sbus.c \- Debian Sources, Zugriff am Januar 19, 2026, [https://sources.debian.org/src/wireshark/1.2.11-6%2Bsqueeze14/epan/dissectors/packet-sbus.c](https://sources.debian.org/src/wireshark/1.2.11-6%2Bsqueeze14/epan/dissectors/packet-sbus.c)  
17. wireshark/epan/dissectors/packet-sbus.c at master \- GitHub, Zugriff am Januar 19, 2026, [https://github.com/boundary/wireshark/blob/master/epan/dissectors/packet-sbus.c](https://github.com/boundary/wireshark/blob/master/epan/dissectors/packet-sbus.c)  
18. E-Line S-Serie RIO 12DI \- Honeywell | Digital Assets, Zugriff am Januar 19, 2026, [https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/sbc/31-149\_ENG\_DS\_PCD1E1000-A10.pdf](https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/sbc/31-149_ENG_DS_PCD1E1000-A10.pdf)