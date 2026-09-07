import React, { useState } from "react";
import "./help.css";
import { Link } from "react-router-dom";
import {
  HelpCircle,
  BookOpen,
  Film,
  Music,
  Image as ImageIcon,
  Workflow,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Layers,
  ArrowRight,
  Terminal,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
} from "lucide-react";

interface FaqItem {
  question: string;
  answer: string;
  emoji: string;
}

const FAQS: FaqItem[] = [
  {
    emoji: "🔒",
    question: "Pourquoi le caractère deux-points (:) est-il interdit dans les noms de fichiers ?",
    answer:
      "C'est une protection vitale contre les failles d'injection par protocole. Dans FFmpeg et ImageMagick, un chemin contenant ':' peut être interprété comme un protocole distant (ex: 'http://', 'concat:', 'msl:'). Pour garantir un sandboxing étanche, Mediakit refuse tout chemin contenant ce caractère.",
  },
  {
    emoji: "🔴",
    question: "Pourquoi certaines actions ou pipelines sont-ils grisés ou désactivés ?",
    answer:
      "Mediakit teste la présence réelle des binaires installés sur votre machine (FFmpeg, SoX, ImageMagick). Si une action ou une étape de pipeline nécessite un binaire introuvable, le bouton est automatiquement verrouillé avec un badge explicatif afin d'éviter tout crash.",
  },
  {
    emoji: "🧹",
    question: "Combien de temps mes fichiers générés sont-ils conservés ?",
    answer:
      "La durée de conservation est définie par la valeur 'file_ttl' dans les Paramètres (par défaut 3600 secondes = 1 heure). Passé ce délai, le nettoyeur asynchrone purge automatiquement les dossiers temporaires scratch pour préserver l'espace disque de la machine.",
  },
  {
    emoji: "⚡",
    question: "Comment fonctionnent les Super-Pipelines sans pipes Unix (|) ?",
    answer:
      "Contrairement aux scripts shell classiques qui s'échangent des octets bruts par des pipes susceptibles de bloquer, Mediakit matérialise chaque sortie dans un fichier intermédiaire propre sur le disque de travail. L'étape suivante prend ce fichier en entrée de façon atomique et vérifiée.",
  },
  {
    emoji: "📟",
    question: "Puis-je fermer l'onglet ou rafraîchir la page pendant un rendu lourd ?",
    answer:
      "Oui ! Les tâches s'exécutent en arrière-plan sur le serveur sous forme de sous-processus managés. Le serveur conserve les logs en mémoire tampon (buffer). Dès votre retour sur l'Atelier Studio, le flux WebSocket rejoue l'historique manqué (Replay) et reprend le suivi en direct.",
  },
  {
    emoji: "🚀",
    question: "Qu'est-ce que le 'Faststart' dans les conversions vidéo web ?",
    answer:
      "L'option Faststart déplace l'atome 'moov' (l'index des métadonnées de la vidéo) au tout début du fichier MP4. Cela permet à la vidéo de se lancer instantanément sur un navigateur web avant même que le fichier entier ne soit téléchargé.",
  },
];

