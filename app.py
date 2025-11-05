from pathlib import Path

import streamlit as st

from core import (
    split_pdf_bytes_to_named_files,
    build_zip_from_named_files,
)


st.set_page_config(page_title="DossierFacile Extract", page_icon="✂️")

st.title("✂️ Découpeur DossierFacile → ZIP")
st.markdown(
    """\
Téléversez votre PDF global exporté depuis DossierFacile. L'application détecte et découpe
les pièces en fichiers PDF individuels, puis vous propose un ZIP à télécharger.
"""
)

uploaded_file = st.file_uploader("Fichier PDF DossierFacile", type=["pdf"])

if uploaded_file is not None:
    pdf_bytes: bytes = uploaded_file.read()
    zip_basename: str = f"{Path(uploaded_file.name).stem}_extracted"

    with st.spinner("Traitement du PDF…"):
        named_files = split_pdf_bytes_to_named_files(pdf_bytes)
        zip_filename, zip_bytes = build_zip_from_named_files(named_files, zip_basename)

    st.download_button(
        label=f"Télécharger les {len(named_files)} fichiers générés",
        data=zip_bytes,
        file_name=zip_filename,
        mime="application/zip",
        type="primary",
        width="stretch",
        icon=":material/download:",
    )

    st.divider()

    st.subheader("Détails")

    file_data = [
        {"Nom du fichier": name, "Taille (MB)": f"{len(content) / (1024 * 1024):.2f}"}
        for name, content in named_files
    ]
    st.table(file_data)
