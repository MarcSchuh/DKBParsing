# apt-Repository für DKBParsing einrichten

Dieser Leitfaden beschreibt, wie `dkbparsing` über `apt` installierbar wird.

## Wie es funktioniert

- Der Workflow [`.github/workflows/apt-repo.yml`](../.github/workflows/apt-repo.yml) läuft automatisch bei jedem neuen GitHub Release.
- Er baut den PyInstaller-Executable, verpackt ihn per [`scripts/build_deb_package.sh`](../scripts/build_deb_package.sh) in ein `.deb` (lädt es zusätzlich als Release-Asset hoch), aktualisiert die Repository-Metadaten mit `apt-ftparchive` und signiert sie.
- Das fertige Repository (Pool + Metadaten + `public.key`) wird auf den Branch `apt` gepusht und von **GitHub Pages** ausgeliefert.

Die Auslieferungs-URL lautet: `https://marcschuh.github.io/DKBParsing/`

## Manuell zu erledigen (Checkliste)

### 1. GPG-Schlüssel erzeugen (einmalig, lokal)

Der Schlüssel signiert die apt-Metadaten. Er muss **nicht** auf einem Server liegen – lokal reicht:

```bash
gpg --full-generate-key
# RSA and RSA → 4096 bits → kein Verfallsdatum
# Name: z.B. "DKBParsing apt repository"
# E-Mail: dkbparsing@marc-schuh.de
# Passphrase: vergeben und notieren!
```

Danach Key-ID/Fingerprint abgreifen:

```bash
gpg --list-secret-keys --keyid-format long
```

Privaten Schlüssel exportieren (komplette Ausgabe inkl. `-----BEGIN…`/`-----END…`-Zeilen kopieren):

```bash
gpg --export-secret-keys --armor <KEY-ID> | wl-copy   # oder > private.key
```

> ⚠️ Der private Schlüssel gehört **nie** ins Repository, nur in die GitHub Secrets.

### 2. GitHub Secrets anlegen

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret-Name | Inhalt |
|---|---|
| `APT_GPG_PRIVATE_KEY` | Export aus Schritt 1 (privater Schlüssel, armored) |
| `APT_GPG_PASSPHRASE` | Die gewählte Passphrase |

### 3. Workflow einmal starten

Repo → **Actions → "Publish apt repository" → Run workflow** (Eingabe leer lassen = letzter Release).
Damit wird der `apt`-Branch erstmals befüllt. Danach läuft der Workflow automatisch bei jedem Release mit.

### 4. GitHub Pages aktivieren

Repo → **Settings → Pages**:

- Source: **Deploy from a branch**
- Branch: **`apt`** → Ordner: `/ (root)` → **Save**

### 5. Optional: Schlüssel-Fingerprint dokumentieren

Damit Nutzer den Schlüssel verifizieren können, z.B. Fingerprint in die README oder auf einen Keyserver (`gpg --keyserver keys.openpgp.org --send-keys <KEY-ID>`) hochladen.

## Installation für Nutzer (nach Einrichtung)

```bash
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://marcschuh.github.io/DKBParsing/public.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/dkbparsing.gpg
echo "deb [signed-by=/etc/apt/keyrings/dkbparsing.gpg] https://marcschuh.github.io/DKBParsing/ stable main" \
  | sudo tee /etc/apt/sources.list.d/dkbparsing.list
sudo apt update
sudo apt install dkbparsing
```

Updates künftig einfach über `sudo apt update && sudo apt upgrade dkbparsing`.

## Hinweise / Betrieb

- **Nur `amd64`** – der Executable wird auf dem Ubuntu-Runner gebaut und ist an dessen glibc-Version gebunden. Sehr alte Distributionen könnten daher nicht funktionieren.
- Alle gebauten Versionen bleiben im `pool/` liegen, ältere Releases bleiben also installierbar. Aufräumen = `.deb` aus `apt-repo/pool/…` löschen und Workflow neu laufen lassen.
- Der Workflow versagt bewusst mit klarer Meldung, falls die Secrets fehlen (unsignierte apt-Repos wären kein sinnvoller Zustand).
- Tags, die **vor** diesem PR liegen, haben `scripts/build_deb_package.sh` noch nicht – für sie funktioniert der manuelle Workflow-Start nicht. Einfach einen neuen Release (Version bump) auslösen.