export const HelpPage: React.FC = () => {
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  const toggleFaq = (idx: number) => {
    setOpenFaqIndex(openFaqIndex === idx ? null : idx);
  };

  return (
    <div className="wb-help-container">
      {/* ─── En-tête ─── */}
      <div className="wb-help-hero">
        <div className="wb-help-hero__tag">
          <BookOpen size={13} />
          <span>GUIDE OFFICIEL & DOCUMENTATION</span>
        </div>
        <h1 className="wb-help-hero__title">
          Comment maîtriser Workbench Mediakit 📖
        </h1>
        <p className="wb-help-hero__subtitle">
          Retrouvez les bonnes pratiques, le fonctionnement des pipelines, le glossaire multimédia et les réponses à toutes vos questions.
        </p>
      </div>

      {/* ─── SECTION 1 : Guide Pas-à-Pas ─── */}
      <section className="wb-help-section">
        <div className="wb-help-section__header">
          <span className="section-tag">🚀 PRISE EN MAIN RAPIDE</span>
          <h2 className="section-title">Le flux de travail en 4 étapes simples</h2>
        </div>

        <div className="wb-help-steps-grid">
          <div className="wb-card wb-help-step-card">
            <span className="step-badge">Étape 1</span>
            <h3>Sélectionnez une Action 🗂️</h3>
            <p>
              Parcourez l'<strong>Atelier Studio</strong>. Filtrez par outil (Vidéo, Audio, Image ou Super-Pipeline) et cliquez sur une carte pour inspecter ses prérequis.
            </p>
          </div>

          <div className="wb-card wb-help-step-card">
            <span className="step-badge">Étape 2</span>
            <h3>Configurez & Uploadez ⚙️</h3>
            <p>
              Le formulaire dynamique génère automatiquement les champs typés nécessaires. Glissez-déposez vos fichiers sources dans la zone de dépôt.
            </p>
          </div>

          <div className="wb-card wb-help-step-card">
            <span className="step-badge">Étape 3</span>
            <h3>Supervisez en Direct 📟</h3>
            <p>
              Le <strong>Job Deck</strong> ouvre un WebSocket dédié. Suivez en temps réel les logs <code>stdout</code> et <code>stderr</code> émis par le moteur CLI.
            </p>
          </div>

          <div className="wb-card wb-help-step-card">
            <span className="step-badge">Étape 4</span>
            <h3>Téléchargez & Visionnez 🎬</h3>
            <p>
              Une fois le job terminé, prévisualisez directement la vidéo, l'audio ou l'image dans le lecteur intégré ou téléchargez les fichiers en un clic.
            </p>
          </div>
        </div>
      </section>

      {/* ─── SECTION 2 : Les Trois Moteurs CLI ─── */}
      <section className="wb-help-section">
        <div className="wb-help-section__header">
          <span className="section-tag">🛠️ PANORAMA DES OUTILS</span>
          <h2 className="section-title">Quand utiliser quel moteur ?</h2>
        </div>

        <div className="wb-help-tools-grid">
          <div className="wb-card wb-help-tool-card">
            <div className="tool-card-head">
              <Film size={22} className="tool-icon tool-icon--ffmpeg" />
              <h4>FFmpeg · Vidéo & Flux 🎬</h4>
            </div>
            <p>
              Idéal pour toutes les manipulations temporelles et de conteneurs : conversion en MP4/WebM, découpage précis à la frame près, ajout de filigranes ou logos, incrustation de sous-titres en dur (Hardsub), et génération de GIF haute fidélité.
            </p>
          </div>

          <div className="wb-card wb-help-tool-card">
            <div className="tool-card-head">
              <Music size={22} className="tool-icon tool-icon--sox" />
              <h4>SoX · Audio & Studio DSP 🎚️</h4>
            </div>
            <p>
              La référence pour le traitement sonore chirurgical : normalisation de crête, suppression automatique des silences au début/fin d'enregistrement, compresseur multi-bandes pour voix de podcast, et conversion 16 kHz mono pour l'IA Whisper.
            </p>
          </div>

          <div className="wb-card wb-help-tool-card">
            <div className="tool-card-head">
              <ImageIcon size={22} className="tool-icon tool-icon--magick" />
              <h4>ImageMagick · Rendu & Image 🎨</h4>
            </div>
            <p>
              Indispensable pour l'optimisation visuelle web : conversion en WebP/AVIF ultra-légers, création de miniatures carrées centrées sans distorsion, suppression des métadonnées privées EXIF/GPS, et création de favicons ICO multi-tailles.
            </p>
          </div>
        </div>
      </section>

      {/* ─── SECTION 3 : Glossaire Technique ─── */}
      <section className="wb-help-section">
        <div className="wb-help-section__header">
          <span className="section-tag">💡 CONCEPTS CLÉS</span>
          <h2 className="section-title">Glossaire & Notions Multimédias</h2>
        </div>

        <div className="wb-help-glossary-grid">
          <div className="wb-card wb-glossary-card">
            <span className="glossary-term">CRF (Constant Rate Factor)</span>
            <p>
              Facteur de qualité d'encodage vidéo (de 18 à 35). Plus le chiffre est bas, plus la fidélité est élevée. <strong>CRF 24 à 28</strong> offre un compromis poids/qualité idéal pour le web.
            </p>
          </div>

          <div className="wb-card wb-glossary-card">
            <span className="glossary-term">EBU R128 & LUFS</span>
            <p>
              Standard broadcast de mesure du volume perçu par l'oreille humaine. YouTube, Spotify et Netflix recommandent un niveau intégré entre <strong>-14 et -16 LUFS</strong> pour éviter la baisse de volume automatique.
            </p>
          </div>

          <div className="wb-card wb-glossary-card">
            <span className="glossary-term">Strip des Métadonnées EXIF</span>
            <p>
              Suppression de toutes les données invisibles attachées à une photo : coordonnées GPS, date, modèle d'appareil. Essentiel pour alléger le fichier et préserver la vie privée en ligne.
            </p>
          </div>

          <div className="wb-card wb-glossary-card">
            <span className="glossary-term">Découpe sans ré-encodage (-c copy)</span>
            <p>
              Découpe instantanée d'un segment vidéo en copiant directement les flux binaires. Très rapide mais calée sur les <em>keyframes</em> (images clés) les plus proches.
            </p>
          </div>
        </div>
      </section>

      {/* ─── SECTION 4 : FAQ Interactive ─── */}
      <section className="wb-help-section">
        <div className="wb-help-section__header">
          <span className="section-tag">❓ QUESTIONS FRÉQUENTES</span>
          <h2 className="section-title">Foire Aux Questions (FAQ)</h2>
        </div>

        <div className="wb-faq-accordion">
          {FAQS.map((faq, idx) => {
            const isOpen = openFaqIndex === idx;
            return (
              <div key={idx} className={`wb-card wb-faq-item ${isOpen ? "is-open" : ""}`}>
                <button
                  type="button"
                  className="wb-faq-trigger"
                  onClick={() => toggleFaq(idx)}
                >
                  <span className="wb-faq-question">
                    <span className="wb-faq-emoji">{faq.emoji}</span>
                    {faq.question}
                  </span>
                  {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {isOpen && (
                  <div className="wb-faq-content">
                    <p>{faq.answer}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ─── Call To Action Final ─── */}
      <div className="wb-help-cta">
        <h3>Prêt à lancer votre premier traitement ?</h3>
        <p>Rejoignez l'Atelier Studio et exploitez toute la richesse du catalogue Mediakit.</p>
        <Link to="/work" className="wb-btn wb-btn--primary help-cta-btn">
          <span>Ouvrir l'Atelier Studio</span>
          <ArrowRight size={15} />
        </Link>
      </div>
    </div>
  );
};

export default HelpPage;