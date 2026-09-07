import React, { useState, useEffect } from "react";
import "./home.css";
import { Link } from "react-router-dom";
import {
  Layers,
  ArrowRight,
  Film,
  Music,
  Image as ImageIcon,
  ShieldCheck,
  Terminal,
  Zap,
  Cpu,
  Sparkles,
  Sliders,
  CheckCircle2,
  Workflow,
  Wrench,
  BookOpen,
  Code2,
  Check,
  FolderLock,
  Radio,
} from "lucide-react";
import { AppConfig } from "@/types/types";
import { getConfig } from "@/hooks/get_config";
import { verifyToolInstalled } from "@/hooks/utils";
import { useToast } from "./utils/toast/toast_context";

export const Home: React.FC = () => {
  const toast = useToast();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [binaries, setBinaries] = useState<{
    ffmpeg: boolean | null;
    sox: boolean | null;
    magick: boolean | null;
  }>({ ffmpeg: null, sox: null, magick: null });

  // 1. Chargement de config.json
  useEffect(() => {
    getConfig().then((cfg) => setConfig(cfg));
  }, []);

  // 2. Vérification de santé des moteurs au montage
  useEffect(() => {
    async function checkHealth() {
      const onResult = (val: any) => null;
      const onError = (val: any) => {if (val) toast.error(val)}

      const [ff, sx, mg] = await Promise.all([
        verifyToolInstalled("ffmpeg", onResult, onError),
        verifyToolInstalled("sox", onResult, onError),
        verifyToolInstalled("magick", onResult, onError),
      ]);
      setBinaries({ ffmpeg: ff, sox: sx, magick: mg });
    }
    checkHealth();
  }, []);

  const productName = config?.productName || "Mediakit";
  const version = config?.version || "1.0.0";

  return (
    <div className="wb-home-container">
      {/* ─── 1. HERO SECTION ─── */}
      <section className="wb-home-hero">
        <div className="wb-home-hero__badge">
          <Wrench size={13} className="wb-home-hero__badge-icon" />
          <span>WORKBENCH · {productName.toUpperCase()}</span>
          <span className="wb-home-hero__version">v{version}</span>
          <span className="wb-home-hero__badge-dot">✨</span>
        </div>

        <h1 className="wb-home-hero__title">
          Domptez la puissance brute du multimédia CLI.{" "}
          <span className="wb-home-hero__gradient">Sans taper une seule commande.</span>
        </h1>

        <p className="wb-home-hero__subtitle">
          <strong>Workbench {productName}</strong> unifie les trois mastodontes du traitement multimédia —{" "}
          <span className="highlight">FFmpeg</span>, <span className="highlight">SoX</span> et{" "}
          <span className="highlight">ImageMagick</span> — dans un studio graphique moderne, sécurisé par sandboxing et supervisé en temps réel.
        </p>

        <div className="wb-home-hero__actions">
          <Link to="/work" className="wb-btn wb-btn--primary wb-home-cta-btn">
            <Layers size={17} />
            <span>Ouvrir l'Atelier Studio 🚀</span>
          </Link>

          <Link to="/help" className="wb-btn wb-btn--ghost wb-home-secondary-btn">
            <BookOpen size={16} />
            <span>Documentation 📖</span>
          </Link>

          <Link to="/config" className="wb-btn wb-btn--ghost wb-home-secondary-btn">
            <Sliders size={16} />
            <span>Paramètres ⚙️</span>
          </Link>
        </div>

        {/* Santé des 3 Moteurs CLI en direct */}
        <div className="wb-home-hero__stats">
          <div className="wb-home-stat">
            <span className="wb-home-stat__emoji">🎬</span>
            <div className="wb-home-stat__info">
              <span className="wb-home-stat__value">
                FFmpeg {binaries.ffmpeg ? "🟢" : binaries.ffmpeg === false ? "🔴" : "⏳"}
              </span>
              <span className="wb-home-stat__label">Vidéo & Conteneurs</span>
            </div>
          </div>

          <div className="wb-home-stat__divider" />

          <div className="wb-home-stat">
            <span className="wb-home-stat__emoji">🎧</span>
            <div className="wb-home-stat__info">
              <span className="wb-home-stat__value">
                SoX {binaries.sox ? "🟢" : binaries.sox === false ? "🔴" : "⏳"}
              </span>
              <span className="wb-home-stat__label">DSP & Audio Studio</span>
            </div>
          </div>

          <div className="wb-home-stat__divider" />

          <div className="wb-home-stat">
            <span className="wb-home-stat__emoji">🖼️</span>
            <div className="wb-home-stat__info">
              <span className="wb-home-stat__value">
                ImageMagick {binaries.magick ? "🟢" : binaries.magick === false ? "🔴" : "⏳"}
              </span>
              <span className="wb-home-stat__label">Optimisation & Rendu</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 2. COMPARATIF VISUEL : AVANT VS AVEC WORKBENCH ─── */}
      <section className="wb-home-showcase-section">
        <div className="wb-home-showcase-grid">
          {/* Avant : La ligne de commande austère et risquée */}
          <div className="wb-card wb-showcase-card wb-showcase-card--cli">
            <div className="wb-showcase-card__header">
              <span className="wb-showcase-badge is-cli">
                <Terminal size={13} /> En Ligne de Commande (CLI brut)
              </span>
              <span className="wb-showcase-status text-danger">⚠️ Risque d'erreur de syntaxe</span>
            </div>
            <div className="wb-showcase-code">
              <code>
                <span className="cmd-name">ffmpeg</span> -y -i input.mp4 \<br />
                &nbsp;&nbsp;-filter_complex <span className="cmd-str">"[0:v]crop=ih*(9/16):ih,boxblur=25:5[bg];[bg][0:v]overlay=(W-w)/2:(H-h)/2"</span> \<br />
                &nbsp;&nbsp;-c:v libx264 -crf 28 -preset slow \<br />
                &nbsp;&nbsp;-movflags +faststart output_vertical.mp4
              </code>
            </div>
            <ul className="wb-showcase-bullets">
              <li>❌ Commandes à mémoriser et syntaxe complexe</li>
              <li>❌ Risque de blocage stdin ou crash sur dimensions impaires</li>
              <li>❌ Aucun retour graphique ni prévisualisation</li>
            </ul>
          </div>

          {/* Avec Workbench Mediakit */}
          <div className="wb-card wb-showcase-card wb-showcase-card--workbench">
            <div className="wb-showcase-card__header">
              <span className="wb-showcase-badge is-wb">
                <Sparkles size={13} /> Avec Workbench Mediakit
              </span>
              <span className="wb-showcase-status text-success">✓ Formulaires validés & Sécurisés</span>
            </div>
            <div className="wb-showcase-gui-preview">
              <div className="wb-gui-item">
                <span className="gui-label">Action choisie :</span>
                <span className="gui-val">Format vertical 9:16 (TikTok / Reels) 🎬</span>
              </div>
              <div className="wb-gui-item">
                <span className="gui-label">Mode de cadrage :</span>
                <span className="gui-val">Flou d'arrière-plan esthétique ✨</span>
              </div>
              <div className="wb-gui-item">
                <span className="gui-label">Sécurité :</span>
                <span className="gui-val text-success">Dimensions paires garanties auto 🔒</span>
              </div>
            </div>
            <ul className="wb-showcase-bullets">
              <li>✅ Formulaires dynamiques générés par introspection</li>
              <li>✅ Détection automatique des outils et surveillance WebSocket</li>
              <li>✅ Téléchargement immédiat et prévisualisation intégrée</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ─── 3. LE TRIO DES MOTEURS CLI (PILLARS) ─── */}
      <section className="wb-home-section">
        <div className="wb-home-section__header">
          <span className="wb-home-section__tag">🎯 LE COEUR DU RÉACTEUR</span>
          <h2 className="wb-home-section__title">Trois géants du CLI. Une interface unifiée.</h2>
          <p className="wb-home-section__desc">
            Chaque outil excelle dans son domaine. Mediakit expose leurs fonctionnalités avancées à travers des formulaires dynamiques validés par Pydantic.
          </p>
        </div>

        <div className="wb-home-grid-3">
          {/* CARTE 1 : FFmpeg */}
          <div className="wb-card wb-home-card wb-home-card--ffmpeg">
            <div className="wb-home-card__icon-header">
              <span className="wb-home-card__tool-icon">
                <Film size={22} />
              </span>
              <span className="wb-badge wb-badge--accent">Vidéo & Streaming</span>
            </div>

            <h3 className="wb-home-card__title">
              FFmpeg Engine <span className="wb-home-card__emoji">🎞️</span>
            </h3>
            <p className="wb-home-card__body">
              Transcodage matériel, compression intelligente via CRF ou cible en Mo, adaptation verticale 9:16 (TikTok, Reels) avec flou d'arrière-plan, et extraction audio lossless.
            </p>

            <ul className="wb-home-card__features">
              <li><CheckCircle2 size={14} className="feature-check" /> Découpe chirurgicale & sans ré-encodage</li>
              <li><CheckCircle2 size={14} className="feature-check" /> Incrustation de sous-titres (Hardsub)</li>
              <li><CheckCircle2 size={14} className="feature-check" /> GIF animés 256 couleurs haute fidélité</li>
            </ul>
          </div>

          {/* CARTE 2 : SoX */}
          <div className="wb-card wb-home-card wb-home-card--sox">
            <div className="wb-home-card__icon-header">
              <span className="wb-home-card__tool-icon">
                <Music size={22} />
              </span>
              <span className="wb-badge wb-badge--info">Audio & DSP Studio</span>
            </div>

            <h3 className="wb-home-card__title">
              SoX Engine <span className="wb-home-card__emoji">🎚️</span>
            </h3>
            <p className="wb-home-card__body">
              Le véritable "couteau suisse" audio : normalisation de crête, compression multi-bandes pour podcasts, filtres passe-haut anti-rumble et conditionnement optimal pour l'IA Whisper.
            </p>

            <ul className="wb-home-card__features">
              <li><CheckCircle2 size={14} className="feature-check" /> Détection et suppression des silences</li>
              <li><CheckCircle2 size={14} className="feature-check" /> Modification de tempo sans altérer la voix</li>
              <li><CheckCircle2 size={14} className="feature-check" /> Réverbération & Saturation Lo-Fi vintage</li>
            </ul>
          </div>

          {/* CARTE 3 : ImageMagick */}
          <div className="wb-card wb-home-card wb-home-card--magick">
            <div className="wb-home-card__icon-header">
              <span className="wb-home-card__tool-icon">
                <ImageIcon size={22} />
              </span>
              <span className="wb-badge wb-badge--warning">Image & Rendu</span>
            </div>

            <h3 className="wb-home-card__title">
              ImageMagick <span className="wb-home-card__emoji">🎨</span>
            </h3>
            <p className="wb-home-card__body">
              Traitement vectoriel et matriciel sans concession : conversion WebP/AVIF ultra-légère pour le web, recadrage avatar centré, suppression définitive des tags GPS/EXIF et filigranes.
            </p>

            <ul className="wb-home-card__features">
              <li><CheckCircle2 size={14} className="feature-check" /> Protection anti-bombes de décompression</li>
              <li><CheckCircle2 size={14} className="feature-check" /> Génération de suites Favicon multi-tailles (.ico)</li>
              <li><CheckCircle2 size={14} className="feature-check" /> Floutage gaussien d'anonymisation</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ─── 4. SUPER-PIPELINES CROISÉS ─── */}
      <section className="wb-home-pipeline-banner">
        <div className="wb-home-pipeline-banner__glow" />
        <div className="wb-home-pipeline-banner__content">
          <div className="wb-home-pipeline-banner__left">
            <div className="wb-badge wb-badge--accent wb-home-pipeline-tag">
              <Workflow size={13} />
              <span>SUPER-PIPELINES CROISÉS ⚡</span>
            </div>
            <h2 className="wb-home-pipeline-banner__title">
              Faites coopérer des outils hétérogènes. Sans aucun pipe Unix.
            </h2>
            <p className="wb-home-pipeline-banner__text">
              La force architecturale de Workbench réside dans son moteur de pipeline sécurisé : chaque étape matérialise son résultat dans un dossier temporaire dédié. L'audio masterisé par SoX et la pochette 1080p taillée par ImageMagick fusionnent instantanément dans FFmpeg pour produire une vidéo prête pour YouTube.
            </p>
            <div className="wb-home-pipeline-banner__action">
              <Link to="/work" className="wb-btn wb-btn--primary">
                Explorer les Pipelines <ArrowRight size={15} />
              </Link>
            </div>
          </div>

          <div className="wb-home-pipeline-banner__right">
            <div className="wb-pipeline-flow-preview">
              <div className="wb-pipeline-node">
                <span className="wb-pipeline-node__emoji">🎧</span>
                <div className="wb-pipeline-node__info">
                  <span className="wb-pipeline-node__name">Étape 1 : SoX</span>
                  <span className="wb-pipeline-node__desc">Mastering Voix & Compand</span>
                </div>
              </div>
              <div className="wb-pipeline-arrow">↓</div>
              <div className="wb-pipeline-node">
                <span className="wb-pipeline-node__emoji">🖼️</span>
                <div className="wb-pipeline-node__info">
                  <span className="wb-pipeline-node__name">Étape 2 : ImageMagick</span>
                  <span className="wb-pipeline-node__desc">Toile 1920x1080 + Titrage</span>
                </div>
              </div>
              <div className="wb-pipeline-arrow">↓</div>
              <div className="wb-pipeline-node wb-pipeline-node--final">
                <span className="wb-pipeline-node__emoji">🎬</span>
                <div className="wb-pipeline-node__info">
                  <span className="wb-pipeline-node__name">Étape 3 : FFmpeg</span>
                  <span className="wb-pipeline-node__desc">Multiplexage MP4 Final</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 5. SÉCURITÉ & ARCHITECTURE WORKBENCH ─── */}
      <section className="wb-home-section">
        <div className="wb-home-section__header">
          <span className="wb-home-section__tag">🛡️ ARCHITECTURE ROBUSTE</span>
          <h2 className="wb-home-section__title">Conçu pour la sécurité et la production</h2>
          <p className="wb-home-section__desc">
            Exécuter des processus système comporte des risques. Workbench a été pensé dès le premier jour avec une politique de défense en profondeur.
          </p>
        </div>

        <div className="wb-home-grid-3">
          <div className="wb-card wb-home-sec-card">
            <div className="wb-home-sec-card__icon">
              <ShieldCheck size={20} />
            </div>
            <h4>Zéro Injection de Commande</h4>
            <p>
              Aucun argument textuel libre. Chaque paramètre est strictement typé (Path, Int, Float, Bool, Enum) et validé par Pydantic avant d'atteindre le sous-processus.
            </p>
          </div>

          <div className="wb-card wb-home-sec-card">
            <div className="wb-home-sec-card__icon">
              <FolderLock size={20} />
            </div>
            <h4>Sandboxing des Chemins</h4>
            <p>
              Blocage automatique de toute tentative de path traversal (<code>../</code>) et interdiction stricte des préfixes de protocole dangereux (<code>http:</code>, <code>concat:</code>).
            </p>
          </div>

          <div className="wb-card wb-home-sec-card">
            <div className="wb-home-sec-card__icon">
              <Radio size={20} />
            </div>
            <h4>Streaming Live WebSocket</h4>
            <p>
              Chaque tâche possède son propre gestionnaire de buffer isolé avec rejeu d'historique (replay) pour un streaming fluide des flux <code>stdout</code> et <code>stderr</code>.
            </p>
          </div>
        </div>
      </section>

      {/* ─── 6. CALL TO ACTION FINAL ─── */}
      <section className="wb-home-footer-cta">
        <h2 className="wb-home-footer-cta__title">Prêt à transformer vos fichiers multimédias ?</h2>
        <p className="wb-home-footer-cta__desc">
          Ouvrez l'Atelier Studio, choisissez une action ou un pipeline dans le catalogue et laissez les moteurs faire le travail.
        </p>
        <Link to="/work" className="wb-btn wb-btn--primary wb-home-cta-btn">
          <span>Accéder à l'Atelier Studio 🚀</span>
          <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
};

export default Home;