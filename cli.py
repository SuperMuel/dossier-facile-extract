# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer",
#     "pypdf",
# ]
# ///

from pathlib import Path

import typer
from core import (
    get_page_titles,
    group_consecutive_pages,
    export_groups_to_pdfs,
)

app = typer.Typer(
    help=(
        "Outil pour découper le PDF global exporté par DossierFacile en fichiers PDF "
        "individuels (une pièce justificative par fichier), afin de pouvoir déposer "
        "chaque document séparément sur les plateformes immobilières."
    )
)


@app.command()
def split(
    pdf_path: Path = typer.Argument(
        ..., help="Chemin vers le PDF DossierFacile à traiter"
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Dossier de sortie (créé s'il n'existe pas). Par défaut: <pdf>_extracted",
    ),
) -> None:
    """
    Découpe le PDF global en PDFs individuels par pièce justificative.
    Le regroupement est fait en détectant les séquences de pages ayant le même titre.
    """
    if not pdf_path.exists():
        typer.secho(
            f"Erreur: Le fichier '{pdf_path}' n'existe pas.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if not pdf_path.is_file():
        typer.secho(
            f"Erreur: '{pdf_path}' n'est pas un fichier.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    dest_dir = output_dir or (pdf_path.parent / f"{pdf_path.stem}_extracted")
    typer.secho(f"Lecture du fichier: {pdf_path}", fg=typer.colors.BLUE)

    try:
        titles = get_page_titles(pdf_path)
        nb_pages = len(titles)
        typer.secho(f"Nombre de pages: {nb_pages}", fg=typer.colors.GREEN)

        groups = group_consecutive_pages(titles)
        results = export_groups_to_pdfs(
            pdf_path=pdf_path, groups=groups, dest_dir=dest_dir
        )

        for res in results:
            start_display = res.group.start_idx + 1
            end_display = res.group.end_idx + 1
            num_pages_in_group = res.group.num_pages
            typer.secho(
                f"Créé: {res.output_path.name}  (pages {start_display}-{end_display}, {num_pages_in_group} page(s))",
                fg=typer.colors.YELLOW,
            )

        typer.secho(
            f"Export terminé: {len(results)} fichier(s) dans '{dest_dir}'.",
            fg=typer.colors.GREEN,
        )

    except Exception as e:
        typer.secho(
            f"Erreur lors du traitement du PDF: {e}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)


@app.command(hidden=True)
def titres_pages(
    pdf_path: Path = typer.Argument(
        ..., help="Chemin vers le PDF DossierFacile à traiter"
    ),
) -> None:
    """
    Affiche, pour chaque page, le titre détecté (nom de la pièce justificative).
    """
    if not pdf_path.exists():
        typer.secho(
            f"Erreur: Le fichier '{pdf_path}' n'existe pas.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if not pdf_path.is_file():
        typer.secho(
            f"Erreur: '{pdf_path}' n'est pas un fichier.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    typer.secho(f"Lecture du fichier: {pdf_path}", fg=typer.colors.BLUE)

    try:
        titles = get_page_titles(pdf_path)
        nb_pages = len(titles)

        typer.secho(f"Nombre de pages: {nb_pages}\n", fg=typer.colors.GREEN)

        for i, title in enumerate(titles, start=1):
            typer.secho(
                f"--- Page {i}/{nb_pages} ---", fg=typer.colors.YELLOW, bold=True
            )
            print(title)

    except Exception as e:
        typer.secho(
            f"Erreur lors de la lecture du PDF: {e}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
