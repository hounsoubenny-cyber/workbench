export function logError(error: Error): null | string {
  // 1. Si pas d'erreur, on retourne null
  if (!error) return null;
  
  // 2. Construction du message d'erreur
  const timestamp = new Date().toLocaleString("fr-FR");
  const logMessage = `[${timestamp}] ${error.name}: ${error.message}\nStack: ${error.stack || 'Pas de stack'}`;
  
  // 3. On log dans la console
  console.error(logMessage);
  
  // 4. On retourne le message (ou null si pas d'erreur)
  return logMessage;
}