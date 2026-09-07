/**
 * Fait défiler la page vers un élément avec un décalage
 * @param elementId - ID de l'élément vers lequel scroller
 * @param offset - Décalage supplémentaire (ex: 80px pour la barre de navigation)
 */
export function scrollToElement(elementId: string, offset: number = 80) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;

    window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
    });
}