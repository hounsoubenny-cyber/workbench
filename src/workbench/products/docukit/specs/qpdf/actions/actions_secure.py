"""
Docukit — qpdf : sécurité (protéger par mot de passe, déverrouiller).

⚠️ Les mots de passe transitent par la ligne de commande du process qpdf
(visible dans `ps` / `/proc/<pid>/cmdline` par les autres utilisateurs LOCAUX
de la machine). C'est acceptable pour l'usage prévu de Docukit (poste
personnel, ou serveur mono-utilisateur) mais PAS pour un serveur partagé
multi-utilisateurs — voir la section Sécurité du README.
Ils ne sont jamais écrits dans les logs, ni renvoyés au client.
"""

from workbench.core.subprocess.wb_subprocess_types import (
    EnumArg, PathArg, PatternArg,
)
from workbench.products.docukit.specs.common import (
    Out, attached_option, flag, ordered,
)
from workbench.products.docukit.specs.qpdf.base_spec import QpdfSpec
from workbench.products.docukit.specs.qpdf.base_model import ProtectInput, UnlockInput


def _protect_args(u: ProtectInput) -> list:
    return [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=Out.PROTECTED),
        flag("--encrypt"),
        # Mot de passe d'ouverture, puis propriétaire, puis taille de clé.
        PatternArg(value=u.password),
        PatternArg(value=u.owner_password or u.password),
        EnumArg(value="256", enum_values=["256"]),
        # qpdf n'accepte ces options que sous la forme collée `--option=valeur`.
        attached_option("--print", "full" if u.allow_print else "none", r"full|none"),
        attached_option("--extract", "y" if u.allow_copy else "n", r"y|n"),
        attached_option("--modify", "all" if u.allow_modify else "none", r"all|none"),
        flag("--"),
    ]


protect_spec = QpdfSpec[ProtectInput](
    id="qpdf_protect",
    label="Protéger par mot de passe",
    description="Chiffre le PDF (AES-256) : un mot de passe sera demandé à l'ouverture.",
    input_cls=ProtectInput,
    output_filename_template=Out.PROTECTED,
    build_args=_protect_args,
)

unlock_spec = QpdfSpec[UnlockInput](
    id="qpdf_unlock",
    label="Retirer le mot de passe",
    description="Produit une copie du PDF sans chiffrement (le mot de passe actuel est requis).",
    input_cls=UnlockInput,
    output_filename_template=Out.UNLOCKED,
    build_args=lambda u: [
        attached_option("--password", u.password, r"[^\x00-\x1f\x7f]{1,128}"),
        flag("--decrypt"),
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=Out.UNLOCKED),
    ],
)

QPDF_SECURE_ACTIONS = ordered(protect_spec, unlock_spec)
__all__ = ["QPDF_SECURE_ACTIONS"]
