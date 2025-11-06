## DossierFacile Extract

Outil pour découper le PDF global exporté par DossierFacile en fichiers PDF individuels (une pièce justificative par fichier).

### Prérequis
- [uv](https://docs.astral.sh/uv/)
- c'est tout

### CLI
```bash
uv run cli.py split DossierFacile.pdf
```

### Web App
Démarrer l'interface web locale, puis téléverser le PDF DossierFacile:
```bash
uv run streamlit run app.py
```
