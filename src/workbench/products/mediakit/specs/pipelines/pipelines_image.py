#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep  5 11:35:33 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions Pipelines ImageMagick : Workflows Image Dédiés.

Ce fichier orchestre des enchaînements multi-étapes 100% image :
le packaging de photos de produits pour sites e-commerce (auto-orient, avatar carré,
nettoyage EXIF et compression WebP), la création de cartes postales rétro (sépia,
vignettage et cadre), la suite de favicons et l'anonymisation sécurisée.
"""

from workbench.specs.registry import collect_specs
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.products.mediakit.specs.pipelines.base_model import (
    EcommerceProductInput, VintageCardInput, FaviconGeneratorInput, PrivacyBlurInput
)
from workbench.products.mediakit.specs.magick.actions.actions_geometry import (
    auto_orient_spec, square_thumbnail_spec
)
from workbench.products.mediakit.specs.magick.actions.actions_convert import (
    strip_metadata_spec, compress_quality_spec, generate_favicon_spec
)
from workbench.products.mediakit.specs.magick.actions.actions_color import (
    sepia_spec
)
from workbench.products.mediakit.specs.magick.actions.actions_effects import (
    vignette_spec, blur_spec
)
from workbench.products.mediakit.specs.magick.actions.actions_overlays import (
    add_border_spec
)
from workbench.products.mediakit.specs.magick.base_model import (
    AutoOrientInput, SquareThumbnailInput, StripMetadataInput, CompressQualityInput,
    SepiaToneInput, VignetteInput, AddBorderInput, GenerateFaviconInput, BlurImageInput
)


# ─── 1. PACKAGING PRODUIT E-COMMERCE (SANS PERTE INTERMÉDIAIRE) ──────────────
pipeline_ecommerce_product = PipelineSpec[EcommerceProductInput](
    id="pipeline_ecommerce_product",
    label="Packaging Photo E-Commerce (Redressement + Format carré + Strip EXIF + WebP)",
    input_cls=EcommerceProductInput,
    steps=[
        PipelineStepSpec[EcommerceProductInput](
            id="step_orient",
            action=auto_orient_spec,
            build_step_input=lambda p, o: AutoOrientInput(
                input_file=p.input_file,
                output_format="png"  # Intermédiaire sans perte
            )
        ),
        PipelineStepSpec[EcommerceProductInput](
            id="step_square",
            action=square_thumbnail_spec,
            build_step_input=lambda p, o: SquareThumbnailInput(
                input_file=o["_previous"],
                dimension=p.dimension,
                output_format="png"  # Intermédiaire sans perte
            )
        ),
        PipelineStepSpec[EcommerceProductInput](
            id="step_strip",
            action=strip_metadata_spec,
            build_step_input=lambda p, o: StripMetadataInput(
                input_file=o["_previous"],
                output_format="png"  # Intermédiaire sans perte
            )
        ),
        PipelineStepSpec[EcommerceProductInput](
            id="step_compress_webp",
            action=compress_quality_spec,
            build_step_input=lambda p, o: CompressQualityInput(
                input_file=o["_previous"],
                quality=p.quality,
                output_format="webp"  # Compression finale contrôlée
            )
        )
    ]
)


# ─── 2. CARTE POSTALE VINTAGE (SÉPIA -> VIGNETTAGE -> CADRE) ─────────────────
pipeline_vintage_card = PipelineSpec[VintageCardInput](
    id="pipeline_vintage_card",
    label="Carte Postale Rétro (Virage Sépia + Vignettage sombre + Cadre photo)",
    input_cls=VintageCardInput,
    steps=[
        PipelineStepSpec[VintageCardInput](
            id="step_sepia",
            action=sepia_spec,
            build_step_input=lambda p, o: SepiaToneInput(
                input_file=p.input_file,
                threshold_percent=p.sepia_intensity,
                output_format="jpg"
            )
        ),
        PipelineStepSpec[VintageCardInput](
            id="step_vignette",
            action=vignette_spec,
            build_step_input=lambda p, o: VignetteInput(
                input_file=o["_previous"],
                radius=0,
                sigma=25,
                output_format="jpg"
            )
        ),
        PipelineStepSpec[VintageCardInput](
            id="step_border",
            action=add_border_spec,
            build_step_input=lambda p, o: AddBorderInput(
                input_file=o["_previous"],
                thickness=p.border_thickness,
                color=p.border_color,
                output_format="jpg"
            )
        )
    ]
)


# ─── 3. SUITE FAVICON DU WEB (SQUARE -> ICO) ─────────────────────────────────
pipeline_favicon_generator = PipelineSpec[FaviconGeneratorInput](
    id="pipeline_favicon_generator",
    label="Générateur de Favicon (Recadrage carré 512px + Conteneur ICO multi-tailles)",
    input_cls=FaviconGeneratorInput,
    steps=[
        PipelineStepSpec[FaviconGeneratorInput](
            id="step_square",
            action=square_thumbnail_spec,
            build_step_input=lambda p, o: SquareThumbnailInput(
                input_file=p.input_file,
                dimension="512",
                output_format="png"
            )
        ),
        PipelineStepSpec[FaviconGeneratorInput](
            id="step_ico",
            action=generate_favicon_spec,
            build_step_input=lambda p, o: GenerateFaviconInput(
                input_file=o["_previous"]
            )
        )
    ]
)


# ─── 4. ANONYMISATION DE CONFIDENTIALITÉ (FLOU + STRIP EXIF) ─────────────────
pipeline_privacy_blur = PipelineSpec[PrivacyBlurInput](
    id="pipeline_privacy_blur",
    label="Anonymisation Complète (Flou gaussien + Suppression métadonnées GPS/EXIF)",
    input_cls=PrivacyBlurInput,
    steps=[
        PipelineStepSpec[PrivacyBlurInput](
            id="step_blur",
            action=blur_spec,
            build_step_input=lambda p, o: BlurImageInput(
                input_file=p.input_file,
                radius=0,
                sigma=p.blur_intensity,
                output_format="jpg"
            )
        ),
        PipelineStepSpec[PrivacyBlurInput](
            id="step_strip",
            action=strip_metadata_spec,
            build_step_input=lambda p, o: StripMetadataInput(
                input_file=o["_previous"],
                output_format="jpg"
            )
        )
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
PIPELINES_IMAGE_ACTIONS = collect_specs(__name__, spec_type=PipelineSpec)
__all__ = ["PIPELINES_IMAGE_ACTIONS"]