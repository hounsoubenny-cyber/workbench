export function toTitleCaseWithUnderscore(str: string): string {
    if (!str) return "";
    
    return str
        .split("_")
        .map(word => {
            if (word.length === 0) return "";
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        })
        .join(" ")
        .trim();
}