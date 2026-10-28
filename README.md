# ausblick-clientes-data

Daten der App [Ausblick – Clientes](https://lucashcandido.github.io/ausblick-clientes/). Wird von der App geschrieben – nicht von Hand bearbeiten, während jemand die App benutzt.

## Import Oktober 2026 (Parkplätze AMBA)

- **Registro de Garajes Comerciales** – Gobierno de la Ciudad de Buenos Aires, [data.buenosaires.gob.ar](https://data.buenosaires.gob.ar/dataset/garajes-comerciales), Stand 2019, Lizenz CC BY 2.5 AR. Alle Garagen in CABA (Adresse, Barrio); Einträge `gcba-…`.
- **OpenStreetMap** – © OpenStreetMap-Mitwirkende, [ODbL](https://www.openstreetmap.org/copyright). Telefon/Web/Namen für Register-Garagen und kommerzielle Parkplätze im übrigen AMBA; Einträge `osm-…`.
- Skript: `import/build.py`. Telefonnummern stehen nur dort, wo sie in OSM erfasst sind.
