from dataclasses import dataclass
import io
import zipfile
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader, PdfWriter


INTRO_FIRST_PAGE_TITLE = "Page de garde DossierFacile"


@dataclass(frozen=True)
class PageGroup:
    title: str
    start_idx: int
    end_idx: int

    @property
    def num_pages(self) -> int:
        return self.end_idx - self.start_idx + 1


@dataclass(frozen=True)
class ExportResult:
    output_path: Path
    group: PageGroup


def _extract_page_title(text: str) -> str:
    """Retourne le titre (nom de la pièce) détecté pour une page.

    Heuristique: privilégie la 4e ligne (index 3) si présente, sinon "unknown".
    """
    if not text:
        return "unknown"
    lines = [line.strip() for line in text.split("\n")] if text else []
    if len(lines) > 3 and lines[3]:
        return lines[3]
    return "unknown"


def _slugify(value: str, max_length: int = 80) -> str:
    """Génère un nom de fichier sûr à partir d'un titre."""
    normalized = unicodedata.normalize("NFKD", value or "document")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = re.sub(r"[^a-z0-9\-\_\s]", "", ascii_text)
    ascii_text = re.sub(r"\s+", "-", ascii_text).strip("-") or "document"
    return (
        (ascii_text[:max_length].rstrip("-"))
        if len(ascii_text) > max_length
        else ascii_text
    )


def get_page_titles(pdf_path: Path) -> list[str]:
    """Lit le PDF et renvoie la liste des titres détectés par page.

    La première page est forcée à INTRO_FIRST_PAGE_TITLE si le PDF contient au moins une page.
    """
    reader = PdfReader(pdf_path)
    titles: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        titles.append(_extract_page_title(text))
    if len(titles) > 0:
        titles[0] = INTRO_FIRST_PAGE_TITLE
    return titles


def get_page_titles_from_bytes(pdf_bytes: bytes) -> list[str]:
    """Lit un PDF en mémoire et renvoie la liste des titres détectés par page.

    La première page est forcée à INTRO_FIRST_PAGE_TITLE si le PDF contient au moins une page.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    titles: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        titles.append(_extract_page_title(text))
    if len(titles) > 0:
        titles[0] = INTRO_FIRST_PAGE_TITLE
    return titles


def group_consecutive_pages(page_titles: list[str]) -> list[PageGroup]:
    """Regroupe les pages consécutives partageant le même titre."""
    nb_pages = len(page_titles)
    groups: list[PageGroup] = []
    if nb_pages == 0:
        return groups

    current_title = page_titles[0]
    start_idx = 0
    for idx in range(1, nb_pages):
        if page_titles[idx] != current_title:
            groups.append(
                PageGroup(title=current_title, start_idx=start_idx, end_idx=idx - 1)
            )
            current_title = page_titles[idx]
            start_idx = idx
    groups.append(
        PageGroup(title=current_title, start_idx=start_idx, end_idx=nb_pages - 1)
    )
    return groups


def export_groups_to_pdfs(
    pdf_path: Path, groups: list[PageGroup], dest_dir: Path
) -> list[ExportResult]:
    """Exporte chaque groupe en un PDF distinct dans dest_dir et renvoie les résultats."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(pdf_path)
    results: list[ExportResult] = []

    for group_index, group in enumerate(groups, start=1):
        safe_title = group.title if group.title else f"document-{group_index}"
        filename = f"{group_index:02d}-{_slugify(safe_title)}.pdf"
        output_path = dest_dir / filename

        writer = PdfWriter()
        for page_idx in range(group.start_idx, group.end_idx + 1):
            writer.add_page(reader.pages[page_idx])

        with output_path.open("wb") as f:
            writer.write(f)

        results.append(ExportResult(output_path=output_path, group=group))

    return results


def export_groups_to_memory(
    pdf_bytes: bytes, groups: list[PageGroup]
) -> list[tuple[str, bytes]]:
    """Exporte chaque groupe en un PDF en mémoire et renvoie (filename, content)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    outputs: list[tuple[str, bytes]] = []

    for group_index, group in enumerate(groups, start=1):
        safe_title = group.title if group.title else f"document-{group_index}"
        filename = f"{group_index:02d}-{_slugify(safe_title)}.pdf"

        writer = PdfWriter()
        for page_idx in range(group.start_idx, group.end_idx + 1):
            writer.add_page(reader.pages[page_idx])

        buffer = io.BytesIO()
        writer.write(buffer)
        outputs.append((filename, buffer.getvalue()))

    return outputs


def split_pdf_by_titles(
    pdf_path: Path, output_dir: Path | None = None
) -> list[ExportResult]:
    """Découpe le PDF en PDFs individuels par pièce.

    Renvoie la liste des résultats d'export (un par groupe).
    """
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(f"Fichier PDF introuvable ou invalide: {pdf_path}")

    dest_dir = output_dir or (pdf_path.parent / f"{pdf_path.stem}_extracted")

    titles = get_page_titles(pdf_path)
    groups = group_consecutive_pages(titles)
    return export_groups_to_pdfs(pdf_path=pdf_path, groups=groups, dest_dir=dest_dir)


def split_pdf_bytes_to_named_files(pdf_bytes: bytes) -> list[tuple[str, bytes]]:
    """Découpe un PDF (bytes) en PDFs individuels (en mémoire) nommés.

    Renvoie une liste de tuples (filename, content_bytes).
    """
    titles = get_page_titles_from_bytes(pdf_bytes)
    groups = group_consecutive_pages(titles)
    return export_groups_to_memory(pdf_bytes=pdf_bytes, groups=groups)


def build_zip_from_named_files(
    named_files: list[tuple[str, bytes]], zip_basename: str
) -> tuple[str, bytes]:
    """Construit un ZIP en mémoire à partir d'une liste (filename, content_bytes).

    Renvoie (zip_filename, zip_bytes).
    """
    zip_name = f"{_slugify(zip_basename or 'extracted')}.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in named_files:
            # Evite les chemins dans les noms
            arcname = Path(filename).name
            zf.writestr(arcname, content)
    return zip_name, buffer.getvalue()


def split_pdf_bytes_to_zip(
    pdf_bytes: bytes, zip_basename: str | None = None
) -> tuple[str, bytes]:
    """Pipeline complet: découpe un PDF en mémoire et renvoie un ZIP (nom, bytes)."""
    named_files = split_pdf_bytes_to_named_files(pdf_bytes)
    base = zip_basename or "extracted"
    return build_zip_from_named_files(named_files, base)
