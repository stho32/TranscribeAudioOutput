# Anforderungen

## Nummernschema

Alle Anforderungsdateien folgen dem Format `RXXXXX-kurzname.md`, wobei:

- **R** = Prefix fuer "Requirement"
- **XXXXX** = Fuenfstellige, fortlaufende Nummer (z.B. 00001, 00002)
- **kurzname** = Beschreibender Kurzname in Kleinbuchstaben

Beispiel: `R00001-record.md`

## Konventionen

- Jede Anforderung enthaelt YAML-Frontmatter mit den Feldern:
  - `id` - Anforderungs-ID (z.B. R00001)
  - `title` - Aussagekraeftiger Titel
  - `type` - Art der Anforderung (feature, bugfix, improvement)
  - `status` - Aktueller Status (draft, in-progress, done)
  - `created` - Erstellungsdatum (YYYY-MM-DD)
- Neue Anforderungen erhalten die naechste freie Nummer
- Anforderungen werden nach Fertigstellung nicht geloescht, sondern auf `status: done` gesetzt

## Uebersicht

| ID     | Titel                                  | Typ     | Status |
|--------|----------------------------------------|---------|--------|
| R00001 | Record - System-Audio Aufnahme         | feature | done   |
| R00002 | Transcribe - Audio-Transkription mit OpenAI | feature | done   |
