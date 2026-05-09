# incoming/

Place **source PDFs** here and commit them (Git LFS optional later; standard Git stores them as binary per `.gitattributes`).

## Naming

Prefer descriptive ASCII filenames: `Author_Year_ShortTitle.pdf`. The **`document_id`** used under `extracted/<document_id>/` is derived from the basename without `.pdf` (see `research/README.md`).

## Hygiene

- Only papers/documents you have redistribution rights for.
- Remove corrupted uploads—replace with a fixed binary rather than committing placeholder text files named `.pdf`.
