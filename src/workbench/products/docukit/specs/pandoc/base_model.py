"""
Docukit — modèle d'entrée de l'action pandoc (conversion de documents).
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from workbench.specs.uploads import UploadRef
from workbench.products.docukit.specs.common import PANDOC_IN_EXTS, check_filename

PandocFrom = Literal["markdown", "gfm", "html", "docx", "odt", "epub", "rst", "latex"]
PandocTo = Literal["html", "gfm", "markdown", "plain", "rst", "docx", "odt", "epub"]


class PandocConvertInput(BaseModel):
    input_file: str = UploadRef(
        description="Document à convertir (.md, .txt, .html, .docx, .odt, .epub, .rst, .tex)"
    )
    from_format: PandocFrom = Field(default="markdown", description="Format du document source")
    to_format: PandocTo = Field(default="docx", description="Format de sortie")
    standalone: bool = Field(
        default=True, description="Document complet (ex : page HTML avec <html> et <head>)"
    )
    toc: bool = Field(default=False, description="Ajouter une table des matières")

    @field_validator("input_file")
    @classmethod
    def _name(cls, v: str) -> str:
        return check_filename(v, PANDOC_IN_EXTS)

    @model_validator(mode="after")
    def _toc_needs_standalone(self):
        if self.toc and not self.standalone:
            raise ValueError("la table des matières nécessite l'option « document complet »")
        return self
