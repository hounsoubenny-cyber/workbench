import { AppConfig } from "@/types/types";
type cachedConfigType = AppConfig | null;
let cachedConfig: cachedConfigType = null;

async function getConfig(force: boolean = true): Promise<AppConfig> {
    if (!force && cachedConfig !== null) return cachedConfig;
    const data = await fetch("/config.json");
    const json: AppConfig = await data.json();
    cachedConfig = json;
    return cachedConfig;
}

export {getConfig};